from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from backend.models.models import Thread, Message, FinancialState


# ─── Conversation Memory ──────────────────────────────────────────────────────

class ConversationMemory:
    """
    Manages per-thread conversation history.
    Stores user_name and user_email with every thread and message
    so DB is always traceable by person — not just by ID.
    """

    def __init__(self, db: Session, max_history: int = 20):
        self.db          = db
        self.max_history = max_history

    # ─── Create Thread ────────────────────────────────────────────────────

    def create_thread(
        self,
        user_id:     int,
        title:       str,
        thread_type: str = "general",
        user_name:   str = None,
        user_email:  str = None
    ) -> Thread:
        """
        Create a new conversation thread.
        Saves user_name and user_email so every thread
        in the DB is clearly linked to a real person.
        """
        thread = Thread(
            user_id     = user_id,
            user_name   = user_name,
            user_email  = user_email,
            title       = title[:200] if title else "Untitled",
            thread_type = thread_type
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        print(f"[Memory] Thread created: '{title[:40]}' for {user_name or user_id}")
        return thread

    # ─── Add Message ──────────────────────────────────────────────────────

    def add_message(
        self,
        thread_id:  int,
        role:       str,
        content:    str,
        user_id:    int  = None,
        user_name:  str  = None,
        metadata:   dict = None
    ) -> Message:
        """
        Save a message to a thread.

        role      : 'user' or 'assistant'
        user_name : stored so every message in DB shows who sent it.
                    For assistant messages pass user_name='AI Advisor'
        metadata  : stored in extra_data column (not metadata — reserved)
        """
        msg = Message(
            thread_id  = thread_id,
            user_id    = user_id,
            user_name  = user_name,
            role       = role,
            content    = content,
            extra_data = metadata or {}
        )
        self.db.add(msg)
        self.db.commit()
        return msg

    # ─── Get History ──────────────────────────────────────────────────────

    def get_history(self, thread_id: int) -> List[Dict[str, str]]:
        """
        Get conversation history for a thread.
        Returns last N messages formatted for LLM.

        Format:
        [
            {"role": "user",      "content": "...", "user_name": "Raj"},
            {"role": "assistant", "content": "...", "user_name": "AI Advisor"}
        ]
        """
        messages = (
            self.db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .all()
        )

        formatted = [
            {
                "role":      m.role,
                "content":   m.content,
                "user_name": m.user_name or ""
            }
            for m in messages
        ]

        return formatted[-self.max_history:]

    # ─── Get History as String ────────────────────────────────────────────

    def get_history_as_string(self, thread_id: int) -> str:
        """
        Get conversation history as plain text string.
        Used for injecting context into agent prompts.
        """
        history = self.get_history(thread_id)

        if not history:
            return "No previous conversation."

        lines = []
        for msg in history:
            role    = msg["role"].upper()
            content = msg["content"]
            lines.append(f"{role}: {content}")

        return "\n\n".join(lines)

    # ─── Get Thread ───────────────────────────────────────────────────────

    def get_thread(self, thread_id: int) -> Optional[Thread]:
        """Get a specific thread by ID."""
        return (
            self.db.query(Thread)
            .filter(Thread.id == thread_id)
            .first()
        )

    # ─── Get User Threads ─────────────────────────────────────────────────

    def get_user_threads(self, user_id: int) -> List[Thread]:
        """Get all threads for a user ordered by newest first."""
        return (
            self.db.query(Thread)
            .filter(Thread.user_id == user_id)
            .order_by(Thread.created_at.desc())
            .all()
        )

    # ─── Message Count ────────────────────────────────────────────────────

    def get_message_count(self, thread_id: int) -> int:
        """Get total number of messages in a thread."""
        return (
            self.db.query(Message)
            .filter(Message.thread_id == thread_id)
            .count()
        )

    # ─── Get All Messages ─────────────────────────────────────────────────

    def get_all_messages(self, thread_id: int) -> List[Message]:
        """Get all raw message objects for a thread."""
        return (
            self.db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .all()
        )


# ─── Long Term Memory ─────────────────────────────────────────────────────────

class LongTermMemory:
    """
    Stores and retrieves financial analysis results
    across sessions for a user.

    Used to:
    - Cache agent analysis results
    - Track health score over time
    - Retrieve last analysis without re-running agents
    """

    def __init__(self, db: Session):
        self.db = db

    # ─── Save Analysis Result ─────────────────────────────────────────────

    def save_analysis_result(
        self,
        user_id:       int,
        analysis_type: str,
        result:        dict
    ):
        """
        Save agent analysis results.
        Merges new results with existing ones.
        """
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        current = {}
        if state and state.last_recommendations:
            current = dict(state.last_recommendations)

        current[analysis_type] = result

        if state:
            state.last_recommendations = current
            state.last_updated         = datetime.utcnow()
        else:
            state = FinancialState(
                user_id              = user_id,
                last_recommendations = current
            )
            self.db.add(state)

        self.db.commit()

    # ─── Get Last Analysis ────────────────────────────────────────────────

    def get_last_analysis(
        self,
        user_id:       int,
        analysis_type: str
    ) -> dict:
        """
        Retrieve last saved analysis results.
        Returns empty dict if not found.
        """
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if not state or not state.last_recommendations:
            return {}

        return state.last_recommendations.get(analysis_type, {})

    # ─── Get All Last Results ─────────────────────────────────────────────

    def get_all_last_results(self, user_id: int) -> dict:
        """
        Get all saved analysis results for a user.
        Returns empty dict if none found.
        """
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if not state or not state.last_recommendations:
            return {}

        return dict(state.last_recommendations)

    # ─── Update Health Score ──────────────────────────────────────────────

    def update_health_score(self, user_id: int, score: float):
        """Update the user's financial health score."""
        self._update_state(user_id, {
            "health_score": round(score, 1)
        })

    # ─── Update Portfolio Value ───────────────────────────────────────────

    def update_portfolio_value(self, user_id: int, value: float):
        """Update the user's total portfolio value."""
        self._update_state(user_id, {
            "portfolio_value": round(value, 2)
        })

    # ─── Update Savings Rate ──────────────────────────────────────────────

    def update_savings_rate(self, user_id: int, rate: float):
        """Update the user's monthly savings rate."""
        self._update_state(user_id, {
            "monthly_savings_rate": round(rate, 2)
        })

    # ─── Update Full State ────────────────────────────────────────────────

    def update_full_state(
        self,
        user_id:         int,
        health_score:    float,
        portfolio_value: float,
        savings_rate:    float
    ):
        """Update all financial state fields at once."""
        self._update_state(user_id, {
            "health_score":         round(health_score,    1),
            "portfolio_value":      round(portfolio_value, 2),
            "monthly_savings_rate": round(savings_rate,    2)
        })

    # ─── Has Analysis ─────────────────────────────────────────────────────

    def has_analysis(self, user_id: int) -> bool:
        """Check if user has any saved analysis results."""
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if not state or not state.last_recommendations:
            return False

        return len(state.last_recommendations) > 0

    # ─── Get Health Score ─────────────────────────────────────────────────

    def get_health_score(self, user_id: int) -> float:
        """Get the user's last saved health score."""
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if not state:
            return 0.0

        return state.health_score or 0.0

    # ─── Internal Update ──────────────────────────────────────────────────

    def _update_state(self, user_id: int, data: dict):
        """Internal helper to update or create financial state."""
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if state:
            for key, val in data.items():
                setattr(state, key, val)
            state.last_updated = datetime.utcnow()
        else:
            state = FinancialState(
                user_id = user_id,
                **data
            )
            self.db.add(state)

        self.db.commit()


# ─── Memory Manager ───────────────────────────────────────────────────────────

class MemoryManager:
    """
    Convenience class that combines both memory systems.
    Single entry point for all memory operations.

    Usage:
        memory = MemoryManager(db)
        memory.conversation.add_message(...)
        memory.long_term.save_analysis_result(...)
    """

    def __init__(self, db: Session):
        self.conversation = ConversationMemory(db)
        self.long_term    = LongTermMemory(db)
        self.db           = db

    def save_full_analysis(
        self,
        user_id:          int,
        analysis_results: dict
    ):
        """
        Save complete analysis results and update
        financial state metrics in one call.
        Called after execute_full_analysis() completes.
        """

        # Save full results
        self.long_term.save_analysis_result(
            user_id       = user_id,
            analysis_type = "full",
            result        = analysis_results
        )

        # Extract and save individual metrics
        health     = analysis_results.get("health",     {})
        investment = analysis_results.get("investment", {})

        health_score    = health.get("overall_score", 0)
        portfolio_value = investment.get("projected_corpus_10yr", 0)

        components   = health.get("components", {})
        savings_comp = components.get("savings_rate", {})
        savings_val  = savings_comp.get("value", "0%")

        try:
            savings_rate = float(
                str(savings_val).replace("%", "").strip()
            )
        except (ValueError, AttributeError):
            savings_rate = 0.0

        self.long_term.update_full_state(
            user_id         = user_id,
            health_score    = health_score,
            portfolio_value = portfolio_value,
            savings_rate    = savings_rate
        )