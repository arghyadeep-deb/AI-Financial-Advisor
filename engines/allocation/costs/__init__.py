"""Comparison arithmetic; unknown sale taxes cannot establish net improvement."""
from backend.core.money import check_paise, sum_paise
from engines.allocation.contracts import AllocationResult, AssumptionPack, Holding


def compare(plan: AllocationResult, holdings: tuple[Holding, ...] | None, pack: AssumptionPack,
            *, sale_paise: int = 0, cost_basis_paise: int | None = None) -> dict:
    check_paise(sale_paise)
    if sale_paise < 0:
        raise ValueError("sale cannot be negative")
    if cost_basis_paise is not None:
        check_paise(cost_basis_paise)
        if cost_basis_paise < 0:
            raise ValueError("basis cannot be negative")
    if holdings is not None and len({h.asset for h in holdings}) != len(holdings):
        raise ValueError("duplicate holdings")
    if plan.status != "feasible":
        return {"status": "unavailable", "net_improvement": None}
    fees = {a.asset: a.annual_fee_bps for a in pack.assets}
    # Aggregate exact numerators, then ceil once for conservative annual estimate.
    fee = (sum(h.value_paise * fees[h.asset] for h in plan.amounts) + 9999) // 10000
    current = None if holdings is None else {h.asset: h.value_paise for h in holdings}
    total = None if holdings is None else sum_paise(h.value_paise for h in holdings)
    return {"status": "partial", "current_allocation_paise": current,
            "contribution_first": {"sales_paise": 0, "annual_fee_estimate_paise": fee,
                                   "allocation_paise": {h.asset: h.value_paise for h in plan.amounts}},
            "baseline": {"rule": "retain_holdings_add_contribution_to_cash.v1",
                         "existing_holdings_paise": current, "new_cash_paise": plan.budget_paise},
            "current_value_paise": total, "sale_alternative_paise": sale_paise,
            "cost_basis_status": "unknown" if cost_basis_paise is None else "supplied_unverified",
            "tax_cost_paise": None, "exit_load_paise": None, "transaction_cost_paise": None,
            "excluded_costs": ["tax: no supported disposal rule pack", "exit loads", "transaction costs"],
            "net_improvement": None}


def stress(plan: AllocationResult, pack: AssumptionPack) -> dict:
    if plan.status != "feasible":
        return {"status": "unavailable"}
    assumptions = {b.asset: b for b in pack.assets}
    low = sum(h.value_paise * (10000 + assumptions[h.asset].adverse_return_bps) for h in plan.amounts) // 10000
    high = sum(h.value_paise * (10000 + assumptions[h.asset].favourable_return_bps) for h in plan.amounts) // 10000
    return {"status": "synthetic_sensitivity", "adverse_terminal_paise": low,
            "favourable_terminal_paise": high, "delayed_income_new_contribution_paise": 0,
            "horizon_months": 12, "volatility_model": "unavailable; bounded shocks only",
            "guaranteed": False}
