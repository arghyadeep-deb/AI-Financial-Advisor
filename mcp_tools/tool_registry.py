from typing import Callable, Dict, Any


# ─── Tool Definition ──────────────────────────────────────────────────────────

class Tool:
    """
    Represents a single callable tool.

    Tools are functions the AI agent can call
    to get specific data or perform calculations.
    """

    def __init__(
        self,
        name:        str,
        description: str,
        fn:          Callable,
        parameters:  dict = None
    ):
        self.name        = name
        self.description = description
        self.fn          = fn
        self.parameters  = parameters or {}

    def run(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return self.fn(**kwargs)

    def to_dict(self) -> dict:
        """Serialize tool definition for LLM tool calling."""
        return {
            "name":        self.name,
            "description": self.description,
            "parameters":  self.parameters
        }


# ─── Tool Registry ────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Central registry of all available tools.

    Tools registered here can be:
    - Called by agents during analysis
    - Listed for LLM to choose from
    - Executed by ToolExecutor
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_all()

    # ─── Registration ─────────────────────────────────────────────────────

    def register(self, tool: Tool):
        """Register a single tool."""
        self._tools[tool.name] = tool
        print(f"[ToolRegistry] Registered: {tool.name}")

    def _register_all(self):
        """Register all built-in tools."""

        # ── Health Tools ──────────────────────────────────────────────────
        self.register(Tool(
            name        = "calculate_health_score",
            description = "Calculate financial health score from user profile",
            fn          = self._tool_health_score,
            parameters  = {
                "monthly_income":   {"type": "number", "required": True},
                "monthly_expenses": {"type": "number", "required": True},
                "existing_savings": {"type": "number", "required": False},
                "credit_score":     {"type": "number", "required": False}
            }
        ))

        self.register(Tool(
            name        = "calculate_emergency_fund_gap",
            description = "Calculate how much more is needed for 6 month emergency fund",
            fn          = self._tool_emergency_gap,
            parameters  = {
                "monthly_expenses": {"type": "number", "required": True},
                "existing_savings": {"type": "number", "required": True}
            }
        ))

        # ── Investment Tools ──────────────────────────────────────────────
        self.register(Tool(
            name        = "calculate_sip_future_value",
            description = "Calculate future value of a monthly SIP investment",
            fn          = self._tool_sip_fv,
            parameters  = {
                "monthly_amount": {"type": "number", "required": True},
                "annual_rate":    {"type": "number", "required": True},
                "years":          {"type": "number", "required": True}
            }
        ))

        self.register(Tool(
            name        = "calculate_required_sip",
            description = "Calculate monthly SIP needed to reach a target corpus",
            fn          = self._tool_required_sip,
            parameters  = {
                "target_amount":  {"type": "number", "required": True},
                "existing":       {"type": "number", "required": False},
                "annual_rate":    {"type": "number", "required": True},
                "years":          {"type": "number", "required": True}
            }
        ))

        self.register(Tool(
            name        = "get_portfolio_allocation",
            description = "Get recommended portfolio allocation based on age and risk",
            fn          = self._tool_portfolio_allocation,
            parameters  = {
                "age":           {"type": "number", "required": True},
                "risk_tolerance":{"type": "string", "required": True}
            }
        ))

        self.register(Tool(
            name        = "calculate_retirement_corpus",
            description = "Calculate retirement corpus needed based on expenses and age",
            fn          = self._tool_retirement_corpus,
            parameters  = {
                "monthly_expenses": {"type": "number", "required": True},
                "current_age":      {"type": "number", "required": True},
                "retirement_age":   {"type": "number", "required": False}
            }
        ))

        # ── Tax Tools ─────────────────────────────────────────────────────
        self.register(Tool(
            name        = "calculate_tax_savings",
            description = "Calculate total tax saved via 80C, 80CCD, 80D deductions",
            fn          = self._tool_tax_savings,
            parameters  = {
                "monthly_income":  {"type": "number", "required": True},
                "elss_annual":     {"type": "number", "required": False},
                "ppf_annual":      {"type": "number", "required": False},
                "nps_annual":      {"type": "number", "required": False},
                "health_insurance":{"type": "number", "required": False}
            }
        ))

        # ── Credit Card Tools ─────────────────────────────────────────────
        self.register(Tool(
            name        = "calculate_card_nry",
            description = "Calculate Net Reward Yield for a credit card",
            fn          = self._tool_card_nry,
            parameters  = {
                "card_name":        {"type": "string", "required": True},
                "monthly_spend":    {"type": "number", "required": True},
                "spend_categories": {"type": "array",  "required": False}
            }
        ))

        self.register(Tool(
            name        = "get_best_cards_for_categories",
            description = "Get best credit cards for specific spending categories",
            fn          = self._tool_best_cards,
            parameters  = {
                "categories":     {"type": "array",  "required": True},
                "monthly_income": {"type": "number", "required": True},
                "monthly_spend":  {"type": "number", "required": False}
            }
        ))

        # ── Knowledge Base Tools ──────────────────────────────────────────
        self.register(Tool(
            name        = "search_knowledge_base",
            description = "Search the financial knowledge base for information",
            fn          = self._tool_search_kb,
            parameters  = {
                "query": {"type": "string", "required": True}
            }
        ))

        self.register(Tool(
            name        = "graph_rag_search",
            description = "Search using Graph RAG traversal for semantic queries",
            fn          = self._tool_graph_rag,
            parameters  = {
                "query": {"type": "string", "required": True}
            }
        ))

        # ── Risk Tools ────────────────────────────────────────────────────
        self.register(Tool(
            name        = "calculate_risk_score",
            description = "Calculate risk score and recommend risk profile",
            fn          = self._tool_risk_score,
            parameters  = {
                "age":                {"type": "number", "required": True},
                "employment_type":    {"type": "string", "required": True},
                "investment_horizon": {"type": "string", "required": True},
                "existing_savings":   {"type": "number", "required": False},
                "monthly_expenses":   {"type": "number", "required": False}
            }
        ))

        # ── Market Data Tools ─────────────────────────────────────────────
        self.register(Tool(
            name        = "get_stock_info",
            description = "Get information about a stock or ETF from knowledge base",
            fn          = self._tool_stock_info,
            parameters  = {
                "ticker": {"type": "string", "required": True}
            }
        ))

        self.register(Tool(
            name        = "get_investment_info",
            description = "Get information about an investment instrument",
            fn          = self._tool_investment_info,
            parameters  = {
                "name": {"type": "string", "required": True}
            }
        ))

    # ─── Tool Getter ──────────────────────────────────────────────────────

    def get(self, name: str) -> Tool:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> list:
        """List all registered tools."""
        return [t.to_dict() for t in self._tools.values()]

    def list_names(self) -> list:
        """List all tool names."""
        return list(self._tools.keys())

    # ─── Tool Implementations ─────────────────────────────────────────────

    def _tool_health_score(self, **kwargs) -> dict:
        from engines.financial_health_engine import FinancialHealthEngine
        engine = FinancialHealthEngine()
        return engine.calculate(kwargs)

    def _tool_emergency_gap(self, **kwargs) -> dict:
        monthly_expenses = kwargs.get("monthly_expenses", 0)
        existing_savings = kwargs.get("existing_savings", 0)
        needed           = monthly_expenses * 6
        gap              = max(0, needed - existing_savings)
        months_covered   = (existing_savings / monthly_expenses) if monthly_expenses > 0 else 0
        return {
            "emergency_needed":  round(needed),
            "current_savings":   round(existing_savings),
            "gap":               round(gap),
            "months_covered":    round(months_covered, 1),
            "monthly_save_needed": round(gap / 12) if gap > 0 else 0,
            "status": "adequate" if gap <= 0 else "needs_work"
        }

    def _tool_sip_fv(self, **kwargs) -> dict:
        from engines.investment_engine import InvestmentEngine
        engine  = InvestmentEngine()
        monthly = kwargs.get("monthly_amount", 0)
        rate    = kwargs.get("annual_rate",    10)
        years   = kwargs.get("years",          10)
        fv      = engine.fv_sip(monthly, rate, years)
        return {
            "monthly_amount":  monthly,
            "annual_rate":     rate,
            "years":           years,
            "future_value":    fv,
            "total_invested":  round(monthly * years * 12),
            "wealth_created":  round(fv - (monthly * years * 12))
        }

    def _tool_required_sip(self, **kwargs) -> dict:
        from engines.investment_engine import InvestmentEngine
        engine   = InvestmentEngine()
        target   = kwargs.get("target_amount", 0)
        existing = kwargs.get("existing",      0)
        rate     = kwargs.get("annual_rate",   10)
        years    = kwargs.get("years",         10)
        req_sip  = engine.required_sip(target, existing, rate, years)
        return {
            "target_amount":    target,
            "existing":         existing,
            "annual_rate":      rate,
            "years":            years,
            "required_monthly": req_sip
        }

    def _tool_portfolio_allocation(self, **kwargs) -> dict:
        from engines.investment_engine import InvestmentEngine
        engine  = InvestmentEngine()
        profile = {
            "age":            kwargs.get("age",            30),
            "risk_tolerance": kwargs.get("risk_tolerance", "moderate")
        }
        return engine.get_allocation(profile)

    def _tool_retirement_corpus(self, **kwargs) -> dict:
        from engines.investment_engine import InvestmentEngine
        engine = InvestmentEngine()
        return engine.retirement_corpus_needed(
            monthly_expenses = kwargs.get("monthly_expenses", 30000),
            current_age      = kwargs.get("current_age",      30),
            retirement_age   = kwargs.get("retirement_age",   60)
        )

    def _tool_tax_savings(self, **kwargs) -> dict:
        monthly_income   = kwargs.get("monthly_income",   0)
        elss_annual      = kwargs.get("elss_annual",      0)
        ppf_annual       = kwargs.get("ppf_annual",       0)
        nps_annual       = kwargs.get("nps_annual",       0)
        health_insurance = kwargs.get("health_insurance", 25000)

        tax_bracket = 0.30 if monthly_income > 100000 else 0.20 if monthly_income > 50000 else 0.05

        total_80c       = min(elss_annual + ppf_annual, 150000)
        total_80ccd     = min(nps_annual, 50000)
        total_80d       = min(health_insurance, 25000)

        tax_saved_80c   = round(total_80c   * tax_bracket)
        tax_saved_80ccd = round(total_80ccd * tax_bracket)
        tax_saved_80d   = round(total_80d   * tax_bracket)
        total_saved     = tax_saved_80c + tax_saved_80ccd + tax_saved_80d

        return {
            "tax_bracket_percent":  int(tax_bracket * 100),
            "section_80C": {
                "invested": total_80c,
                "tax_saved": tax_saved_80c
            },
            "section_80CCD_1B": {
                "invested": total_80ccd,
                "tax_saved": tax_saved_80ccd
            },
            "section_80D": {
                "invested": total_80d,
                "tax_saved": tax_saved_80d
            },
            "total_tax_saved_annually": total_saved,
            "monthly_tax_saved": round(total_saved / 12)
        }

    def _tool_card_nry(self, **kwargs) -> dict:
        from engines.reward_engine import RewardEngine
        from rag.kb_loader import load_credit_cards

        card_name    = kwargs.get("card_name",        "")
        monthly_spend = kwargs.get("monthly_spend",   0)
        categories   = kwargs.get("spend_categories", [])

        # Find card by name
        cards = load_credit_cards()
        card  = next(
            (c for c in cards if card_name.lower() in c.get("card_name", "").lower()),
            None
        )

        if not card:
            return {"error": f"Card '{card_name}' not found in knowledge base"}

        engine = RewardEngine()
        return engine.calculate_nry(
            card             = card,
            monthly_spend    = monthly_spend,
            spend_categories = categories
        )

    def _tool_best_cards(self, **kwargs) -> dict:
        from engines.reward_engine import RewardEngine
        engine = RewardEngine()
        profile = {
            "monthly_income":       kwargs.get("monthly_income",  0),
            "monthly_credit_spend": kwargs.get("monthly_spend",   0),
            "top_spend_categories": kwargs.get("categories",      [])
        }
        cards = engine.compare_cards(profile)
        return {"top_cards": cards[:5]}

    def _tool_search_kb(self, **kwargs) -> dict:
        from rag.rag_pipeline import search_knowledge_base
        query   = kwargs.get("query", "")
        results = search_knowledge_base(query)
        return {"results": results, "query": query}

    def _tool_graph_rag(self, **kwargs) -> dict:
        from rag.rag_router import route_query
        query   = kwargs.get("query", "")
        results = route_query(query, mode="graph")
        return {"results": results, "query": query}

    def _tool_risk_score(self, **kwargs) -> dict:
        from engines.risk_engine import RiskEngine
        engine = RiskEngine()
        return engine.calculate_risk_score(kwargs)

    def _tool_stock_info(self, **kwargs) -> dict:
        from rag.kb_loader import load_stocks
        ticker = kwargs.get("ticker", "").upper()
        stocks = load_stocks()
        stock  = next(
            (s for s in stocks if s.get("ticker", "").upper() == ticker),
            None
        )
        if not stock:
            return {"error": f"Stock '{ticker}' not found"}
        return stock

    def _tool_investment_info(self, **kwargs) -> dict:
        from rag.kb_loader import load_investments
        name        = kwargs.get("name", "").lower()
        investments = load_investments()
        inv         = next(
            (i for i in investments if name in i.get("name", "").lower()),
            None
        )
        if not inv:
            return {"error": f"Investment '{name}' not found"}
        return inv


# ─── Singleton ────────────────────────────────────────────────────────────────

_registry = None

def get_tool_registry() -> ToolRegistry:
    """Get singleton ToolRegistry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry