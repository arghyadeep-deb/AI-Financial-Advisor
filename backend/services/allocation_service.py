"""Internal synthetic scenarios only. No router, LLM, trade or external adapter.

Authenticated adapters must supply the current owner, never take it from model
arguments. Public proposal publication stays gated even with a feasible scenario.
"""
from datetime import date
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.feature_flags import allocation_public_eligible
from backend.finance.suitability import Suitability
from backend.knowledge.registry import Registry
from backend.models.models import AllocationPlan, FinancialProfile
from backend.services.output_guard import guard_allocation
from backend.services.profile_service import snapshot_for
from engines.allocation import allocate, evidence_current
from engines.allocation.contracts import AssumptionPack, Constraints, Holding
from engines.allocation.costs import compare, stress


def _profile(db: Session, owner_id: int) -> FinancialProfile:
    profile = db.query(FinancialProfile).filter_by(user_id=owner_id).first()
    if profile is None:
        raise HTTPException(404, "Allocation input not found")
    return profile


def create_scenario(db: Session, *, owner_id: int, expected_revision: int, suitability: Suitability,
                    pack: AssumptionPack, constraints: Constraints, registry: Registry, as_of: date,
                    holdings: tuple[Holding, ...] | None = None, holdings_revision: str | None = None,
                    model_output=None) -> dict:
    profile = _profile(db, owner_id)
    if profile.revision != expected_revision:
        raise HTTPException(409, "Profile changed; recompute scenario")
    if holdings is not None and not holdings_revision:
        raise HTTPException(422, "Holdings revision required")
    snapshot = snapshot_for(profile)
    result = allocate(snapshot, suitability, pack, constraints, registry, owner_id=owner_id, as_of=as_of)
    payload = guard_allocation({"allocation": result.model_dump(mode="json"),
                               "comparison": compare(result, holdings, pack),
                               "stress": stress(result, pack)}, model_output)
    # Recheck persisted revision before publication; do not trust the identity map.
    current = db.query(FinancialProfile.revision).filter_by(user_id=owner_id).scalar()
    if current != expected_revision:
        raise HTTPException(409, "Profile changed; recompute scenario")
    record = AllocationPlan(id=str(uuid4()), user_id=owner_id, profile_revision=expected_revision,
                            suitability_revision=suitability.revision,
                            input_snapshot={"finance": snapshot.to_dict(),
                                            "suitability": suitability.model_dump(mode="json"),
                                            "assumptions": pack.model_dump(mode="json"),
                                            "constraints": constraints.model_dump(mode="json"),
                                            "holdings_revision": holdings_revision,
                                            "holdings": None if holdings is None else [h.model_dump() for h in holdings],
                                            "as_of": as_of.isoformat()}, result=payload)
    db.add(record)
    db.commit()
    return {"id": record.id, **payload}


def read_plan(db: Session, *, owner_id: int, plan_id: str, registry: Registry, as_of: date,
              suitability_revision: int, holdings_revision: str | None = None,
              assumption_version: str | None = None) -> dict:
    record = db.query(AllocationPlan).filter_by(id=plan_id, user_id=owner_id).first()
    if record is None:
        raise HTTPException(404, "Allocation plan not found")
    profile = _profile(db, owner_id)
    pack = AssumptionPack.model_validate_json(json.dumps(record.input_snapshot["assumptions"]))
    stale = (profile.revision != record.profile_revision
             or suitability_revision != record.suitability_revision
             or holdings_revision != record.input_snapshot["holdings_revision"]
             or assumption_version != pack.version
             or not evidence_current(pack, registry, owner_id, as_of))
    return {"id": record.id, "stale": stale, "inputs": record.input_snapshot,
            **guard_allocation(record.result)}


def propose(*args, **kwargs) -> dict:
    if not allocation_public_eligible():
        return {"status": "gated", "reasons": ["D05 and independent release evidence unresolved"]}
    raise RuntimeError("public allocation has no approved implementation")


def sandbox_enabled():
    import os
    return os.getenv('APP_ENV', 'development') in {'test', 'development'} and os.getenv('ALLOCATION_SANDBOX_ENABLED', 'false').lower() == 'true'


def _require_sandbox():
    if not sandbox_enabled():
        raise HTTPException(404, 'Allocation sandbox unavailable.')


def _owned_inputs(db, owner):
    from backend.services import portfolio_service as portfolio, planning_service as planning
    from backend.services.finance_snapshot_service import current_snapshot
    profile = _profile(db, owner)
    holdings = portfolio.get(db, owner, 'holdings')
    answers = portfolio.get(db, owner, 'suitability')
    finance = current_snapshot(db, owner)
    if finance is None:
        raise HTTPException(422, 'Finance snapshot unavailable.')
    return profile, holdings, answers, finance, planning.vector(db, owner)


from backend.finance.ledger import atomic, lock_owner
from backend.core.telemetry import traceable


@atomic
@traceable(name='allocation_sandbox')
def create_owned_scenario(db, owner, payload):
    """Authenticated synthetic sandbox. All revision identities are resolved server-side."""
    _require_sandbox()
    from backend.finance.allocation_sources import synthetic_fixture
    from backend.services import portfolio_service as portfolio
    from engines.allocation.costs import rebalance
    lock_owner(db, owner, bump=False)
    request = payload.model_dump(mode='json')
    # Existing immutable table; owner lock serializes idempotency lookup/publication.
    old = db.query(AllocationPlan).filter(AllocationPlan.user_id == owner,
        AllocationPlan.input_snapshot['request']['idempotency_key'].as_string() == payload.idempotency_key).first()
    if old:
        # Fill added optional defaults for old immutable requests before comparing.
        # Never rewrite the original receipt or recompute its stored allocation.
        prior_request = type(payload).model_validate(old.input_snapshot['request']).model_dump(mode='json')
        if prior_request != request:
            raise HTTPException(409, 'Idempotency key reused with different input.')
        db.rollback()
        return read_owned_plan(db, owner, old.id)
    profile, book, answers, finance, planning = _owned_inputs(db, owner)
    if (payload.expected_revision != 0 or profile.revision != payload.expected_profile_revision or
            book.revision != payload.expected_holdings_revision or answers.revision != payload.expected_suitability_revision or
            planning != payload.expected_planning_vector):
        raise HTTPException(409, 'Input revisions changed; reload before retrying.')
    from sqlalchemy import update
    # ProfileService uses CAS on this row rather than the shared owner lock.
    fence = db.execute(update(FinancialProfile).where(FinancialProfile.user_id == owner,
        FinancialProfile.revision == payload.expected_profile_revision).values(revision=FinancialProfile.revision))
    if fence.rowcount != 1:
        raise HTTPException(409, 'Profile changed; reload before retrying.')
    day = portfolio.today()
    capacity_view = None
    if payload.planning_capacity is not None:
        from dataclasses import replace
        from backend.services.planning_calculations import goal_plan
        if payload.planning_capacity.as_of != day or payload.planning_capacity.expected_planning_vector != planning:
            raise HTTPException(409, 'Capacity inputs must match the current date and planning vector.')
        capacity_view = goal_plan(db, owner, payload.planning_capacity)
        cap = capacity_view['capacity']['available_paise']
        if cap is not None:
            cap = min(cap, capacity_view['unallocated_capacity_paise'])
        if any(g['status'] in {'deadline_passed', 'shortfall'} for g in capacity_view['goals']):
            cap = 0
        # A verified historical shortfall still prevents positive contribution.
        cap = 0 if finance.shortfall_paise else cap
        finance = replace(finance, available_contribution_paise=cap,
            contribution_status='unavailable' if cap is None else 'available' if cap > 0 else 'none',
            contribution_reason='shared planning capacity after goal funding; declared forward assumptions')
    elif planning:
        from dataclasses import replace
        finance = replace(finance, available_contribution_paise=None, contribution_status='unavailable',
            contribution_reason='Shared planning capacity required for existing commitments and goals')
    try:
        pack, registry = synthetic_fixture('v2')
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Synthetic assumptions unavailable; retry after operator review.') from exc
    suitability = Suitability.model_validate_json(json.dumps(answers.data))
    constraints = Constraints(eligible_liquid_paise=payload.eligible_liquid_paise,
        excluded=tuple(payload.excluded_assets), liquidity_floor_bps=payload.liquidity_floor_bps,
        maximum_liquidity_days=payload.maximum_liquidity_days)
    result = allocate(finance, suitability, pack, constraints, registry, owner_id=owner, as_of=day)
    observed = portfolio.valuation_data(book.data, day)
    complete = (observed['total_value_paise'] is not None and not observed['stale'] and
                observed['inventory_complete_declared'] and not any(
                    p['asset_class'] is None for p in book.data['observations'] if not p['closed']))
    holdings = tuple(Holding(asset=a, value_paise=n) for a, n in observed['asset_class_paise'].items()) if complete else None
    target = {a.asset: a.value_paise * 10000 // result.budget_paise for a in result.amounts} if result.budget_paise else {}
    if target:
        target['cash'] += 10000 - sum(target.values())
    output = guard_allocation({'allocation': result.model_dump(mode='json'),
        'comparison': compare(result, holdings, pack), 'stress': stress(result, pack)})
    output['rebalance'] = rebalance(holdings, result.budget_paise, target) if holdings is not None and result.status == 'feasible' else {'status': 'unavailable'}
    # Preserve source coverage and assumptions even when feasibility cannot be established.
    inputs = {'request': request, 'finance': finance.to_dict(), 'suitability': answers.data,
        'holdings': book.data, 'holdings_revision': book.revision, 'planning_vector': planning,
        'assumptions': pack.model_dump(mode='json'), 'as_of': day.isoformat(),
        'constraints': constraints.model_dump(mode='json'), 'holdings_coverage': observed['coverage'],
        'planning_capacity': capacity_view, 'portfolio_rule_version': observed['rule_version']}
    row = AllocationPlan(id=str(uuid4()), user_id=owner, profile_revision=profile.revision,
        suitability_revision=answers.revision, input_snapshot=inputs, result=output)
    db.add(row)
    db.commit()
    return read_owned_plan(db, owner, row.id)


def read_owned_plan(db, owner, identity):
    from backend.finance.allocation_sources import synthetic_fixture
    from backend.services import portfolio_service as portfolio
    from backend.services.finance_snapshot_service import sources_changed
    from engines.portfolio import RULES as portfolio_rules
    row = db.query(AllocationPlan).filter_by(user_id=owner, id=identity).first()
    if row is None:
        raise HTTPException(404, 'Allocation plan not found')
    if 'request' not in row.input_snapshot:
        # Legacy internal-only plans lack owned revision provenance.
        return {'id': row.id, 'status': 'needs_review', 'stale': True, 'public_eligible': False}
    def envelope(reasons):
        return {'id': row.id, 'status': 'hypothetical', 'stale': bool(reasons), 'stale_reasons': reasons,
                'inputs': row.input_snapshot, **row.result, 'public_eligible': False, 'named_products_eligible': False}
    try:
        profile, holdings, answers, finance, planning = _owned_inputs(db, owner)
    except HTTPException as exc:
        if exc.status_code in (404, 422):
            return envelope(['current_inputs_unavailable'])
        raise
    day = portfolio.today()
    try:
        pack, registry = synthetic_fixture('v2')
    except (OSError, ValueError):
        return envelope(['assumptions_unavailable'])
    reasons = []
    for changed, label in ((profile.revision != row.profile_revision, 'profile_changed'),
            (holdings.revision != row.input_snapshot['holdings_revision'], 'holdings_changed'),
            (answers.revision != row.suitability_revision, 'suitability_changed'),
            (planning != row.input_snapshot['planning_vector'], 'planning_changed'),
            (portfolio_rules.version != row.input_snapshot.get('portfolio_rule_version'), 'portfolio_rules_changed'),
            (day.isoformat() != row.input_snapshot['as_of'], 'valuation_date_changed'),
            (pack.model_dump(mode='json') != row.input_snapshot['assumptions'] or
             not evidence_current(pack, registry, owner, day), 'assumptions_changed_or_expired'),
            (sources_changed(db, owner, row.input_snapshot['finance']) or
             finance.source_revision_vector != row.input_snapshot['finance'].get('source_revision_vector', {}), 'finance_sources_changed')):
        if changed:
            reasons.append(label)
    return envelope(reasons)
