"""Immutable monthly observed facts, evidence and full account revision vectors."""
import calendar
import csv
from datetime import date, timedelta
import io
from uuid import uuid4
from fastapi import HTTPException
from backend.models.models import (StatementAccount, StatementImport, LedgerEntry, LedgerLink,
    LedgerEvidence, MonthlyReport)
from backend.finance.ledger import atomic, lock_owner, metrics
from backend.services.statement_service import owned

RULE_VERSION = 'ledger.v2'


def vector(db, owner):
    return {a.id: [a.revision, a.link_revision] for a in db.query(StatementAccount).filter_by(user_id=owner).order_by(StatementAccount.id)}


def coverage(db, owner, account, start, end):
    intervals = db.query(StatementImport).filter_by(user_id=owner, account_id=account, state='completed').all()
    verified, unverified = set(), set()
    for job in intervals:
        if not job.start_date or not job.end_date:
            continue
        day = max(start, date.fromisoformat(job.start_date))
        last = min(end, date.fromisoformat(job.end_date))
        while day <= last:
            (verified if job.difference_paise == 0 else unverified).add(day.isoformat())
            day += timedelta(days=1)
    expected = (end-start).days + 1
    gaps = []
    day = start
    while day <= end:
        if day.isoformat() not in verified:
            gaps.append(day.isoformat())
        day += timedelta(days=1)
    return {'verified_days': len(verified), 'unverified_days': len(unverified - verified),
        'required_days': expected, 'complete': len(verified) == expected, 'missing_verified_dates': gaps}


@atomic
def create(db, owner, payload):
    selected = sorted(set(payload.account_ids))
    if len(selected) != len(payload.account_ids):
        raise HTTPException(422, 'Repeated account in scope.')
    for identity in selected:
        owned(db, StatementAccount, owner, identity)
    lock_owner(db, owner, bump=False)
    current = vector(db, owner)
    if current != payload.expected_vector:
        raise HTTPException(409, 'Account or link revisions changed; reload scope vector.')
    year, month = map(int, payload.month.split('-'))
    try:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
    except ValueError as exc:
        raise HTTPException(422, 'Invalid calendar month.') from exc
    entries = db.query(LedgerEntry).filter(LedgerEntry.user_id == owner, LedgerEntry.account_id.in_(selected),
        LedgerEntry.active.is_(True), LedgerEntry.posting_date >= start.isoformat(), LedgerEntry.posting_date <= end.isoformat()).order_by(LedgerEntry.id).all()
    links = db.query(LedgerLink).filter_by(user_id=owner, active=True).all()
    scopes = {identity: coverage(db, owner, identity, start, end) for identity in selected}
    facts = metrics(entries, links)
    from backend.services import planning_service as planning
    categories = planning.category_spending(entries, links,
        lambda identity: db.query(LedgerEntry).filter_by(user_id=owner, id=identity).first())
    restatement = None
    if payload.restatement_refund_ids and not payload.restates_report_id:
        raise HTTPException(422, 'Refund restatement requires the original report identity.')
    if payload.restates_report_id:
        if not payload.restatement_reason:
            raise HTTPException(422, 'An explicit restatement reason is required.')
        original = read(db, owner, payload.restates_report_id)
        if original['month'] != payload.month or original['snapshot']['account_ids'] != selected:
            raise HTTPException(422, 'Restatement must retain the original month and account scope.')
        if len(set(payload.restatement_refund_ids)) != len(payload.restatement_refund_ids):
            raise HTTPException(422, 'Repeated refund in restatement.')
        adjustments = []
        for identity in payload.restatement_refund_ids:
            link = owned(db, LedgerLink, owner, identity)
            left = owned(db, LedgerEntry, owner, link.left_id)
            right = owned(db, LedgerEntry, owner, link.right_id)
            if not link.active or link.kind != 'refund' or left.id not in {e.id for e in entries} or right.posting_date <= end.isoformat():
                raise HTTPException(422, 'Restatement needs a confirmed later refund of a scoped purchase.')
            facts['spending_paise'] -= link.amount_paise
            adjustment_categories = planning.category_spending([right], [link], lambda _: left)
            for category, value in adjustment_categories.items():
                categories[category] = categories.get(category, 0)+value
            adjustments.append({'link_id': link.id, 'amount_paise': link.amount_paise,
                                'purchase_entry_id': left.id, 'credit_entry_id': right.id,
                                'credit_source': {'entry_id': right.id, 'posting_date': right.posting_date,
                                    'amount_paise': right.amount_paise, 'revision': right.revision,
                                    'evidence': [{'import_id': e.import_id, 'row_id': e.row_id} for e in
                                        db.query(LedgerEvidence).filter_by(user_id=owner, entry_id=right.id, active=True)]}})
        facts['recognized_surplus_paise'] = facts['income_paise']-facts['spending_paise']
        facts['shortfall_paise'] = max(0, -facts['recognized_surplus_paise'])
        facts['eligible_contribution_paise'] = 0 if facts['shortfall_paise'] else None
        facts['affordability_status'] = 'deficit' if facts['shortfall_paise'] else 'unavailable'
        restatement = {'original_report_id': original['id'], 'adjustments': adjustments,
                       'reason': payload.restatement_reason, 'actor_id': owner,
                       'basis': 'explicit_later_refunds; original_cash_movement_unchanged'}
    sources = []
    for entry in entries:
        evidence = db.query(LedgerEvidence).filter_by(user_id=owner, entry_id=entry.id, active=True).all()
        sources.append({'entry_id': entry.id, 'account_id': entry.account_id, 'posting_date': entry.posting_date,
            'amount_paise': entry.amount_paise, 'description': entry.description, 'components': entry.components,
            'origin': entry.origin,
            'revision': entry.revision, 'evidence': [{'import_id': e.import_id, 'row_id': e.row_id} for e in evidence]})
    snapshot = {'metrics': facts, 'coverage': scopes, 'selected_scope_complete': all(c['complete'] for c in scopes.values()),
        'household_coverage': 'undeclared_inventory', 'account_ids': selected, 'sources': sources,
        'links': [{'id': l.id, 'left_id': l.left_id, 'right_id': l.right_id, 'kind': l.kind,
                   'amount_paise': l.amount_paise} for l in links if any(e.id in (l.left_id, l.right_id) for e in entries)],
        'narrative_status': 'deterministic', 'narrative': 'Observed account activity; affordability requires verified future commitments and liquidity.'}
    snapshot['planning_vector'] = planning.vector(db, owner)
    snapshot['budget'] = planning.budget_snapshot(db, owner, payload.month, categories)
    snapshot['confirmed_obligations'] = [planning.describe(r) for r in planning.active_rows(db, owner, 'obligation')]
    snapshot['receivables'] = planning.receivables(db, owner)
    snapshot['restatement'] = restatement
    snapshot['card_support'] = 'canonical_ledger_only; no_card_statement_adapter'
    # The ledger cannot establish owned holdings, cost basis or complete debt
    # balances; never add observed transfers or future projections to net worth.
    snapshot['net_worth'] = {'status': 'unavailable', 'value_paise': None,
        'reason': 'owned_dated_holdings_debt_balances_and_complete_inventory_required'}
    previous_month = (start-timedelta(days=1)).strftime('%Y-%m')
    previous = db.query(MonthlyReport).filter_by(user_id=owner, month=previous_month).order_by(
        MonthlyReport.created_at.desc(), MonthlyReport.id.desc()).all()
    previous = next((r for r in previous if r.snapshot['account_ids'] == selected), None)
    comparable = bool(previous and not read(db, owner, previous.id)['stale'] and
                      previous.snapshot['selected_scope_complete'] and snapshot['selected_scope_complete'] and
                      previous.snapshot['metrics']['classification_complete'] and facts['classification_complete'])
    snapshot['comparison'] = {'status': 'available' if comparable else 'unavailable',
        'previous_report_id': previous.id if previous else None,
        'reason': None if comparable else 'current_verified_reports_for_both_months_required',
        'changes_paise': {key: facts[key]-previous.snapshot['metrics'][key]
            for key in ('income_paise', 'spending_paise', 'recognized_surplus_paise')} if comparable else {}}
    included_ids = {e.id for e in entries}
    snapshot['out_of_scope_link_ids'] = [l.id for l in links if (l.left_id in included_ids) != (l.right_id in included_ids)]
    # Recheck entire vector before insertion. Locking serializes concurrent account writes.
    if current != vector(db, owner):
        raise HTTPException(409, 'Sources changed during report calculation.')
    report = MonthlyReport(id=str(uuid4()), user_id=owner, month=payload.month, rule_version=RULE_VERSION,
        vector=current, snapshot=snapshot)
    db.add(report)
    from backend.services.notification_service import schedule
    from backend.models.models import utcnow
    schedule(db, owner, report.id, 'report_ready', utcnow())
    db.commit()
    return read(db, owner, report.id)


def read(db, owner, report_id):
    report = owned(db, MonthlyReport, owner, report_id)
    from backend.services import planning_service as planning
    return {'id': report.id, 'month': report.month, 'rule_version': report.rule_version, 'vector': report.vector,
        'stale': report.rule_version != RULE_VERSION or report.vector != vector(db, owner) or
                 report.snapshot.get('planning_vector', {}) != planning.vector(db, owner),
        'snapshot': report.snapshot, 'created_at': report.created_at}


def export_csv(db, owner, report_id):
    report = read(db, owner, report_id)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    extended = report['rule_version'] != 'ledger.v1'
    header = ['report_id', 'rule_version', 'entry_id', 'posting_date', 'amount_paise', 'description']
    writer.writerow(header + (['row_type', 'spending_adjustment_paise'] if extended else []))
    for source in report['snapshot']['sources']:
        description = source['description']
        if description.lstrip().startswith(('=', '+', '-', '@')):
            description = "'" + description
        row = [report['id'], report['rule_version'], source['entry_id'], source['posting_date'], source['amount_paise'], description]
        writer.writerow(row + (['source', ''] if extended else []))
    for adjustment in (report['snapshot'].get('restatement') or {}).get('adjustments', []):
        writer.writerow([report['id'], report['rule_version'], adjustment['credit_entry_id'],
                         adjustment.get('credit_source', {}).get('posting_date', ''), '',
                         'Confirmed later refund: '+adjustment['link_id'], 'restatement', -adjustment['amount_paise']])
    return stream.getvalue()
