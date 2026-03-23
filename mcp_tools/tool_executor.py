import traceback
from typing import Any, Dict, Optional
from mcp_tools.tool_registry import get_tool_registry


class ToolExecutor:
    """
    Executes tools from the registry by name.

    Handles:
    - Tool lookup
    - Parameter validation
    - Execution with error handling
    - Result formatting
    """

    def __init__(self):
        self.registry = get_tool_registry()

    # ─── Execute Single Tool ──────────────────────────────────────────────

    def execute(
        self,
        tool_name:  str,
        parameters: dict = None
    ) -> Dict[str, Any]:
        """
        Execute a single tool by name.

        Returns:
        {
            "success":   True,
            "tool":      "tool_name",
            "result":    {...},
            "error":     None
        }
        """
        parameters = parameters or {}

        # ── Look up tool ──────────────────────────────────────────────────
        tool = self.registry.get(tool_name)

        if not tool:
            return {
                "success": False,
                "tool":    tool_name,
                "result":  None,
                "error":   f"Tool '{tool_name}' not found. Available: {self.registry.list_names()}"
            }

        # ── Execute ───────────────────────────────────────────────────────
        try:
            print(f"[ToolExecutor] Running: {tool_name} with {parameters}")
            result = tool.run(**parameters)
            print(f"[ToolExecutor] Done: {tool_name}")

            return {
                "success": True,
                "tool":    tool_name,
                "result":  result,
                "error":   None
            }

        except TypeError as e:
            # Missing or wrong parameters
            error_msg = f"Parameter error for '{tool_name}': {str(e)}"
            print(f"[ToolExecutor] {error_msg}")
            return {
                "success": False,
                "tool":    tool_name,
                "result":  None,
                "error":   error_msg
            }

        except Exception as e:
            error_msg = f"Execution error for '{tool_name}': {str(e)}"
            traceback.print_exc()
            return {
                "success": False,
                "tool":    tool_name,
                "result":  None,
                "error":   error_msg
            }

    # ─── Execute Multiple Tools ───────────────────────────────────────────

    def execute_batch(
        self,
        tool_calls: list
    ) -> list:
        """
        Execute multiple tools in sequence.

        tool_calls format:
        [
            {"tool": "calculate_sip_future_value", "params": {"monthly_amount": 10000, ...}},
            {"tool": "get_portfolio_allocation",   "params": {"age": 28, ...}}
        ]

        Returns list of results in same order.
        """
        results = []

        for call in tool_calls:
            tool_name  = call.get("tool",   "")
            parameters = call.get("params", {})

            result = self.execute(tool_name, parameters)
            results.append(result)

        return results

    # ─── Execute for Profile ──────────────────────────────────────────────

    def run_financial_toolkit(self, profile: dict) -> dict:
        """
        Run the standard set of financial calculation tools
        for a complete user profile.

        Returns all pre-calculated data for agents to use.
        """

        monthly_income   = profile.get("monthly_income",       0)
        monthly_expenses = profile.get("monthly_expenses",     0)
        existing_savings = profile.get("existing_savings",     0)
        existing_invest  = profile.get("existing_investments", 0)
        credit_score     = profile.get("credit_score",         700)
        age              = profile.get("age",                  30)
        risk             = profile.get("risk_tolerance",       "moderate")
        horizon          = profile.get("investment_horizon",   "long")
        employment       = profile.get("employment_type",      "salaried")
        monthly_surplus  = monthly_income - monthly_expenses

        results = {}

        # ── Health Score ──────────────────────────────────────────────────
        health = self.execute("calculate_health_score", {
            "monthly_income":    monthly_income,
            "monthly_expenses":  monthly_expenses,
            "existing_savings":  existing_savings,
            "existing_investments": existing_invest,
            "existing_debts":    profile.get("existing_debts", 0),
            "credit_score":      credit_score,
            "age":               age
        })
        results["health"] = health["result"] if health["success"] else {}

        # ── Emergency Fund ────────────────────────────────────────────────
        emergency = self.execute("calculate_emergency_fund_gap", {
            "monthly_expenses": monthly_expenses,
            "existing_savings": existing_savings
        })
        results["emergency"] = emergency["result"] if emergency["success"] else {}

        # ── Portfolio Allocation ──────────────────────────────────────────
        allocation = self.execute("get_portfolio_allocation", {
            "age":            age,
            "risk_tolerance": risk
        })
        results["allocation"] = allocation["result"] if allocation["success"] else {}

        # ── SIP Projections ───────────────────────────────────────────────
        rec_sip = monthly_income * 0.20   # 20% of income
        sip_10yr = self.execute("calculate_sip_future_value", {
            "monthly_amount": rec_sip,
            "annual_rate":    11,
            "years":          10
        })
        results["sip_10yr"] = sip_10yr["result"] if sip_10yr["success"] else {}

        sip_20yr = self.execute("calculate_sip_future_value", {
            "monthly_amount": rec_sip,
            "annual_rate":    11,
            "years":          20
        })
        results["sip_20yr"] = sip_20yr["result"] if sip_20yr["success"] else {}

        # ── Tax Savings ───────────────────────────────────────────────────
        tax = self.execute("calculate_tax_savings", {
            "monthly_income":   monthly_income,
            "elss_annual":      min(monthly_surplus * 0.3 * 12, 75000),
            "ppf_annual":       min(monthly_surplus * 0.3 * 12, 75000),
            "nps_annual":       50000 if employment == "salaried" else 0,
            "health_insurance": 25000
        })
        results["tax"] = tax["result"] if tax["success"] else {}

        # ── Retirement Corpus ─────────────────────────────────────────────
        retirement = self.execute("calculate_retirement_corpus", {
            "monthly_expenses": monthly_expenses,
            "current_age":      age
        })
        results["retirement"] = retirement["result"] if retirement["success"] else {}

        # ── Risk Score ────────────────────────────────────────────────────
        risk_result = self.execute("calculate_risk_score", {
            "age":                age,
            "employment_type":    employment,
            "investment_horizon": horizon,
            "existing_savings":   existing_savings,
            "monthly_expenses":   monthly_expenses
        })
        results["risk"] = risk_result["result"] if risk_result["success"] else {}

        return results

    # ─── List Tools ───────────────────────────────────────────────────────

    def list_tools(self) -> list:
        """List all available tools."""
        return self.registry.list_all()

    def get_tool_names(self) -> list:
        """Get all tool names."""
        return self.registry.list_names()


# ─── Singleton ────────────────────────────────────────────────────────────────

_executor = None

def get_tool_executor() -> ToolExecutor:
    """Get singleton ToolExecutor instance."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor

