from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.auth import decode_token
from backend.core.database import get_db
from backend.models.models import AuthSession, FinancialProfile, User

# auto_error=False so a missing header is a uniform 401 (not FastAPI's 403).
bearer = HTTPBearer(auto_error=False)

_UNAUTH = "Invalid or expired credentials. Please sign in again."


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, _UNAUTH, headers={"WWW-Authenticate": "Bearer"})


class AuthContext:
    """The authenticated user plus the session that authenticated the call."""
    def __init__(self, user: User, session_id: str):
        self.user = user
        self.session_id = session_id


def get_auth_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise _unauthorized()
    claims = decode_token(credentials.credentials)
    if not claims:
        raise _unauthorized()

    session = db.get(AuthSession, claims["sid"])
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if (session is None or session.revoked_at is not None or session.expires_at <= now
            or str(session.user_id) != claims["sub"]):
        raise _unauthorized()

    user = db.get(User, int(claims["sub"]))
    if not user or not user.is_active:
        raise _unauthorized()
    from backend.core.config import config
    from backend.models.models import MfaCredential
    credential = db.get(MfaCredential, user.id)
    enrolled = bool(credential and credential.enabled)
    if (config.MFA_REQUIRED or enrolled) and not session.mfa_verified:
        # A policy-mandated unenrolled user has only an enrollment session.
        # Enrolled users must complete the public single-use challenge instead.
        setup_routes = {'/auth/mfa/status', '/auth/mfa/enroll/start', '/auth/mfa/enroll/confirm', '/auth/logout'}
        if enrolled or request.url.path not in setup_routes:
            raise _unauthorized()
    if config.SUPPRESSION_JOURNAL:
        from backend.services.privacy.lifecycle import configured_journal
        if configured_journal().contains(user.id):
            raise _unauthorized()
    return AuthContext(user, session.id)


def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    return ctx.user


def get_current_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FinancialProfile:
    profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not found. Please complete your profile first.",
        )
    return profile
