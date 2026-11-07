"""Immutable owned synthetic tax lifecycle using shared transactions/privacy."""
from uuid import uuid4
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from backend.core.config import config
from backend.core.telemetry import traceable
from backend.finance.ledger import atomic, lock_owner
from backend.finance.tax import reconcile
from backend.models.models import TaxRevision
from backend.schemas.tax import TaxInputs
from backend.core.limits import reserve
from engines.tax import comparison


def today():
    return datetime.now(ZoneInfo('Asia/Kolkata')).date()


def gate():
    if not config.TAX_SANDBOX_ENABLED or config.APP_ENV not in {'test', 'development'}:
        raise HTTPException(404, 'Tax sandbox unavailable.')


def query(db, owner, case_id, kind):
    return db.query(TaxRevision).filter_by(user_id=owner, case_id=case_id, kind=kind)


def latest(db, owner, case_id, kind, required=True):
    row = query(db, owner, case_id, kind).order_by(TaxRevision.revision.desc()).first()
    if row is None and required:
        raise HTTPException(404, 'Tax resource not found.')
    return row


def case_at(db, owner, case_id, revision=None):
    q = query(db, owner, case_id, 'case')
    if revision is not None:
        q = q.filter_by(revision=revision)
    row = q.order_by(TaxRevision.revision.desc()).first()
    if row is None:
        raise HTTPException(404, 'Tax resource not found.')
    return describe(row)


def owned(db, owner, identity, kind):
    row = db.query(TaxRevision).filter_by(user_id=owner, id=identity, kind=kind).first()
    if row is None:
        raise HTTPException(404, 'Tax resource not found.')
    return row


def describe(row):
    return {'id': row.id, 'case_id': row.case_id, 'kind': row.kind, 'revision': row.revision,
            'data': row.data, 'created_at': row.created_at.isoformat()}


def replay(db, owner, request):
    row = db.query(TaxRevision).filter_by(user_id=owner, operation_key=request['idempotency_key']).first()
    if row and row.request != request:
        raise HTTPException(409, 'Idempotency key reused with different input.')
    return row


def expect(row, revision):
    if (row.revision if row else 0) != revision:
        raise HTTPException(409, 'Revision changed; reload before retrying.')


def store(db, owner, case_id, kind, revision, request, data):
    reserve(db, owner, 'analysis', 1, config.ANALYSIS_DAILY_LIMIT)
    row = TaxRevision(id=str(uuid4()), user_id=owner, case_id=case_id, kind=kind,
        revision=revision, operation_key=request['idempotency_key'], request=request, data=data)
    db.add(row)
    db.commit()
    return describe(row)


@atomic
@traceable(name='tax_case_revision')
def write_case(db, owner, payload, case_id=None):
    gate()
    lock_owner(db, owner, bump=False)
    request = {'kind': 'case', 'case_id': case_id, **payload.model_dump(mode='json')}
    if case_id:
        latest(db, owner, case_id, 'case')
    prior = replay(db, owner, request)
    if prior:
        return describe(prior)
    before = latest(db, owner, case_id, 'case', False) if case_id else None
    expect(before, payload.expected_revision)
    try:
        preview = reconcile(payload.data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return store(db, owner, case_id or str(uuid4()), 'case', payload.expected_revision + 1,
        request, {'inputs': payload.data.model_dump(mode='json'), 'preview': preview})


@atomic
@traceable(name='tax_field_review')
def review(db, owner, case_id, payload):
    gate()
    lock_owner(db, owner, bump=False)
    case = latest(db, owner, case_id, 'case')
    request = {'kind': 'review', 'case_id': case_id, **payload.model_dump(mode='json')}
    prior = replay(db, owner, request)
    if prior:
        return describe(prior)
    expect(case, payload.expected_revision)
    try:
        fields = reconcile(TaxInputs.model_validate(case.data['inputs']), payload.resolutions)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    before = latest(db, owner, case_id, 'review', False)
    return store(db, owner, case_id, 'review', before.revision + 1 if before else 1, request,
        {**fields, 'case_revision': case.revision, 'confirmed': payload.confirmed,
         'status': fields['status'] if payload.confirmed else 'needs_review'})


@atomic
@traceable(name='tax_sample_draft')
def draft(db, owner, case_id, payload):
    gate()
    lock_owner(db, owner, bump=False)
    case = latest(db, owner, case_id, 'case')
    request = {'kind': 'draft', 'case_id': case_id, **payload.model_dump(mode='json')}
    prior = replay(db, owner, request)
    if prior:
        return read_draft(db, owner, prior.id)
    expect(case, payload.expected_revision)
    reviewed = latest(db, owner, case_id, 'review', False)
    try:
        result = comparison.compare(TaxInputs.model_validate(case.data['inputs']),
            reviewed.data if reviewed else None, revision=case.revision, as_of=today())
    except (ValueError, OSError):
        return {'status': 'needs_review', 'reasons': ['sample_pack_unavailable'], 'persisted': False}
    if result['status'] != 'sample_draft':
        return {**result, 'persisted': False}
    before = latest(db, owner, case_id, 'draft', False)
    saved = store(db, owner, case_id, 'draft', before.revision + 1 if before else 1, request,
        {**result, 'case_snapshot': case.data, 'review_id': reviewed.id,
         'review_revision': reviewed.revision, 'review_snapshot': reviewed.data})
    return read_draft(db, owner, saved['id'])


@traceable(name='tax_draft_read')
def read_draft(db, owner, identity):
    row = owned(db, owner, identity, 'draft')
    case = latest(db, owner, row.case_id, 'case')
    reviewed = latest(db, owner, row.case_id, 'review', False)
    reasons = []
    if case.revision != row.data['case_revision']:
        reasons.append('case_revision_changed')
    if not reviewed or reviewed.id != row.data['review_id']:
        reasons.append('review_revision_changed')
    try:
        pair = comparison.packs()
        from engines.tax.sample_packs import pack_digest
        if {k: pack_digest(p) for k, p in pair.items()} != row.data['pack_vector']:
            reasons.append('rule_pack_changed')
        if any(not p.effective <= today() < p.expires for p in pair.values()):
            reasons.append('rule_pack_not_current')
    except (ValueError, OSError):
        reasons.append('rule_pack_unavailable')
    return {**describe(row), 'stale': bool(reasons), 'stale_reasons': reasons}


@atomic
@traceable(name='tax_draft_export')
def export(db, owner, identity):
    import json
    from hashlib import sha256
    draft = read_draft(db, owner, identity)
    reserve(db, owner, 'exports', 1, config.EXPORT_DAILY_LIMIT)
    snapshot = json.dumps(draft['data'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    result = {'format': 'synthetic-tax-review-pack-v1', 'label': comparison.LABEL,
        'official_acknowledgment': False, **draft,
        'snapshot_sha256': sha256(snapshot.encode('utf-8')).hexdigest()}
    db.commit()
    return json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2)
