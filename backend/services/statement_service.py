"""Owned document/job transitions over the existing outbox. Synthetic-only gate."""
from datetime import timedelta
from hashlib import sha256
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from backend.core.config import config
from backend.core.limits import reserve
from backend.finance.storage import configured_storage
from backend.models.models import (StatementAccount, StatementDocument, StatementImport,
                                    StatementRow, WorkItem, utcnow)
from backend.workers import queue


def enabled():
    if not config.SYNTHETIC_STATEMENTS_ENABLED or config.is_production_like:
        raise HTTPException(503, 'Synthetic statement imports are disabled. Real bank data is unsupported.')


def owned(db, model, owner, identity):
    row = db.query(model).filter_by(user_id=owner, id=identity).first()
    if row is None:
        raise HTTPException(404, 'Resource not found.')
    return row


def create_account(db, owner, payload):
    enabled()
    from backend.finance.ledger import lock_owner
    lock_owner(db, owner, bump=False)
    row = StatementAccount(id=str(uuid4()), user_id=owner, **payload.model_dump())
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, 'Account token already exists.') from exc
    return row


def upload(db, owner, account_id, content):
    enabled()
    account = owned(db, StatementAccount, owner, account_id)
    if not content or len(content) > config.STATEMENT_MAX_BYTES:
        raise HTTPException(413, 'Empty or oversized statement.')
    digest = sha256(content).hexdigest()
    existing = db.query(StatementDocument).filter_by(user_id=owner, account_id=account.id, digest=digest).first()
    if existing:
        return db.query(StatementImport).filter_by(user_id=owner, document_id=existing.id).order_by(StatementImport.generation.desc()).first()
    storage = configured_storage()
    document_id = str(uuid4())
    reserve(db, owner, 'uploads', 1, config.UPLOAD_DAILY_LIMIT)
    reserve(db, owner, 'storage_bytes', len(content), config.STORAGE_DAILY_BYTES)
    reserve(db, owner, 'jobs', 1, config.UPLOAD_DAILY_LIMIT)
    document = StatementDocument(id=document_id, user_id=owner, account_id=account.id,
        digest=digest, storage_key=document_id, size=len(content),
        expires_at=utcnow() + timedelta(days=config.SOURCE_RETENTION_DAYS))
    try:
        storage.put(owner, document_id, content)
        db.add(document)
        db.flush()
        work = queue.enqueue(db, owner, 'statement:' + document_id + ':1', 'statement')
        row = StatementImport(id=str(uuid4()), user_id=owner, account_id=account.id, document_id=document_id, work_id=work.id)
        db.add(row)
        db.commit()
        return row
    except Exception as exc:
        db.rollback()
        storage.delete(owner, document_id)
        if isinstance(exc, IntegrityError):
            existing = db.query(StatementDocument).filter_by(user_id=owner, account_id=account.id, digest=digest).first()
            if existing:
                return db.query(StatementImport).filter_by(document_id=existing.id).order_by(StatementImport.generation.desc()).first()
        raise


def read_document(db, owner, document_id):
    row = owned(db, StatementDocument, owner, document_id)
    if row.expires_at <= utcnow():
        raise HTTPException(410, 'Source document expired.')
    return configured_storage().get(owner, row.storage_key)


def process_claimed(db, work_id, fence, *, scanner_available=True):
    """Parse outside DB transaction, then fenced atomic stage/checkpoint publication."""
    from backend.workers.parser_runtime import extract
    work = db.get(WorkItem, work_id)
    if not work or work.kind != 'statement':
        raise ValueError('Unsupported work')
    job = db.query(StatementImport).filter_by(work_id=work_id, user_id=work.user_id).one()
    job_id, owner = job.id, job.user_id
    if job.state != 'queued':
        queue.complete(db, work_id, fence, lambda *_: None)
        return
    try:
        content = read_document(db, owner, job.document_id)
        result = extract(content, scanner_available=scanner_available)
    except (HTTPException, ValueError, OSError):
        result = {'ok': False, 'error_code': 'source_unavailable'}
    db.rollback()  # no open read transaction across publication lock

    def stage(db, owner):
        from backend.finance.ledger import lock_owner
        lock_owner(db, owner, bump=False)
        current = owned(db, StatementImport, owner, job_id)
        db.refresh(current)
        if current.state != 'queued':
            return
        current.revision += 1
        current.checkpoint = 'reconciled' if result['ok'] else 'quarantined'
        if not result['ok']:
            current.state, current.error_code = 'quarantined', result['error_code']
            return
        data = result['parsed']
        account = owned(db, StatementAccount, owner, current.account_id)
        if data['account_token'] != account.token:
            current.state, current.error_code = 'needs_review', 'account_mismatch'
            return
        for field in ('start_date', 'end_date', 'opening_paise', 'closing_paise', 'difference_paise'):
            setattr(current, field, data[field])
        for fields in data['rows']:
            db.add(StatementRow(id=str(uuid4()), user_id=owner, import_id=current.id, **fields))
        current.state = 'needs_review'
        current.error_code = 'balance_mismatch' if data['difference_paise'] not in (None, 0) else 'unverified_balance' if data['difference_paise'] is None else None
    queue.complete(db, work_id, fence, stage)


def describe(job):
    return {key: getattr(job, key) for key in ('id', 'account_id', 'document_id', 'work_id', 'generation',
        'revision', 'state', 'checkpoint', 'parser_version', 'error_code', 'start_date', 'end_date',
        'opening_paise', 'closing_paise', 'difference_paise', 'business_commit_id')}
