"""Transparent bounded allocator: minima, then target deficits, then spare capacity.

Stable order cash/debt/equity resolves residual paise. Bounds use ceil for minima
and floor for maxima; infeasible integer rounding fails closed. No expected-return
optimization. FinanceSnapshot is supplied by the shared profile/ledger owner.
"""
from datetime import date
import json

from backend.core.money import check_paise
from backend.finance.suitability import Suitability
from backend.knowledge.registry import Registry
from engines.cashflow import FinanceSnapshot
from .contracts import AllocationResult, AssumptionPack, Constraints, Holding


def evidence_current(pack: AssumptionPack, registry: Registry, owner_id: int, as_of: date) -> bool:
    source = registry.resolve(pack.source_id, pack.source_version, "allocation", owner_id=owner_id, as_of=as_of)
    if source is None:
        return False
    try:
        sourced = AssumptionPack.model_validate_json(json.dumps({**json.loads(source.text), "source_hash": source.content_hash}))
    except (ValueError, TypeError):
        return False
    return bool(sourced == pack and source.content_hash == pack.source_hash
                and pack.effective <= as_of < pack.expires
                and source.effective <= pack.effective and pack.expires <= source.expires)


def allocate(snapshot: FinanceSnapshot, suitability: Suitability, pack: AssumptionPack,
             constraints: Constraints, registry: Registry, *, owner_id: int, as_of: date) -> AllocationResult:
    def result(status, reasons, **kw):
        return AllocationResult(status=status, reasons=tuple(reasons), assumption_version=pack.version, **kw)
    if snapshot.owner_id != owner_id:
        raise ValueError("snapshot owner mismatch")
    if not evidence_current(pack, registry, owner_id, as_of):
        return result("insufficient_data", ["Assumptions unavailable, corrected or expired"])
    blockers = suitability.blockers()
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
    bounds = constraints.bounds or pack.assets
    if len(bounds) != 3 or {b.asset for b in bounds} != {b.asset for b in pack.assets}:
        return result("infeasible", ["Unsupported or duplicate asset bounds"])
    canonical = {b.asset: b for b in pack.assets}
    # User bounds may tighten the sourced universe, never relax it.
    lows, highs, targets = {}, {}, {}
    for b in sorted(bounds, key=lambda b: ("cash", "debt", "equity").index(b.asset)):
        source = canonical[b.asset]
        low_bps = max(b.minimum_bps, source.minimum_bps,
                      constraints.liquidity_floor_bps if b.asset == "cash" else 0)
        high_bps = min(b.maximum_bps, source.maximum_bps)
        if b.asset == "equity":
            high_bps = min(high_bps, {"low": 1000, "moderate": 4000, "high": 6000}[suitability.loss_capacity])
            if (suitability.horizon_months < 36 or suitability.income_stable is False
                or (suitability.essential_goal_months is not None and suitability.essential_goal_months < 36)):
                high_bps = 0
        if b.asset in constraints.excluded:
            high_bps = 0
        lows[b.asset] = (budget * low_bps + 9999) // 10000
        highs[b.asset] = budget * high_bps // 10000
        targets[b.asset] = min(highs[b.asset], budget * b.target_bps // 10000)
    if any(lows[a] > highs[a] for a in lows) or sum(lows.values()) > budget or sum(highs.values()) < budget:
        return result("infeasible", ["Bounds, exclusions or liquidity cannot conserve cash"])
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
