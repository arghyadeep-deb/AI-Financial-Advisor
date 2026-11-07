from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import AuthContext, get_auth_context
from backend.schemas.schemas import (
    AuthResponse, LoginRequest, MessageOnly, PasswordResetConfirm,
    PasswordResetRequest, SignupRequest,
)
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user. Returns a short-lived access token."""
    return AuthService(db).signup(payload.email, payload.full_name, payload.password)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password. Failures are generic and rate limited."""
    return AuthService(db).login(payload.email, payload.password)


@router.post("/logout", status_code=204)
def logout(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """Revoke the current session; the token stops working immediately."""
    AuthService(db).logout(ctx.session_id, ctx.user.id)
    return Response(status_code=204)


@router.post("/password-reset/request", response_model=MessageOnly, status_code=202)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Always answers identically, whether or not the account exists."""
    AuthService(db).request_reset(payload.email)
    return MessageOnly(message="If an account exists for that address, recovery instructions have been issued.")


@router.post("/password-reset/confirm", response_model=MessageOnly)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Single-use token; revokes every existing session for the account."""
    AuthService(db).confirm_reset(payload.token, payload.new_password)
    return MessageOnly(message="Password updated. Please sign in again.")
