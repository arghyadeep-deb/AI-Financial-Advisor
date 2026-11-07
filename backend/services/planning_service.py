"""Single revision store for typed offline planning, using the ledger's owner lock.

Splits remain owned by ledger.split. No model, provider, payment or trade path.
"""
from collections import defaultdict
from datetime import date, datetime, time
from uuid import uuid4
from fastapi import HTTPException
from backend.core.money import check_paise
from backend.finance.ledger import atomic, lock_owner
from backend.models.models import PlanningRevision, LedgerEntry, LedgerLink, LedgerCorrection, StatementAccount
from backend.services.statement_service import owned


def current(db, owner, kind=None):
    query = db.query(PlanningRevision).filter_by(user_id=owner)
    if kind:
        query = query.filter_by(kind=kind)
    latest = {}
    for row in query.order_by(PlanningRevision.revision):
        latest[row.resource_id] = row
    return sorted(latest.values(), key=lambda r: r.resource_id)


def vector(db, owner):
    return {r.resource_id: r.revision for r in current(db, owner) if r.kind != 'debt_scenario'}


def get(db, owner, kind, identity, revision=None):
    query = db.query(PlanningRevision).filter_by(user_id=owner, kind=kind, resource_id=identity)
    if revision is not None:
        query = query.filter_by(revision=revision)
    row = query.order_by(PlanningRevision.revision.desc()).first()
    if not row:
        raise HTTPException(404, 'Resource not found.')
    return row


def describe(row):
    return {'id': row.resource_id, 'kind': row.kind, 'revision': row.revision,
            'data': row.data, 'created_at': row.created_at.isoformat()}


def replay(db, owner, request, key):
    row = db.query(PlanningRevision).filter_by(user_id=owner, operation_key=key).first()
    if row and row.request != request:
        raise HTTPException(409, 'Idempotency key reused with different input.')
    return row


def active_rows(db, owner, kind):
    return [r for r in current(db, owner, kind) if not r.data.get('archived')]


def settlement_valid(db, owner, row):
    data = row.data
    entry = db.query(LedgerEntry).filter_by(user_id=owner, id=data['entry_id'], active=True).first()
    obligation = get(db, owner, 'obligation', data['obligation_id'])
    return (not data['reversed'] and entry is not None and entry.revision == data['expected_entry_revision']
            and obligation.revision == data['expected_obligation_revision'])


@atomic
def write(db, owner, kind, payload, identity=None):
    # Check ownership before idempotency to preserve indistinguishable 404s.
    if identity:
        get(db, owner, kind, identity)
    request = {'kind': kind, 'target': identity, **payload.model_dump(mode='json')}
    prior = replay(db, owner, request, payload.idempotency_key)
    if prior:
        return describe(prior)
    lock_owner(db, owner, bump=False)
    prior = replay(db, owner, request, payload.idempotency_key)
    if prior:
        db.rollback()
        return describe(prior)
    before = get(db, owner, kind, identity) if identity else None
    revision = before.revision if before else 0
    if revision != payload.expected_revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')
    data = payload.data.model_dump(mode='json')
    validate(db, owner, kind, data, identity, before)
    row = PlanningRevision(id=str(uuid4()), user_id=owner, kind=kind,
        resource_id=identity or str(uuid4()), revision=revision + 1,
        operation_key=payload.idempotency_key, request=request, data=data)
    db.add(row)
    if kind == 'obligation' and data['reminder_opt_in'] and not data['paused'] and not data['archived']:
        from backend.services.notification_service import schedule
        # Notification worker rechecks this exact revision before delivery.
        schedule(db, owner, row.resource_id + ':' + str(row.revision), 'reminder',
                 datetime.combine(date.fromisoformat(data['due_date']), time(3, 30)))
    if kind == 'goal' and data['reminder_opt_in'] and not data['archived'] and data['allocated_paise'] < data['target_paise']:
        from backend.services.notification_service import schedule
        schedule(db, owner, 'goal:' + row.resource_id + ':' + str(row.revision), 'reminder',
                 datetime.combine(date.fromisoformat(data['target_date']), time(3, 30)))
    db.commit()
    return describe(row)


def validate(db, owner, kind, data, identity, before):
    if kind == 'budget':
        if any(r.resource_id != identity and r.data['month'] == data['month'] and not r.data['archived']
               for r in current(db, owner, 'budget')) and not data['archived']:
            raise HTTPException(409, 'An active budget already exists for this month.')
        check_paise(sum(data['lines'].values()))
    elif kind == 'obligation':
        for entry_id in data['candidate_entry_ids']:
            entry = owned(db, LedgerEntry, owner, entry_id)
            if not entry.active or entry.amount_paise >= 0:
                raise HTTPException(422, 'Candidate evidence must be an active debit.')
    elif kind == 'settlement':
        obligation = get(db, owner, 'obligation', data['obligation_id'])
        entry = owned(db, LedgerEntry, owner, data['entry_id'])
        if before and any(before.data[k] != data[k] for k in ('entry_id', 'obligation_id')):
            raise HTTPException(422, 'Reverse a settlement before creating a different match.')
        if data['reversed'] and before is None:
            raise HTTPException(422, 'A new settlement cannot be reversed.')
        if not data['reversed']:
            if obligation.data['paused'] or obligation.data['archived'] or not entry.active or entry.amount_paise >= 0:
                raise HTTPException(422, 'Settlement requires an active obligation and debit.')
            if entry.revision != data['expected_entry_revision']:
                raise HTTPException(409, 'Payment evidence changed.')
            if obligation.revision != data['expected_obligation_revision']:
                raise HTTPException(409, 'Obligation changed; reload before matching payment.')
            due = date.fromisoformat(obligation.data['due_date'])
            paid_day = date.fromisoformat(entry.posting_date)
            cadence = obligation.data['cadence']
            if ((cadence == 'monthly' and (paid_day.year, paid_day.month) != (due.year, due.month)) or
                (cadence == 'annual' and paid_day.year != due.year) or
                (cadence == 'once' and abs((paid_day-due).days) > 31)):
                raise HTTPException(422, 'Payment is outside this confirmed bill occurrence.')
            if any(r.resource_id != identity and r.data['entry_id'] == entry.id and not r.data['reversed']
                   for r in current(db, owner, 'settlement')):
                raise HTTPException(409, 'A transaction can settle only one obligation.')
            paid = sum(-owned(db, LedgerEntry, owner, s.data['entry_id']).amount_paise
                       for s in current(db, owner, 'settlement') if s.resource_id != identity and
                       s.data['obligation_id'] == data['obligation_id'] and settlement_valid(db, owner, s))
            if paid-entry.amount_paise > obligation.data['amount_paise']:
                raise HTTPException(422, 'Payments exceed the confirmed bill amount; confirm any variable amount first.')
    elif kind == 'receivable':
        entry = owned(db, LedgerEntry, owner, data['purchase_entry_id'])
        if not entry.active or entry.amount_paise >= 0 or any(c['category'] not in {'purchase', 'fee', 'interest'} for c in entry.components):
            raise HTTPException(422, 'Receivable needs an active purchase.')
        if entry.revision != data['expected_entry_revision']:
            raise HTTPException(409, 'Purchase evidence changed.')
        if data['due_paise'] > -entry.amount_paise:
            raise HTTPException(422, 'Receivable exceeds purchase.')
        if any(r.resource_id != identity and r.data['purchase_entry_id'] == entry.id for r in active_rows(db, owner, kind)):
            raise HTTPException(409, 'Purchase already has a receivable.')
        received = sum(l.amount_paise for l in db.query(LedgerLink).filter_by(user_id=owner,
                       left_id=entry.id, active=True, kind='reimbursement'))
        if received > data['due_paise']:
            raise HTTPException(422, 'Due amount is below confirmed receipts.')
    elif kind == 'goal':
        owned(db, StatementAccount, owner, data['funding_account_id'])
        if data['allocated_paise'] > data['target_paise']:
            raise HTTPException(422, 'Allocated amount exceeds target.')
    elif kind == 'debt':
        obligation = get(db, owner, 'obligation', data['obligation_id'])
        if obligation.data['archived'] or obligation.data['paused']:
            raise HTTPException(422, 'Debt needs an active confirmed obligation.')
        if data['minimum_payment_paise'] != obligation.data['amount_paise']:
            raise HTTPException(422, 'Debt payment must equal the confirmed obligation amount.')
        if any(r.resource_id != identity and r.data['obligation_id'] == data['obligation_id'] for r in active_rows(db, owner, kind)):
            raise HTTPException(409, 'Obligation already belongs to a debt.')


def category_spending(entries, links, lookup):
    """Recognized ledger spending grouped by explicit user budget labels.

    Confirmed refunds use purchase category proportions with residual paise assigned
    in component order; reimbursements stay separate from recognized spending.
    """
    totals = defaultdict(int)
    for entry in entries:
        if not entry.active:
            continue
        if any(l.active and l.kind in {'transfer', 'card_settlement'} and entry.id in (l.left_id, l.right_id) for l in links):
            continue
        for component in entry.components:
            if component['category'] in {'purchase', 'fee', 'interest'}:
                totals[component.get('budget_category') or 'uncategorized'] -= component['amount_paise']
        for link in links:
            if not link.active or link.kind != 'refund' or link.right_id != entry.id:
                continue
            purchase = lookup(link.left_id)
            if purchase is None:
                continue
            components = purchase.components
            remaining = link.amount_paise
            for i, c in enumerate(components):
                amount = remaining if i == len(components)-1 else link.amount_paise * abs(c['amount_paise']) // abs(purchase.amount_paise)
                totals[c.get('budget_category') or 'uncategorized'] -= amount
                remaining -= amount
    return dict(totals)


def budget_snapshot(db, owner, month, categories):
    budgets = [r for r in active_rows(db, owner, 'budget') if r.data['month'] == month]
    if not budgets:
        return {'status': 'unavailable', 'actual_paise': categories, 'budget': None}
    row = budgets[0]
    return {'status': 'available', 'budget': describe(row), 'actual_paise': categories,
            'lines': {key: {'allocated_paise': amount, 'actual_paise': categories.get(key, 0),
                           'overspend_paise': max(0, categories.get(key, 0)-amount)}
                      for key, amount in row.data['lines'].items()}}


def receivables(db, owner):
    result = []
    for row in active_rows(db, owner, 'receivable'):
        entry = owned(db, LedgerEntry, owner, row.data['purchase_entry_id'])
        received = sum(l.amount_paise for l in db.query(LedgerLink).filter_by(user_id=owner,
                       left_id=entry.id, active=True, kind='reimbursement'))
        valid = entry.active and received <= row.data['due_paise'] and all(
            c['category'] in {'purchase', 'fee', 'interest'} for c in entry.components)
        result.append({**describe(row), 'status': 'confirmed' if valid else 'needs_review',
            'received_paise': received, 'remaining_paise': max(0, row.data['due_paise']-received) if valid else None,
            'own_share_paise': -entry.amount_paise-row.data['due_paise'] if valid else None})
    return result


def candidates(db, owner):
    """Conservative suggestions only, requiring >=3 distinct dates and stable cadence."""
    import re
    groups = defaultdict(list)
    for e in db.query(LedgerEntry).filter_by(user_id=owner, active=True).order_by(LedgerEntry.posting_date, LedgerEntry.id):
        if e.amount_paise < 0 and all(c['category'] in {'purchase', 'fee', 'interest', 'unsplit_debt', 'loan_principal'} for c in e.components):
            merchant = re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', ' ', e.description.lower())).strip()
            if merchant:
                groups[(e.account_id, merchant)].append(e)
    output = []
    for (account, merchant), rows in groups.items():
        days = [date.fromisoformat(e.posting_date) for e in rows]
        gaps = [(b-a).days for a, b in zip(days, days[1:])]
        if len(rows) < 3 or len(set(days)) != len(rows):
            continue
        cadence = 'monthly' if all(25 <= g <= 35 for g in gaps) else 'annual' if all(350 <= g <= 380 for g in gaps) else None
        amounts = [-e.amount_paise for e in rows]
        median = sorted(amounts)[len(amounts)//2]
        if cadence and max(amounts)-min(amounts) <= max(100, median//5):
            output.append({'merchant': merchant, 'account_id': account, 'cadence': cadence,
                'variable': len(set(amounts)) > 1, 'suggested_amount_paise': median,
                'entry_ids': [r.id for r in rows], 'status': 'candidate_requires_confirmation'})
    return output


def category_suggestions(db, owner):
    """Suggest only labels repeatedly confirmed by this owner; never writes splits."""
    import re
    def merchant(entry):
        return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', ' ', entry.description.lower())).strip()
    corrected = {r.target_id for r in db.query(LedgerCorrection)
                 .filter_by(user_id=owner) if r.payload.get('operation') == 'split'}
    entries = db.query(LedgerEntry).filter_by(user_id=owner, active=True).all()
    history = defaultdict(list)
    for e in entries:
        if e.id in corrected and len(e.components) == 1 and e.components[0].get('budget_category'):
            history[(e.account_id, merchant(e))].append(e)
    result = []
    for e in entries:
        prior = [r for r in history[(e.account_id, merchant(e))] if r.posting_date < e.posting_date]
        labels = {(r.components[0]['category'], r.components[0]['budget_category']) for r in prior}
        if len({r.posting_date for r in prior}) >= 3 and len(labels) == 1 and not any(c.get('budget_category') for c in e.components):
            category, budget_category = next(iter(labels))
            result.append({'entry_id': e.id, 'expected_revision': e.revision, 'category': category,
                'budget_category': budget_category, 'status': 'suggestion_requires_confirmation',
                'source_entry_ids': sorted(r.id for r in prior)})
    return result


def copy_budget(db, owner, identity, target_month, report_id=None):
    row = get(db, owner, 'budget', identity)
    data = {**row.data, 'month': target_month, 'archived': False}
    if data['rollover'] == 'positive':
        if not report_id:
            raise HTTPException(422, 'Positive rollover requires the source month report.')
        from backend.services.monthly_report_service import read
        report = read(db, owner, report_id)
        frozen = report['snapshot'].get('budget', {}).get('budget')
        if (report['stale'] or not report['snapshot']['selected_scope_complete'] or
            not report['snapshot']['metrics']['classification_complete'] or
            report['month'] != row.data['month'] or not frozen or
            (frozen['id'], frozen['revision']) != (row.resource_id, row.revision)):
            raise HTTPException(409, 'Rollover needs a current report for this budget revision.')
        actual = report['snapshot']['budget']['actual_paise']
        data['lines'] = {k: check_paise(v+max(0, v-actual.get(k, 0))) for k, v in row.data['lines'].items()}
    return {'source_id': identity, 'source_revision': row.revision, 'preview': data, 'persisted': False,
            'basis': 'selected_report_scope_only; budget_allocation_is_not_investment_capacity'}
