from typing import Generator
from sqlalchemy.orm import Session
from langsmith import traceable
from memory.conversation_memory import ConversationMemory, LongTermMemory
from utils.llm_brain import call_llm, stream_llm


class ChatService:
    """
    Handles all chat operations.

    Features:
    - Standard chat (full response at once)
    - Streaming chat (word by word)
    - Knowledge base search per query
    - Full analysis context injection
    - Conversation history with user names saved to DB
    """

    def __init__(self, db: Session):
        self.db          = db
        self.conv_memory = ConversationMemory(db)
        self.lt_memory   = LongTermMemory(db)

    # ─── Thread Management ────────────────────────────────────────────────

    def get_or_create_thread(
        self,
        user_id:    int,
        thread_id:  int,
        message:    str,
        user_name:  str = None,
        user_email: str = None
    ) -> int:
        """
        Get existing thread or create new one.
        Saves user_name and user_email to DB for traceability.
        """
        if thread_id:
            thread = self.conv_memory.get_thread(thread_id)
            if thread and thread.user_id == user_id:
                return thread_id

        thread = self.conv_memory.create_thread(
            user_id     = user_id,
            title       = message[:50],
            thread_type = "chat",
            user_name   = user_name,
            user_email  = user_email
        )
        return thread.id

    # ─── Prompt Builder ───────────────────────────────────────────────────

    def _build_prompts(
        self,
        user_id:   int,
        user_name: str,
        message:   str,
        thread_id: int,
        profile:   dict
    ) -> tuple:
        """
        Build system prompt and user message.
        Shared by both chat() and chat_stream() to avoid duplication.

        Returns: (system_prompt, user_message)
        """

        # ── Get analysis results ──────────────────────────────────────────
        all_results = self.lt_memory.get_all_last_results(user_id)
        full        = all_results.get("full",  {})
        quick       = all_results.get("quick", {})

        health     = full.get("health",     {}) or quick.get("health",     {})
        investment = full.get("investment", {}) or quick.get("investment", {})
        credit     = full.get("credit",     {}) or quick.get("credit",     {})
        summary    = full.get("summary",    {})
        simulation = full.get("simulation", {})
        optimizer  = full.get("optimizer",  {})

        # ── Extract key numbers ───────────────────────────────────────────
        monthly_income   = profile.get("monthly_income",   0)
        monthly_expenses = profile.get("monthly_expenses", 0)
        monthly_surplus  = monthly_income - monthly_expenses

        health_score     = health.get("overall_score",    "not run yet")
        health_grade     = health.get("grade",            "N/A")
        priority_actions = health.get("priority_actions", [])

        total_sip       = investment.get("total_monthly_investment", 0)
        corpus_5yr      = investment.get("projected_corpus_5yr",     0)
        corpus_10yr     = investment.get("projected_corpus_10yr",    0)
        corpus_20yr     = investment.get("projected_corpus_20yr",    0)
        sip_plan        = investment.get("monthly_sip_plan",         [])
        stock_recs      = investment.get("stock_recommendations",    [])
        tax_plan        = investment.get("tax_saving_plan",          {})
        ef_status       = investment.get("emergency_fund_status",    {})
        portfolio_alloc = investment.get("portfolio_allocation",     {})

        top_card      = ""
        card_strategy = ""
        if credit.get("recommendations"):
            top_card      = credit["recommendations"][0].get("card_name", "")
            card_strategy = credit.get("strategy_note", "")

        quick_wins   = summary.get("quick_wins",        [])
        exec_summary = summary.get("executive_summary", "")

        sim_current   = simulation.get("current_trajectory",   {})
        sim_optimized = simulation.get("optimized_trajectory", {})
        opt_opps      = optimizer.get("optimization_opportunities", [])

        # ── Search knowledge base for this query ──────────────────────────
        kb_context = ""
        try:
            from rag.rag_router import route_query
            kb_context = route_query(message, mode="auto")
        except Exception as e:
            print(f"[ChatService] KB search failed: {e}")

        # ── Get conversation history ──────────────────────────────────────
        history      = self.conv_memory.get_history(thread_id)
        history_text = ""
        for msg in history[-8:]:
            role          = user_name if msg["role"] == "user" else "AI Advisor"
            history_text += f"{role}: {msg['content']}\n\n"

        # ── System prompt ─────────────────────────────────────────────────
        system_prompt = f"""You are a warm, friendly AI Financial Advisor for Indian investors.
You are speaking with {user_name}.

YOUR PERSONALITY:
- Conversational and approachable — like a trusted financial friend
- Always specific with Indian Rupee amounts — never vague
- Personalise every answer to this user's exact situation and numbers
- 3 to 6 sentences unless the user explicitly asks for more detail
- Use bullet points only when listing multiple items
- Never give generic advice — always tie back to their specific numbers
- Encourage and motivate — finances can be stressful

=== USER PROFILE ===
Name                 : {user_name}
Age                  : {profile.get('age', 'not set')}
Employment           : {profile.get('employment_type', 'not set')}
Monthly Income       : Rs {monthly_income:,.0f}
Monthly Expenses     : Rs {monthly_expenses:,.0f}
Monthly Surplus      : Rs {monthly_surplus:,.0f}
Risk Tolerance       : {profile.get('risk_tolerance', 'not set')}
Investment Horizon   : {profile.get('investment_horizon', 'not set')}
Financial Goals      : {profile.get('financial_goals', [])}
Credit Score         : {profile.get('credit_score', 'not set')}
Monthly Credit Spend : Rs {profile.get('monthly_credit_spend', 0):,.0f}
Spend Categories     : {profile.get('top_spend_categories', [])}

=== FINANCIAL HEALTH ===
Health Score         : {health_score}/100  (Grade: {health_grade})
Emergency Fund       : {ef_status.get('current_months', 0)} months covered
Emergency Gap        : Rs {ef_status.get('gap_amount', 0):,.0f}
Priority Actions     : {priority_actions[:3]}

=== INVESTMENT PLAN ===
Portfolio Allocation : {portfolio_alloc}
Total Monthly SIP    : Rs {total_sip:,.0f}
SIP Breakdown:
{chr(10).join([f"  - {s.get('instrument', '')}: Rs {s.get('monthly_amount', 0):,.0f}/month ({s.get('expected_return', '')})" for s in sip_plan])}

Corpus Projections:
  5 Years  : Rs {corpus_5yr:,.0f}
  10 Years : Rs {corpus_10yr:,.0f}
  20 Years : Rs {corpus_20yr:,.0f}

Annual Tax Saving    : Rs {tax_plan.get('total_tax_saved_annually', 0):,.0f}

=== STOCK PICKS ===
{chr(10).join([f"  - {s.get('company', '')} ({s.get('symbol', '')}): {s.get('allocation_percent', 0)}% | Hold {s.get('ideal_holding_period', '')}" for s in stock_recs])}

=== CREDIT CARD ===
Best Card            : {top_card}
Strategy             : {card_strategy}

=== WEALTH SIMULATION ===
Current Path 10yr    : Rs {sim_current.get('corpus_10yr', 0):,.0f}
Optimized Path 10yr  : Rs {sim_optimized.get('corpus_10yr', 0):,.0f}
Difference           : Rs {sim_optimized.get('corpus_10yr', 0) - sim_current.get('corpus_10yr', 0):,.0f} extra by optimizing

=== OPTIMIZATION OPPORTUNITIES ===
{chr(10).join([f"  - {o.get('area', '')}: Rs {o.get('annual_benefit_rupees', 0):,.0f}/year benefit" for o in opt_opps[:3]])}

=== QUICK WINS (30 days) ===
{chr(10).join([f"  - {w}" for w in quick_wins[:3]])}

=== EXECUTIVE SUMMARY ===
{exec_summary[:400] if exec_summary else "Analysis not run yet."}

=== CONVERSATION RULES ===
1. WHY questions   → explain using their exact profile numbers
2. HOW questions   → step by step Indian context with platform names
3. WHAT questions  → explain simply with relatable Indian examples
4. If analysis not run → say "Please click Run Analysis on the dashboard first"
5. Never make up numbers — only use what is provided above
6. If the user seems stressed or worried → be extra encouraging and positive
7. Always end with exactly ONE actionable next step they can take today
8. If user asks about a specific stock or card not in their plan → explain why it was or wasn't included"""

        # ── User message with history and KB context ──────────────────────
        user_message = f"""
Previous conversation:
{history_text if history_text else "This is the start of our conversation."}

{user_name} asks: {message}

{f"Relevant knowledge base context:{chr(10)}{kb_context}" if kb_context else ""}
"""
        return system_prompt, user_message

    def _fallback_chat_reply(self, user_name: str, profile: dict) -> str:
        """Fast deterministic fallback when model providers are unavailable."""
        income = profile.get("monthly_income", 0) or 0
        expenses = profile.get("monthly_expenses", 0) or 0
        surplus = max(income - expenses, 0)

        if surplus > 0:
            next_step = f"Set up an auto-transfer of Rs {min(5000, int(surplus * 0.25)):,.0f} today toward emergency fund/SIP."
        else:
            next_step = "Track your top 3 expenses today and cut one discretionary spend this week."

        return (
            f"I am temporarily unable to reach the model providers, {user_name}. "
            f"From your profile, your monthly surplus is about Rs {surplus:,.0f}. "
            f"{next_step}"
        )

    # ─── Standard Chat ────────────────────────────────────────────────────

    @traceable(
        run_type = "chain",
        name     = "chat_agent",
        tags     = ["agent", "chat", "conversational"]
    )
    def chat(
        self,
        user_id:   int,
        user_name: str,
        message:   str,
        thread_id: int,
        profile:   dict
    ) -> dict:
        """
        Standard (non-streaming) chat.
        Returns full reply at once.
        Traced in LangSmith under chat_agent.
        """

        system_prompt, user_message = self._build_prompts(
            user_id   = user_id,
            user_name = user_name,
            message   = message,
            thread_id = thread_id,
            profile   = profile
        )

        # Call LLM
        try:
            reply = call_llm(
                system_prompt = system_prompt,
                user_message  = user_message,
                max_tokens    = 600,
                agent_name    = "chat_agent"
            )
        except Exception as e:
            print(f"[ChatService] chat LLM failed: {e}")
            reply = self._fallback_chat_reply(user_name=user_name, profile=profile)

        # Save messages to DB with user names
        self.conv_memory.add_message(
            thread_id = thread_id,
            role      = "user",
            content   = message,
            user_id   = user_id,
            user_name = user_name
        )
        self.conv_memory.add_message(
            thread_id = thread_id,
            role      = "assistant",
            content   = reply,
            user_id   = None,
            user_name = "AI Advisor"
        )

        return {
            "reply":     reply,
            "thread_id": thread_id
        }

    # ─── Streaming Chat ───────────────────────────────────────────────────

    def chat_stream(
        self,
        user_id:   int,
        user_name: str,
        message:   str,
        thread_id: int,
        profile:   dict
    ) -> Generator[str, None, None]:
        """
        Streaming chat — yields tokens as they arrive from LLM.

        Flow:
        1. Save user message to DB immediately
        2. Stream tokens from LLM one by one
        3. Save complete assistant reply to DB after streaming done

        Frontend renders each token as it arrives —
        user sees the reply being typed in real time.
        """

        system_prompt, user_message = self._build_prompts(
            user_id   = user_id,
            user_name = user_name,
            message   = message,
            thread_id = thread_id,
            profile   = profile
        )

        # Save user message to DB immediately — before streaming starts
        self.conv_memory.add_message(
            thread_id = thread_id,
            role      = "user",
            content   = message,
            user_id   = user_id,
            user_name = user_name
        )

        # Stream from LLM
        full_reply = ""

        for chunk in stream_llm(
            system_prompt = system_prompt,
            user_message  = user_message,
            max_tokens    = 600,
            agent_name    = "chat_agent"
        ):
            full_reply += chunk
            yield chunk

        # Save complete reply to DB after streaming finishes
        if full_reply:
            self.conv_memory.add_message(
                thread_id = thread_id,
                role      = "assistant",
                content   = full_reply,
                user_id   = None,
                user_name = "AI Advisor"
            )