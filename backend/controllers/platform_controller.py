from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_auth_context, AuthContext
from backend.schemas.platform import PasswordChange, ConsentChoice
from backend.services.auth_service import AuthService
from backend.models.models import ConsentRecord

router = APIRouter(tags=["Account controls"])

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
