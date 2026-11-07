from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_auth_context, AuthContext
from backend.schemas.platform import PasswordChange, ConsentChoice
from backend.services.auth_service import AuthService
from backend.models.models import ConsentRecord
from backend.schemas.platform import Reauthentication
from backend.services.privacy.lifecycle import export_owned, delete_owned, configured_journal
from backend.core.config import config

router = APIRouter(tags=["Account controls"])

@router.post('/privacy/exports', status_code=201)
def request_export(payload: Reauthentication, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    from backend.services.privacy import exports
    return exports.create(db, ctx.user, payload.password.get_secret_value())

@router.get('/privacy/requests/{request_id}')
def request_status(request_id: str, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    from backend.services.privacy import exports
    from backend.models.models import PrivacyRequest
    from backend.services.statement_service import owned
    return exports.describe(owned(db, PrivacyRequest, ctx.user.id, request_id))

@router.get('/privacy/exports/{request_id}/download')
def download_export(request_id: str, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    from backend.services.privacy import exports
    return Response(exports.download(db, ctx.user.id, request_id), media_type='application/json',
        headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename="account-export.json"',
                 'X-Content-Type-Options': 'nosniff'})

@router.get("/privacy/consents")
def consent_status(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    from backend.services.consent_service import allowed
    return {purpose: allowed(db, ctx.user.id, purpose) for purpose in ("model_inference", "tracing")}

@router.post("/privacy/export")
def export(payload: Reauthentication, response: Response, ctx: AuthContext = Depends(get_auth_context),
           db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = 'attachment; filename="account-export.json"'
    return export_owned(db, ctx.user, payload.password.get_secret_value())

@router.post("/privacy/deletion", status_code=202)
def deletion(payload: Reauthentication, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return delete_owned(db, ctx.user, payload.password.get_secret_value(), configured_journal())

@router.get("/sessions")
def sessions(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return [{"id": s.id, "created_at": s.created_at, "expires_at": s.expires_at,
             "revoked_at": s.revoked_at, "current": s.id == ctx.session_id}
            for s in AuthService(db).list_sessions(ctx.user.id)]

@router.delete("/sessions/{session_id}", status_code=204)
def revoke(session_id: str, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    AuthService(db).revoke_session(ctx.user.id, session_id)
    return Response(status_code=204)

@router.post("/auth/password-change", status_code=204)
def change(payload: PasswordChange, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    AuthService(db).change_password(ctx.user, payload.password.get_secret_value(), payload.new_password.get_secret_value())
    return Response(status_code=204)

@router.post("/privacy/consents", status_code=201)
def consent(payload: ConsentChoice, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    row = ConsentRecord(user_id=ctx.user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    return {"id": row.id, **payload.model_dump()}

from backend.schemas.platform import Preferences
from backend.services import notification_service as notices
from backend.models.models import NotificationPreference, DeliveryAttempt

@router.get("/preferences", response_model=Preferences)
def preferences(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    return notices.preferences(db, ctx.user.id)

@router.put("/preferences", response_model=Preferences)
def put_preferences(payload: Preferences, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    row = db.get(NotificationPreference, ctx.user.id)
    if row is None:
        row = NotificationPreference(user_id=ctx.user.id)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return payload

@router.get("/notifications")
def notifications(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    rows = db.query(DeliveryAttempt).filter_by(user_id=ctx.user.id, state="delivered").order_by(DeliveryAttempt.created_at.desc()).limit(100).all()
    return [{"id": r.id, "category": r.category, "message": notices.COPY[r.category], "created_at": r.created_at} for r in rows]
