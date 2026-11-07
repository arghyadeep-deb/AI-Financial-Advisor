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


def rebalance(holdings: tuple[Holding, ...], contribution_paise: int, target_bps: dict[str, int]) -> dict:
    """Asset-class arithmetic only. Targets are user-selected hypothetical weights.

    Floor target amounts, residual paise in cash/debt/equity order. Fill target
    deficits with contributions first; any leftover contribution stays in cash.
    Sale alternative is a comparison, never a transaction instruction.
    """
    assets = ('cash', 'debt', 'equity')
    check_paise(contribution_paise)
    if contribution_paise < 0 or set(target_bps) != set(assets) or any(
            type(n) is not int or not 0 <= n <= 10000 for n in target_bps.values()) or sum(target_bps.values()) != 10000:
        raise ValueError('Invalid hypothetical target or contribution')
    if len({h.asset for h in holdings}) != len(holdings):
        raise ValueError('Duplicate asset classes')
    current = {a: sum(h.value_paise for h in holdings if h.asset == a) for a in assets}
    total = sum_paise([*current.values(), contribution_paise])
    targets = {a: total * target_bps[a] // 10000 for a in assets}
    residual = total - sum(targets.values())
    for a in assets[:residual]:
        targets[a] += 1
    additions = dict.fromkeys(assets, 0)
    remaining = contribution_paise
    for a in assets:
        additions[a] = min(remaining, max(0, targets[a] - current[a]))
        remaining -= additions[a]
    additions['cash'] += remaining
    delta = {a: targets[a] - current[a] for a in assets}
    return {'status': 'hypothetical', 'rule_version': 'rebalance.v1', 'target_bps': target_bps,
        'current_paise': current, 'target_paise': targets, 'total_after_contribution_paise': total,
        'contribution_first': {'additions_paise': additions, 'sales_paise': 0,
            'result_paise': {a: current[a] + additions[a] for a in assets}},
        'sale_alternative': {'delta_paise': delta, 'sales_paise': sum(-n for n in delta.values() if n < 0)},
        'tax_cost_paise': None, 'transaction_cost_paise': None, 'exit_load_paise': None,
        'net_improvement': None, 'execution_enabled': False}
