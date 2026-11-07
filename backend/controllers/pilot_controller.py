"""Free-pilot endpoints: mapped CSV import, manual dated credit entry, billing entitlement flag."""
from datetime import date, datetime
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.finance.importers import mapped
from backend.integrations.credit_bureau import get_adapter
from backend.models.models import ManualCreditEntry, StatementAccount, User
from backend.services import statement_service as service

router = APIRouter(tags=['Free pilot'])
CREDIT_STALE_DAYS = 90


class MappedPreview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    csv_text: str = Field(min_length=1, max_length=10 * 1024 * 1024)
    mapping: mapped.Mapping


class MappedUpload(MappedPreview):
    confirm: Literal[True]                      # explicit confirmation of the previewed result
    expected_rows: StrictInt = Field(ge=1)      # must equal the previewed row count


def _preview(payload):
    try:
        return mapped.preview(payload.csv_text.encode('utf-8'), payload.mapping,
                              max_rows=config.STATEMENT_MAX_ROWS, max_bytes=config.STATEMENT_MAX_BYTES)
    except mapped.MappingError as exc:
        code = str(exc)
        message = ('Scanned documents and photos are not supported yet. Export a CSV from your bank instead.'
                   if code == 'unsupported_scanned_or_image' else 'The file could not be read: ' + code)
        raise HTTPException(422, {'code': code, 'message': message})


@router.post('/statement-accounts/{account_id}/mapped-preview')
def mapped_preview(account_id: str, payload: MappedPreview, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    service.enabled()
    service.owned(db, StatementAccount, user.id, account_id)
    result = _preview(payload)
    result.pop('all_rows')                      # bounded sample only; a preview stores nothing
    return result


@router.post('/statement-accounts/{account_id}/mapped-uploads', status_code=202)
def mapped_upload(account_id: str, payload: MappedUpload, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    service.enabled()
    account = service.owned(db, StatementAccount, user.id, account_id)
    result = _preview(payload)
    if not result['ok']:
        raise HTTPException(422, {'code': 'validation_failed', 'message': 'Fix the listed rows first.',
                                  'errors': result['errors'][:20]})
    if result['row_count'] != payload.expected_rows:
        raise HTTPException(409, 'The file no longer matches the preview you confirmed.')
    return service.describe(service.upload(db, user.id, account.id, mapped.to_canonical(account.token, result)))


class CreditEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    score: StrictInt | None = Field(default=None, ge=300, le=900)   # None = unknown, stays unknown
    bureau_label: str | None = Field(default=None, min_length=1, max_length=40)
    as_of: date


def _describe(entry):
    if entry is None:
        return {'status': 'unknown', 'score': None, 'as_of': None, 'source': None}
    age = (date.today() - entry.as_of.date()).days
    status = 'unknown' if entry.score is None else 'stale' if age > CREDIT_STALE_DAYS else 'current'
    note = 'User-reported and unverified.'
    if status == 'stale':
        note += ' Older than %d days; please update it.' % CREDIT_STALE_DAYS
    return {'id': entry.id, 'status': status, 'score': entry.score, 'bureau_label': entry.bureau_label,
            'as_of': entry.as_of.date().isoformat(), 'age_days': age, 'source': entry.source, 'note': note}


@router.post('/credit/manual', status_code=201)
def credit_add(payload: CreditEntry, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.as_of > date.today():
        raise HTTPException(422, 'The as-of date cannot be in the future.')
    row = ManualCreditEntry(id=str(uuid4()), user_id=user.id, score=payload.score, bureau_label=payload.bureau_label,
                            as_of=datetime.combine(payload.as_of, datetime.min.time()), source='user_reported')
    db.add(row)
    db.commit()
    return _describe(row)


@router.get('/credit/manual')
def credit_latest(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ManualCreditEntry).filter_by(user_id=user.id).order_by(
        ManualCreditEntry.as_of.desc(), ManualCreditEntry.created_at.desc()).limit(50).all()
    adapter = get_adapter()
    return {'latest': _describe(rows[0] if rows else None), 'history': [_describe(r) for r in rows],
            'provider': {'status': adapter.status, 'reason': adapter.reason}}


@router.get('/billing/entitlement')
def entitlement(user: User = Depends(get_current_user)):
    return {'plan': 'free_pilot', 'billing': 'disabled', 'paid_billing': 'deferred', 'features': 'all_pilot_features',
            'note': 'Free controlled pilot. No payment is requested or taken.'}
