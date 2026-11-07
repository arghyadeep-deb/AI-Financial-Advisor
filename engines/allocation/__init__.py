"""Transparent bounded allocator: minima, then target deficits, then spare capacity.

Stable order cash/debt/equity/gold resolves residual paise. Bounds use ceil for minima
and floor for maxima; infeasible integer rounding fails closed. No expected-return
optimization. FinanceSnapshot is supplied by the shared profile/ledger owner.
"""
from datetime import date
import json

from backend.finance.allocation_assumptions import load_register
from backend.core.money import check_paise
from backend.finance.suitability import Suitability
from backend.knowledge.registry import Registry
from engines.cashflow import FinanceSnapshot
from .contracts import ASSET_ORDER, AllocationResult, AssumptionPack, Constraints, Holding


def evidence_current(pack: AssumptionPack, registry: Registry, owner_id: int, as_of: date) -> bool:
    source = registry.resolve(pack.source_id, pack.source_version, "allocation", owner_id=owner_id, as_of=as_of)
    if source is None:
        return False
    try:
        sourced = AssumptionPack.model_validate_json(json.dumps({**json.loads(source.text), "source_hash": source.content_hash}))
    except (ValueError, TypeError):
        return False
    return bool(sourced == pack and source.content_hash == pack.source_hash
                and pack.register is not None and all(a.current(as_of) for a in pack.register.assumptions)
                and pack.effective <= as_of < pack.expires
                and source.effective <= pack.effective and pack.expires <= source.expires)


def allocate(snapshot: FinanceSnapshot, suitability: Suitability, pack: AssumptionPack,
             constraints: Constraints, registry: Registry, *, owner_id: int, as_of: date, synthetic_test: bool = False) -> AllocationResult:
    if snapshot.owner_id != owner_id:
        raise ValueError("snapshot owner mismatch")
    try:
        policy = load_register()
    except (OSError, ValueError):
        policy = None
    configured = {'cash_floor_bps': constraints.liquidity_floor_bps,
                  'near_term_months': constraints.near_term_months}
    liquidity = {b.asset: b.liquidity_days if b.liquidity_evidence is not None
                 and b.liquidity_evidence.as_of <= as_of < b.liquidity_evidence.expires else None
                 for b in pack.assets}
    def result(status, reasons, **kw):
        return AllocationResult(status=status, reasons=tuple(reasons), assumption_version=pack.version, policy_assumptions=() if policy is None else policy.assumptions,
                                policy_configuration=configured, liquidity_days=liquidity, **kw)
    if not synthetic_test:
        return result("gated", ["assumptions not validated"])
    import os
    if os.getenv('APP_ENV') != 'test':
        return result("gated", ["Synthetic fixtures are for tests only; assumptions not validated"])
    if not evidence_current(pack, registry, owner_id, as_of):
        return result("insufficient_data", ["Assumptions unavailable, corrected or expired"])
    if policy is None or not all(a.current(as_of) for a in policy.assumptions):
        return result("insufficient_data", ["Prototype policy assumptions unavailable or expired"])
    blockers = suitability.blockers(near_term_months=constraints.near_term_months)
    if blockers:
        return result("insufficient_data", blockers)
    if snapshot.shortfall_paise > 0 or snapshot.contribution_status == "none":
        return result("infeasible", ["No affordable contribution"])
    cap = snapshot.available_contribution_paise
    if snapshot.contribution_status != "available" or cap is None:
        return result("insufficient_data", ["Contribution unavailable"])
    check_paise(cap)
    if cap <= 0:
        return result("infeasible", ["No affordable contribution"])
    if constraints.eligible_liquid_paise is None:
        return result("insufficient_data", ["Declare eligible liquid cash after commitments and reserves"])
    budget = min(cap, constraints.eligible_liquid_paise)
    if budget == 0:
        return result("infeasible", ["No eligible liquid cash"])
    bounds = pack.assets if constraints.bounds is None else constraints.bounds
    if len(bounds) != len(pack.assets) or {b.asset for b in bounds} != {b.asset for b in pack.assets}:
        return result("infeasible", ["Unsupported or duplicate asset bounds"])
    if not set(constraints.excluded).issubset({b.asset for b in pack.assets}):
        return result("infeasible", ["Exclusion outside the sourced universe"])
    canonical = {b.asset: b for b in pack.assets}
    # User bounds may tighten the sourced universe, never relax it.
    lows, highs, targets = {}, {}, {}
    for b in sorted(bounds, key=lambda b: ASSET_ORDER.index(b.asset)):
        source = canonical[b.asset]
        low_bps = max(b.minimum_bps, source.minimum_bps,
                      constraints.liquidity_floor_bps if b.asset == "cash" else 0)
        high_bps = min(b.maximum_bps, source.maximum_bps)
        if b.asset in {"equity", "gold"}:
            risk = next((r for r in pack.risk_limits if r.asset == b.asset), None)
            if risk is None:
                return result("insufficient_data", ["Risk assumptions unavailable"])
            caps = risk.model_dump()
            high_bps = min(high_bps, caps[suitability.loss_capacity], caps[suitability.loss_tolerance])
            if (suitability.horizon_months < constraints.near_term_months or suitability.income_stable is False
                or (suitability.essential_goal_months is not None and suitability.essential_goal_months < constraints.near_term_months)):
                high_bps = 0
        if b.asset in constraints.excluded:
            high_bps = 0
        if constraints.maximum_liquidity_days is not None and (liquidity[b.asset] is None
                or liquidity[b.asset] > constraints.maximum_liquidity_days):
            high_bps = 0
        lows[b.asset] = (budget * low_bps + 9999) // 10000
        highs[b.asset] = budget * high_bps // 10000
        targets[b.asset] = min(highs[b.asset], budget * b.target_bps // 10000)
    if any(lows[a] > highs[a] for a in lows) or sum(lows.values()) > budget or sum(highs.values()) < budget:
        return result("infeasible", ["Bounds, exclusions or unknown/unsupported liquidity cannot conserve cash"])
    amounts = dict(lows)
    remaining = budget - sum(amounts.values())
    for limits in (targets, highs):
        for a in amounts:
            add = min(remaining, max(0, limits[a] - amounts[a]))
            amounts[a] += add
            remaining -= add
    assert remaining == 0 and sum(amounts.values()) == budget
    binding = tuple(a for a in amounts if amounts[a] in (lows[a], highs[a]))
    return result("feasible", [], budget_paise=budget,
                  amounts=tuple(Holding(asset=a, value_paise=n) for a, n in amounts.items()),
                  binding_constraints=binding)
