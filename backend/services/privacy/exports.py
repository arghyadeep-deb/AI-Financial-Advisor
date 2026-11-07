"""Reauthenticated creation; owner-authenticated short-lived encrypted delivery."""
from datetime import timedelta
import json
from uuid import uuid4
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from backend.core.config import config
from backend.core.limits import reserve
from backend.finance.storage import configured_storage
from backend.models.models import PrivacyRequest, utcnow
from backend.services.privacy.lifecycle import export_owned
from backend.services.statement_service import owned


def describe(row):
    return {'id': row.id, 'kind': row.kind, 'state': 'expired' if row.expires_at <= utcnow() else row.state,
            'created_at': row.created_at, 'expires_at': row.expires_at}


def create(db, user, password):
    content = json.dumps(jsonable_encoder(export_owned(db, user, password)), ensure_ascii=True).encode()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, 'Export exceeds the offline delivery limit; operator assistance required.')
    storage = configured_storage()
    identity = str(uuid4())
    try:
        reserve(db, user.id, 'exports', 1, config.EXPORT_DAILY_LIMIT)
        storage.put(user.id, identity, content)
        row = PrivacyRequest(id=identity, user_id=user.id, kind='export', state='ready', storage_key=identity,
            expires_at=utcnow() + timedelta(seconds=config.EXPORT_TTL_SECONDS))
        db.add(row)
        db.commit()
        return describe(row)
    except Exception:
        db.rollback()
        storage.delete(user.id, identity)
        raise


def download(db, owner, identity):
    row = owned(db, PrivacyRequest, owner, identity)
    if row.expires_at <= utcnow():
        raise HTTPException(410, 'Export expired. Reauthenticate to request another.')
    try:
        return configured_storage().get(owner, row.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(410, 'Export is no longer available.') from exc


def expire(db):
    storage = configured_storage()
    count = 0
    for row in db.query(PrivacyRequest).filter(PrivacyRequest.expires_at <= utcnow()):
        storage.delete(row.user_id, row.storage_key)
        count += 1
    return count
