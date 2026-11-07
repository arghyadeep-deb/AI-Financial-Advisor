"""Safe support tools (T1304). Operators work through these functions (CLI/ops), never through a public data route.

* Request-ID lookup returns metadata only and is always audited.
* A raw source document can be read only through a grant the owner created for that one document, with an expiry;
  every attempt (allowed or refused) is audited and visible to the owner.
"""
from datetime import timedelta
from uuid import uuid4
from fastapi import HTTPException
from backend.models.models import StatementDocument, SupportAccessLog, SupportGrant, utcnow
from backend.observability import requests as request_log
from backend.services import statement_service

MAX_GRANT_HOURS = 72


def _audit(db, operator, action, target, reason, outcome, user_id=None):
    if not operator or not reason or len(reason) > 200 or len(operator) > 80:
        raise ValueError('operator and reason are required')
    db.add(SupportAccessLog(id=str(uuid4()), user_id=user_id, operator=operator, action=action,
                            target=str(target)[:80], reason=reason, outcome=outcome))
    db.commit()


def lookup_request(db, operator, request_id, reason):
    found = request_log.lookup(request_id)
    _audit(db, operator, 'request_lookup', request_id, reason, 'found' if found else 'not_found')
    return dict(found) if found else None


def create_grant(db, owner, document_id, hours):
    if not 1 <= hours <= MAX_GRANT_HOURS:
        raise HTTPException(422, 'Grant duration must be 1 to %d hours.' % MAX_GRANT_HOURS)
    statement_service.owned(db, StatementDocument, owner, document_id)      # 404 for someone else's document
    grant = SupportGrant(id=str(uuid4()), user_id=owner, document_id=document_id,
                         expires_at=utcnow() + timedelta(hours=hours))
    db.add(grant)
    db.commit()
    return grant


def revoke_grant(db, owner, grant_id):
    grant = db.query(SupportGrant).filter_by(user_id=owner, id=grant_id).first()
    if grant is None:
        raise HTTPException(404, 'Resource not found.')
    if grant.revoked_at is None:
        grant.revoked_at = utcnow()
        db.commit()
    return grant


def read_document(db, operator, grant_id, reason):
    grant = db.get(SupportGrant, grant_id)
    if grant is None:
        _audit(db, operator, 'document_read', grant_id, reason, 'refused_unknown_grant')
        raise PermissionError('No such grant.')
    if grant.revoked_at is not None or grant.expires_at <= utcnow():
        _audit(db, operator, 'document_read', grant.document_id, reason, 'refused_expired_or_revoked', grant.user_id)
        raise PermissionError('Grant is expired or revoked.')
    try:
        content = statement_service.read_document(db, grant.user_id, grant.document_id)
    except HTTPException:
        _audit(db, operator, 'document_read', grant.document_id, reason, 'refused_unavailable', grant.user_id)
        raise PermissionError('Document is unavailable.')
    grant.used_at = utcnow()
    _audit(db, operator, 'document_read', grant.document_id, reason, 'allowed', grant.user_id)
    return content


def access_log(db, owner):
    rows = db.query(SupportAccessLog).filter_by(user_id=owner).order_by(SupportAccessLog.created_at.desc()).limit(100)
    return [{'id': r.id, 'action': r.action, 'target': r.target, 'reason': r.reason, 'outcome': r.outcome,
             'at': r.created_at} for r in rows]
