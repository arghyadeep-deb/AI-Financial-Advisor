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

RULE_VERSION = 'ledger.v1'


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
    sources = []
    for entry in entries:
        evidence = db.query(LedgerEvidence).filter_by(user_id=owner, entry_id=entry.id, active=True).all()
        sources.append({'entry_id': entry.id, 'account_id': entry.account_id, 'posting_date': entry.posting_date,
            'amount_paise': entry.amount_paise, 'description': entry.description, 'components': entry.components,
            'revision': entry.revision, 'evidence': [{'import_id': e.import_id, 'row_id': e.row_id} for e in evidence]})
    snapshot = {'metrics': facts, 'coverage': scopes, 'selected_scope_complete': all(c['complete'] for c in scopes.values()),
        'household_coverage': 'undeclared_inventory', 'account_ids': selected, 'sources': sources,
        'links': [{'id': l.id, 'left_id': l.left_id, 'right_id': l.right_id, 'kind': l.kind,
                   'amount_paise': l.amount_paise} for l in links if any(e.id in (l.left_id, l.right_id) for e in entries)],
        'narrative_status': 'deterministic', 'narrative': 'Observed account activity; affordability requires verified future commitments and liquidity.'}
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
    return {'id': report.id, 'month': report.month, 'rule_version': report.rule_version, 'vector': report.vector,
        'stale': report.rule_version != RULE_VERSION or report.vector != vector(db, owner), 'snapshot': report.snapshot, 'created_at': report.created_at}


def export_csv(db, owner, report_id):
    report = read(db, owner, report_id)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['report_id', 'rule_version', 'entry_id', 'posting_date', 'amount_paise', 'description'])
    for source in report['snapshot']['sources']:
        description = source['description']
        if description.lstrip().startswith(('=', '+', '-', '@')):
            description = "'" + description
        writer.writerow([report['id'], report['rule_version'], source['entry_id'], source['posting_date'], source['amount_paise'], description])
    return stream.getvalue()
