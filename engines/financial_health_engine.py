from typing import Optional
from rag.kb_loader import get_health_benchmarks, get_budget_rules


class FinancialHealthEngine:
    """
    Calculates financial health scores and metrics.

    Used by health_agent as the calculation backbone.
    All scoring logic lives here — not in the agent.

    Scoring Components:
    - Savings Rate     (25 points)
    - Emergency Fund   (25 points)
    - Debt Ratio       (25 points)
    - Investment Rate  (15 points)
    - Credit Score     (10 points)
    Total              100 points
    """

    def __init__(self):
        self.benchmarks = get_health_benchmarks()
        self.weights    = self.benchmarks.get("health_score_weights", {
            "savings_rate":    25,
            "emergency_fund":  25,
            "debt_to_income":  25,
            "investment_rate": 15,
            "credit_score":    10
        })

    # ─── Master Calculate Method ──────────────────────────────────────────

    def calculate(self, profile: dict) -> dict:
        """
        Run full financial health calculation.
        Returns complete health report dict.
        """

        monthly_income   = profile.get("monthly_income",       1)
        monthly_expenses = profile.get("monthly_expenses",      0)
        existing_savings = profile.get("existing_savings",      0)
        existing_invest  = profile.get("existing_investments",  0)
        existing_debts   = profile.get("existing_debts",        0)
        credit_score     = profile.get("credit_score",          650)
        age              = profile.get("age",                   30)

        # ── Core Metrics ──────────────────────────────────────────────────
        monthly_surplus  = monthly_income - monthly_expenses
        savings_rate     = self._savings_rate(monthly_income, monthly_expenses)
        emergency_months = self._emergency_months(existing_savings, monthly_expenses)
        dti_ratio        = self._dti_ratio(existing_debts, monthly_income)
        investment_rate  = self._investment_rate(existing_invest, monthly_income)

        # ── Component Scores ──────────────────────────────────────────────
        savings_score    = self._score_savings_rate(savings_rate)
        emergency_score  = self._score_emergency_fund(emergency_months)
        debt_score       = self._score_debt_ratio(dti_ratio)
        invest_score     = self._score_investment_rate(investment_rate)
        credit_comp      = self._score_credit_score(credit_score)

        overall_score    = (
            savings_score  +
            emergency_score +
            debt_score      +
            invest_score    +
            credit_comp
        )

        grade            = self._get_grade(overall_score)

        # ── Budget Suggestion ─────────────────────────────────────────────
        budget           = self._budget_suggestion(monthly_income)

        # ── Emergency Fund Gap ────────────────────────────────────────────
        emergency_needed = monthly_expenses * 6
        emergency_gap    = max(0, emergency_needed - existing_savings)

        return {
            "overall_score":   round(overall_score, 1),
            "grade":           grade,

            "raw_metrics": {
                "monthly_surplus":   round(monthly_surplus,  2),
                "savings_rate":      round(savings_rate,     2),
                "emergency_months":  round(emergency_months, 2),
                "dti_ratio":         round(dti_ratio,        2),
                "investment_rate":   round(investment_rate,  2),
                "emergency_gap":     round(emergency_gap,    2),
                "emergency_needed":  round(emergency_needed, 2)
            },

            "component_scores": {
                "savings_rate":    savings_score,
                "emergency_fund":  emergency_score,
                "debt_ratio":      debt_score,
                "investment_rate": invest_score,
                "credit_score":    credit_comp
            },

            "components": {
                "savings_rate": {
                    "score":     savings_score,
                    "max":       25,
                    "value":     f"{savings_rate:.1f}%",
                    "benchmark": "20%+",
                    "status":    "good" if savings_rate >= 20 else "needs_work"
                },
                "emergency_fund": {
                    "score":     emergency_score,
                    "max":       25,
                    "value":     f"{emergency_months:.1f} months",
                    "benchmark": "6 months",
                    "status":    "good" if emergency_months >= 6 else "needs_work"
                },
                "debt_ratio": {
                    "score":     debt_score,
                    "max":       25,
                    "value":     f"{dti_ratio:.1f}%",
                    "benchmark": "below 36%",
                    "status":    "good" if dti_ratio < 36 else "needs_work"
                },
                "investment_rate": {
                    "score":     invest_score,
                    "max":       15,
                    "value":     f"{investment_rate:.1f}%",
                    "benchmark": "20%+",
                    "status":    "good" if investment_rate >= 15 else "needs_work"
                },
                "credit_score": {
                    "score":     credit_comp,
                    "max":       10,
                    "value":     str(credit_score),
                    "benchmark": "750+",
                    "status":    "good" if credit_score >= 750 else "needs_work"
                }
            },

            "budget_suggestion": budget
        }

    # ─── Metric Calculators ───────────────────────────────────────────────

    def _savings_rate(
        self,
        monthly_income:   float,
        monthly_expenses: float
    ) -> float:
        """Monthly savings as % of income."""
        if monthly_income <= 0:
            return 0.0
        return max(0, (monthly_income - monthly_expenses) / monthly_income * 100)

    def _emergency_months(
        self,
        existing_savings: float,
        monthly_expenses: float
    ) -> float:
        """How many months of expenses are covered by savings."""
        if monthly_expenses <= 0:
            return 0.0
        return existing_savings / monthly_expenses

    def _dti_ratio(
        self,
        existing_debts:  float,
        monthly_income:  float
    ) -> float:
        """Annual debt as % of annual income."""
        if monthly_income <= 0:
            return 0.0
        annual_income = monthly_income * 12
        return (existing_debts / annual_income * 100) if annual_income > 0 else 0.0

    def _investment_rate(
        self,
        existing_investments: float,
        monthly_income:       float
    ) -> float:
        """
        Monthly equivalent of investments as % of income.
        Assumes existing_investments grew over ~2 years.
        """
        if monthly_income <= 0:
            return 0.0
        monthly_equiv = existing_investments / 24   # assume 2 years
        return (monthly_equiv / monthly_income * 100)

    # ─── Score Calculators ────────────────────────────────────────────────

    def _score_savings_rate(self, rate: float) -> int:
        """
        Savings Rate → Score (max 25)
        30%+ = 25 | 20-29% = 20 | 10-19% = 12 | <10% = 5
        """
        if rate >= 30:   return 25
        if rate >= 20:   return 20
        if rate >= 10:   return 12
        return 5

    def _score_emergency_fund(self, months: float) -> int:
        """
        Emergency Fund → Score (max 25)
        6+ = 25 | 3-6 = 15 | 1-3 = 8 | <1 = 0
        """
        if months >= 6:  return 25
        if months >= 3:  return 15
        if months >= 1:  return 8
        return 0

    def _score_debt_ratio(self, dti: float) -> int:
        """
        Debt-to-Income → Score (max 25)
        <20% = 25 | 20-35% = 18 | 36-49% = 10 | 50%+ = 3
        """
        if dti < 20:     return 25
        if dti < 36:     return 18
        if dti < 50:     return 10
        return 3

    def _score_investment_rate(self, rate: float) -> int:
        """
        Investment Rate → Score (max 15)
        20%+ = 15 | 15-19% = 12 | 10-14% = 8 | <10% = 3
        """
        if rate >= 20:   return 15
        if rate >= 15:   return 12
        if rate >= 10:   return 8
        return 3

    def _score_credit_score(self, score: int) -> int:
        """
        Credit Score → Score (max 10)
        800+ = 10 | 750-799 = 8 | 700-749 = 6 | 650-699 = 4 | <650 = 2
        """
        if score >= 800: return 10
        if score >= 750: return 8
        if score >= 700: return 6
        if score >= 650: return 4
        return 2

    # ─── Grade ────────────────────────────────────────────────────────────

    def _get_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:  return "A+"
        if score >= 80:  return "A"
        if score >= 70:  return "B+"
        if score >= 60:  return "B"
        if score >= 50:  return "C"
        return "D"

    # ─── Budget Suggestion ────────────────────────────────────────────────

    def _budget_suggestion(self, monthly_income: float) -> dict:
        """50/20/30 India adapted budget split."""
        return {
            "needs":               round(monthly_income * 0.50),
            "wants":               round(monthly_income * 0.20),
            "savings_investments": round(monthly_income * 0.30),
            "note":                "50% needs | 20% wants | 30% savings and investments"
        }

    # ─── Improvement Suggestions ──────────────────────────────────────────

    def get_improvement_suggestions(self, profile: dict) -> list:
        """
        Generate specific improvement suggestions
        based on the calculated metrics.
        """
        result = self.calculate(profile)
        metrics = result["raw_metrics"]
        suggestions = []

        monthly_income   = profile.get("monthly_income", 0)
        monthly_expenses = profile.get("monthly_expenses", 0)

        # ── Emergency Fund ────────────────────────────────────────────────
        if metrics["emergency_months"] < 6:
            gap     = metrics["emergency_gap"]
            monthly = round(gap / 12)
            suggestions.append({
                "area":     "Emergency Fund",
                "current":  f"{metrics['emergency_months']:.1f} months",
                "target":   "6 months",
                "action_steps": [
                    f"Save Rs {monthly:,.0f}/month in liquid mutual fund",
                    f"Target: Rs {gap:,.0f} total to reach 6 months",
                    "Use Parag Parikh Liquid Fund for better returns than savings account"
                ]
            })

        # ── Savings Rate ──────────────────────────────────────────────────
        if metrics["savings_rate"] < 20:
            target_saving  = round(monthly_income * 0.20)
            current_saving = round(monthly_income - monthly_expenses)
            gap            = max(0, target_saving - current_saving)
            suggestions.append({
                "area":     "Savings Rate",
                "current":  f"{metrics['savings_rate']:.1f}%",
                "target":   "20%+",
                "action_steps": [
                    f"Increase monthly savings by Rs {gap:,.0f}",
                    "Review subscriptions and discretionary spending",
                    "Set up auto-transfer on salary credit date"
                ]
            })

        # ── Investment Rate ───────────────────────────────────────────────
        if metrics["investment_rate"] < 15:
            suggestions.append({
                "area":     "Investment Rate",
                "current":  f"{metrics['investment_rate']:.1f}%",
                "target":   "20%+",
                "action_steps": [
                    f"Start Nifty 50 Index Fund SIP of Rs {round(monthly_income * 0.10):,.0f}/month",
                    "Max out PPF — Rs 1,50,000/year",
                    "Open ELSS SIP for 80C tax saving"
                ]
            })

        # ── Debt Ratio ────────────────────────────────────────────────────
        if metrics["dti_ratio"] > 36:
            suggestions.append({
                "area":     "Debt Management",
                "current":  f"DTI {metrics['dti_ratio']:.1f}%",
                "target":   "Below 36%",
                "action_steps": [
                    "List all debts by interest rate",
                    "Pay highest interest debt first",
                    "Avoid new personal loans above 12% interest"
                ]
            })

        return suggestions[:3]