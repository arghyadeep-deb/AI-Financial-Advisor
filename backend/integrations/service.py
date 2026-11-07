"""Consent, replay-safe sync and unknown-outcome operations over a provider-neutral adapter.

Evidence enters the ledger only through the existing statement import path (canonical text -> sandboxed parser -> review),
so the 002 ledger contract is enforced there, not re-implemented here.
"""
import csv
import io
from datetime import date
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from backend.core.config import config
from backend.integrations.base import ProviderRejected, ProviderTimeout
from backend.models.models import (IntegrationConsent, IntegrationEvent, IntegrationOperation, StatementAccount, utcnow)
from backend.services import statement_service

SCOPES = frozenset({'transactions'})
KINDS = frozenset({'link_check', 'refresh_request'})
IDEMPOTENCY_OK = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-')


def _enabled():
    statement_service.enabled()           # same synthetic-only gate; nothing here runs against a real provider


def owned_consent(db, owner, consent_id):
    row = db.query(IntegrationConsent).filter_by(user_id=owner, id=consent_id).first()
    if row is None:
        raise HTTPException(404, 'Resource not found.')
    return row


def describe_consent(c):
    return {'id': c.id, 'provider': c.provider, 'account_id': c.account_id, 'scopes': c.scopes, 'state': c.state,
            'revision': c.revision}


def grant(db, owner, provider, account_id, scopes):
    _enabled()
    if not scopes or not set(scopes) <= SCOPES:
        raise HTTPException(422, 'Unsupported scope.')
    account = statement_service.owned(db, StatementAccount, owner, account_id)
    if account.account_type != 'synthetic_debit':
        raise HTTPException(422, 'Only debit accounts can receive provider data.')
    from backend.finance.ledger import lock_owner
    lock_owner(db, owner, bump=False)
    row = IntegrationConsent(id=str(uuid4()), user_id=owner, provider=provider, account_id=account.id,
                             scopes=sorted(set(scopes)))
    db.add(row)
    db.commit()
    return row


def revoke(db, owner, consent_id):
    from backend.finance.ledger import lock_owner
    lock_owner(db, owner, bump=False)
    row = owned_consent(db, owner, consent_id)
    db.refresh(row)
    if row.state == 'active':
        row.state, row.revoked_at, row.revision = 'revoked', utcnow(), row.revision + 1
    db.commit()
    return row


def _canonical(token, rows):
    ordered = sorted(rows, key=lambda r: (r['posting_date'], r['event_id']))     # arrival order never matters
    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['SYNTHETIC-INR-v1', token, ordered[0]['posting_date'], ordered[-1]['posting_date'], '', ''])
    writer.writerow(['date', 'description', 'reference', 'signed_rupees', 'category'])
    for r in ordered:
        sign = '-' if r['amount_paise'] < 0 else ''
        paise = abs(r['amount_paise'])
        writer.writerow([r['posting_date'], r['description'], r['event_id'], f'{sign}{paise // 100}.{paise % 100:02d}', 'unknown'])
    return out.getvalue().encode('utf-8')


def _clean(row):
    try:
        stamp = date.fromisoformat(row['posting_date'])
        amount = row['amount_paise']
        event_id, text = str(row['event_id']), str(row['description'])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(502, 'Provider returned an invalid record; nothing was committed.') from exc
    if (type(amount) is not int or amount == 0 or not 1 <= len(event_id) <= 80 or not 1 <= len(text) <= 200
            or stamp > date.today()):
        raise HTTPException(502, 'Provider returned an invalid record; nothing was committed.')
    from backend.finance.importers.mapped import safe_text
    return {'event_id': event_id, 'posting_date': stamp.isoformat(), 'description': safe_text(text), 'amount_paise': amount}


def sync(db, owner, consent_id, adapter, since=None):
    """Fetch outside the lock; commit only if consent is unchanged. Replays are dropped by provider event id."""
    _enabled()
    consent = owned_consent(db, owner, consent_id)
    if consent.state != 'active' or 'transactions' not in consent.scopes or consent.provider != adapter.name:
        raise HTTPException(409, 'Consent is not active for this provider.')
    seen_revision, account_id = consent.revision, consent.account_id
    db.rollback()                                    # no open read transaction across the provider call
    fetched = [_clean(r) for r in adapter.fetch(consent_id, since)]
    from backend.finance.ledger import lock_owner
    lock_owner(db, owner, bump=False)
    consent = owned_consent(db, owner, consent_id)
    db.refresh(consent)
    if consent.state != 'active' or consent.revision != seen_revision:
        db.rollback()
        raise HTTPException(409, 'Consent changed during the fetch; nothing was committed.')
    unique, batch = [], set()
    known = {e for (e,) in db.query(IntegrationEvent.event_id).filter_by(user_id=owner, provider=consent.provider)}
    for r in fetched:
        if r['event_id'] in known or r['event_id'] in batch:
            continue
        batch.add(r['event_id'])
        unique.append(r)
    duplicates = len(fetched) - len(unique)
    if not unique:
        db.rollback()
        return {'accepted': 0, 'duplicates': duplicates, 'import': None}
    account = statement_service.owned(db, StatementAccount, owner, account_id)
    for r in unique:
        db.add(IntegrationEvent(id=str(uuid4()), user_id=owner, provider=consent.provider, event_id=r['event_id'],
                                consent_id=consent.id))
    try:
        job = statement_service.upload(db, owner, account.id, _canonical(account.token, unique))
        db.commit()                                   # events and import are published together
    except IntegrityError as exc:                    # a concurrent sync won the race; nothing of ours is kept
        db.rollback()
        raise HTTPException(409, 'A concurrent sync already recorded these records.') from exc
    except Exception:
        db.rollback()
        raise
    return {'accepted': len(unique), 'duplicates': duplicates, 'import': statement_service.describe(job)}


def describe_operation(op):
    return {'id': op.id, 'kind': op.kind, 'state': op.state, 'attempts': op.attempts,
            'needs_reconciliation': op.state in {'unknown', 'submitting'}}


def submit(db, owner, consent_id, kind, key, adapter):
    """Idempotent by key. A repeat of an `unknown` operation reconciles; it never submits twice."""
    _enabled()
    if kind not in KINDS or not 8 <= len(key) <= 64 or not set(key) <= IDEMPOTENCY_OK:
        raise HTTPException(422, 'Invalid operation request.')
    consent = owned_consent(db, owner, consent_id)
    if consent.state != 'active':
        raise HTTPException(409, 'Consent is not active.')
    existing = db.query(IntegrationOperation).filter_by(user_id=owner, idempotency_key=key).first()
    if existing:
        if existing.consent_id != consent.id or existing.kind != kind:
            raise HTTPException(409, 'Idempotency key was used for a different request.')
        return reconcile(db, owner, existing.id, adapter) if existing.state in {'unknown', 'submitting'} else existing
    op = IntegrationOperation(id=str(uuid4()), user_id=owner, consent_id=consent.id, kind=kind, idempotency_key=key,
                              attempts=1)
    db.add(op)
    try:
        db.commit()                                   # the intent is durable before anything leaves the system
    except IntegrityError:
        db.rollback()
        return db.query(IntegrationOperation).filter_by(user_id=owner, idempotency_key=key).one()
    op_id = op.id
    try:
        adapter.submit(op_id, kind)
        state = 'submitted'
    except ProviderRejected:
        state = 'failed'
    except ProviderTimeout:
        state = 'unknown'
    row = db.query(IntegrationOperation).filter_by(id=op_id).one()
    row.state, row.updated_at = state, utcnow()
    db.commit()
    return row


def reconcile(db, owner, operation_id, adapter):
    """Ask the provider what happened; only a definite answer closes the operation."""
    row = db.query(IntegrationOperation).filter_by(user_id=owner, id=operation_id).first()
    if row is None:
        raise HTTPException(404, 'Resource not found.')
    if row.state in {'confirmed', 'failed'}:
        return row
    answer = adapter.status(row.id)
    if answer in {'confirmed', 'failed'}:
        row.state = answer
    elif row.state == 'submitting':
        row.state = 'unknown'
    row.updated_at = utcnow()
    db.commit()
    return row
