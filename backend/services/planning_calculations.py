"""Revision-bound planning estimates from confirmed obligations and declared assumptions."""
from datetime import date, timedelta
from datetime import datetime
import calendar
from zoneinfo import ZoneInfo
from uuid import uuid4
from fastapi import HTTPException
from backend.core.money import check_paise
from backend.finance.ledger import atomic, lock_owner
from backend.services import planning_service as store, monthly_report_service as reports
from backend.models.models import PlanningRevision
from engines.cashflow import flow_capacity_paise
from engines.planning import goal_requirements, debt_schedule


def capacity(db, owner, payload):
    report = reports.read(db, owner, payload.report_id)
    if payload.expected_planning_vector != store.vector(db, owner):
        raise HTTPException(409, 'Planning inputs changed; reload the planning vector.')
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    if payload.evidence_date != today:
        raise HTTPException(422, 'Forward assumptions must be confirmed with today\'s evidence date.')
    obligations = store.active_rows(db, owner, 'obligation')
    active = {r.resource_id: r for r in obligations if not r.data['paused']}
    included = payload.included_obligation_ids
    if len(included) != len(set(included)) or not set(included) <= set(active):
        raise HTTPException(422, 'Included obligations must be distinct current confirmed IDs.')
    # These IDs assert payments already included in the declared forward spending.
    included_total = sum((active[k].data['amount_paise']+11)//12 if active[k].data['cadence'] == 'annual'
                         else active[k].data['amount_paise'] for k in included)
    if included_total > payload.spending_paise:
        raise HTTPException(422, 'Included payments exceed declared spending.')
    unfunded_flow, unfunded_cash = 0, 0
    needs_review = []
    for identity, row in active.items():
        data = row.data
        due = date.fromisoformat(data['due_date'])
        matches = [s for s in store.current(db, owner, 'settlement') if s.data['obligation_id'] == identity]
        if any(not s.data['reversed'] and not store.settlement_valid(db, owner, s) for s in matches):
            needs_review.append(identity)
        paid = sum(-store.owned(db, store.LedgerEntry, owner, s.data['entry_id']).amount_paise
            for s in matches if store.settlement_valid(db, owner, s))
        outstanding = max(0, data['amount_paise']-paid)
        if identity not in included:
            flow = ((data['amount_paise']+11)//12 if data['cadence'] == 'annual' else
                    data['amount_paise'] if data['cadence'] == 'monthly' else outstanding)
            unfunded_flow = check_paise(unfunded_flow+flow)
        if data['cadence'] != 'once' and (today-due).days > (31 if data['cadence'] == 'monthly' else 366):
            needs_review.append(identity)
        if paid >= data['amount_paise'] and data['cadence'] != 'once':
            if data['cadence'] == 'monthly':
                year, month = due.year+(due.month == 12), due.month % 12+1
            else:
                year, month = due.year+1, due.month
            due = date(year, month, min(due.day, calendar.monthrange(year, month)[1]))
            outstanding = data['amount_paise']
        # Current liquid cash has already lost historical payments. Only unpaid
        # upcoming/overdue commitments are removed from today's liquid amount.
        if due <= today+timedelta(days=31):
            unfunded_cash = check_paise(unfunded_cash+outstanding)
    flow = flow_capacity_paise(payload.income_paise, payload.spending_paise, unfunded_flow,
                               payload.reserve_funding_paise+payload.earmarks_paise)
    liquid = payload.eligible_liquid_paise-unfunded_cash-payload.reserve_funding_paise-payload.earmarks_paise
    snapshot = report['snapshot']
    verified = snapshot['selected_scope_complete'] and snapshot['metrics']['classification_complete']
    available = (payload.assumptions_confirmed and payload.obligations_complete and verified and
                 not report['stale'] and not needs_review)
    deficit = payload.income_paise < payload.spending_paise or snapshot['metrics']['shortfall_paise'] > 0
    amount = 0 if deficit else max(0, min(flow, liquid)) if available else None
    return {'available_paise': amount, 'flow_capacity_paise': check_paise(flow),
        'liquid_capacity_paise': check_paise(liquid), 'unfunded_flow_paise': unfunded_flow,
        'unfunded_cash_paise': unfunded_cash, 'status': 'deficit' if deficit else 'declared_estimate' if available else 'unavailable',
        'reason': 'user_confirmed_future_assumptions' if available else 'current_verified_report_and_complete_forward_assumptions_required',
        'report_id': report['id'], 'report_stale': report['stale'], 'planning_vector': store.vector(db, owner),
        'obligations_needing_review': sorted(set(needs_review)),
        'rule_version': 'planning.v1'}


def goal_plan(db, owner, payload):
    cap = capacity(db, owner, payload)
    goals = [{**r.data, 'id': r.resource_id} for r in store.active_rows(db, owner, 'goal')]
    allocated = sum(g['allocated_paise'] for g in goals)
    if allocated > payload.eligible_liquid_paise:
        raise HTTPException(422, 'Goals allocate the same liquid cash more than once.')
    # Previously allocated goal cash is unavailable for new monthly contributions.
    available = cap['available_paise']
    if available is not None:
        available = max(0, min(available, cap['liquid_capacity_paise']-allocated))
    return {'capacity': cap, **goal_requirements(goals, payload.as_of, available),
            'reserve': {'months': payload.reserve_months, 'essential_expenses_paise': payload.essential_expenses_paise,
                        'target_paise': check_paise(payload.reserve_months*payload.essential_expenses_paise),
                        'basis': 'user_selected; default six months is illustrative'},
            'assumptions': payload.model_dump(mode='json')}


@atomic
def scenario(db, owner, payload):
    request = payload.model_dump(mode='json')
    # Scenario request contract uses the same idempotency envelope as resource writes.
    key = payload.idempotency_key
    prior = store.replay(db, owner, request, key)
    if prior:
        return store.describe(prior)
    lock_owner(db, owner, bump=False)
    prior = store.replay(db, owner, request, key)
    if prior:
        db.rollback()
        return store.describe(prior)
    cap = capacity(db, owner, payload)
    debts = [{**r.data, 'id': r.resource_id} for r in store.active_rows(db, owner, 'debt')]
    for debt in debts:
        obligation = store.get(db, owner, 'obligation', debt['obligation_id'])
        if obligation.data['archived'] or obligation.data['paused'] or obligation.data['amount_paise'] != debt['minimum_payment_paise']:
            raise HTTPException(409, 'Debt obligation changed; reconfirm debt terms.')
    if payload.extra_payment_paise and (cap['available_paise'] is None or payload.extra_payment_paise > cap['available_paise']):
        raise HTTPException(422, 'Extra payments exceed available capacity.')
    result = debt_schedule(debts, payload.strategy, payload.extra_payment_paise, payload.max_months)
    if any(d['evidence_date'] > payload.evidence_date.isoformat() or
           (payload.evidence_date-date.fromisoformat(d['evidence_date'])).days > 31 for d in debts):
        result = {'status': 'incomplete', 'reason': 'debt_evidence_stale', 'schedule': []}
    row = PlanningRevision(id=str(uuid4()), user_id=owner, resource_id=str(uuid4()), kind='debt_scenario', revision=1,
        operation_key=key, request=request, data={'capacity': cap, 'assumptions': request, 'debts': debts, 'result': result})
    db.add(row)
    db.commit()
    return store.describe(row)
