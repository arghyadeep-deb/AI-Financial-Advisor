from sqlalchemy.orm import Session
from fastapi import HTTPException
from agents.graph_executor import GraphExecutor
from memory.conversation_memory import LongTermMemory
from backend.models.models import FinancialState


class AnalysisService:

    VALID_TYPES = [
        "full", "quick", "health", "investment",
        "credit", "optimizer", "simulation",
        "rebalance", "summary"
    ]

    def __init__(self, db: Session):
        self.db       = db
        self.executor = GraphExecutor()
        self.memory   = LongTermMemory(db)

    def run(
        self,
        analysis_type: str,
        profile_dict:  dict,
        user_id:       int
    ) -> dict:
        """Run analysis agents and save results."""

        if analysis_type not in self.VALID_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analysis_type. Must be one of: {self.VALID_TYPES}"
            )

        print(f"[AnalysisService] Running {analysis_type} analysis for user {user_id}")

        # ── Run agents ────────────────────────────────────────────────────
        if analysis_type == "full":
            output = self.executor.execute_full_analysis(profile_dict)
        elif analysis_type == "quick":
            output = self.executor.execute_quick_analysis(profile_dict)
        else:
            output = self.executor.execute_single(analysis_type, profile_dict)

        results = output.get("results", {})

        # ── Save health score ─────────────────────────────────────────────
        if "health" in results:
            score = results["health"].get("overall_score", 0)
            self.memory.update_health_score(user_id, score)

            # Also update portfolio value from investment results
            investment  = results.get("investment", {})
            corpus_10yr = investment.get("projected_corpus_10yr", 0)
            savings_rate = results["health"].get(
                "components", {}
            ).get("savings_rate", {}).get("value", "0%")

            try:
                rate = float(str(savings_rate).replace("%", "").strip())
            except (ValueError, AttributeError):
                rate = 0.0

            self._update_financial_state(
                user_id         = user_id,
                health_score    = score,
                portfolio_value = corpus_10yr,
                savings_rate    = rate
            )

        # ── Cache results ─────────────────────────────────────────────────
        self.memory.save_analysis_result(user_id, analysis_type, results)

        print(f"[AnalysisService] Analysis complete. Errors: {list(output.get('errors', {}).keys()) or 'none'}")

        return output

    def get_last(self, user_id: int) -> dict:
        """Get last cached analysis results."""
        result = self.memory.get_last_analysis(user_id, "full")
        if not result:
            result = self.memory.get_last_analysis(user_id, "quick")
        return result or {}

    def get_state(self, user_id: int) -> dict:
        """Get financial state — health score + portfolio value."""
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if not state:
            return {
                "health_score":         0,
                "portfolio_value":      0,
                "monthly_savings_rate": 0,
                "last_updated":         None,
                "message":              "No analysis run yet. Run POST /analysis first."
            }

        return {
            "health_score":         state.health_score         or 0,
            "portfolio_value":      state.portfolio_value      or 0,
            "monthly_savings_rate": state.monthly_savings_rate or 0,
            "last_updated":         state.last_updated,
            "message":              None
        }

    def _update_financial_state(
        self,
        user_id:         int,
        health_score:    float,
        portfolio_value: float,
        savings_rate:    float
    ):
        """Update or create financial state record."""
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if state:
            state.health_score         = round(health_score,    1)
            state.portfolio_value      = round(portfolio_value, 2)
            state.monthly_savings_rate = round(savings_rate,    2)
            from datetime import datetime
            state.last_updated         = datetime.utcnow()
        else:
            from datetime import datetime
            state = FinancialState(
                user_id              = user_id,
                health_score         = round(health_score,    1),
                portfolio_value      = round(portfolio_value, 2),
                monthly_savings_rate = round(savings_rate,    2)
            )
            self.db.add(state)

        self.db.commit()