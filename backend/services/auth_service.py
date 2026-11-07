"""Authentication lifecycle (T108 / T113, F001-FR06, FR09).

Single auth service: signup, login (with legacy-hash migration), logout,
password recovery.  Responses to login/recovery failures are generic and do
not reveal whether an account exists.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core import auth as authlib
from backend.core import throttle
from backend.core.config import config
from backend.models.models import AuthSession, PasswordResetToken, User

log = logging.getLogger("advisor.auth")

GENERIC_LOGIN_ERROR = "Incorrect email or password."
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "1234567890", "12345678910", "qwertyuiop",
    "iloveyou12", "admin12345", "letmein123", "welcome123", "changeme123",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def validate_new_password(password: str, email: str = "") -> None:
    if not isinstance(password, str) or len(password) < config.MIN_PASSWORD_LENGTH:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.")
    if len(password) > 128:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Password must be at most 128 characters.")
    low = password.lower()
    if low in _COMMON_PASSWORDS or (email and low == email.lower()):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a less common password.")


# Delivery hook for recovery tokens.  No mail provider is approved yet
# (release-gates D06/D09), so in production-like environments the default
# delivers nowhere and the token is never exposed.
def _default_delivery(email: str, token: str) -> None:
    if not config.is_production_like:
        log.info("password-reset token issued (dev/test only) for a registered account")


recovery_delivery: Callable[[str, str], None] = _default_delivery


class AuthService:

    def __init__(self, db: Session):
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────────
    def _issue(self, user: User) -> dict:
        now = _now()
        sid = authlib.new_session_id()
        self.db.add(AuthSession(
            id=sid, user_id=user.id, created_at=now,
            expires_at=now + timedelta(minutes=config.ACCESS_TOKEN_MINUTES),
        ))
        self.db.commit()
        return {
            "access_token": authlib.create_access_token(user.id, sid),
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "expires_in": config.ACCESS_TOKEN_MINUTES * 60,
        }

    def revoke_user_sessions(self, user_id: int, reason: str) -> int:
        res = self.db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason=reason)
        )
        return res.rowcount or 0

    # ── signup ────────────────────────────────────────────────────────────
    def signup(self, email: str, full_name: str, password: str) -> dict:
        email = email.strip().lower()
        validate_new_password(password, email)
        existing = self.db.query(User).filter(func.lower(User.email) == email).first()
        if existing:
            # Known limitation: signup cannot be enumeration-proof without
            # e-mail verification (feature 008/013).  Recorded in the handoff.
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered. Please login instead.")
        user = User(email=email, full_name=full_name.strip(),
                    hashed_password=authlib.hash_password(password),
                    password_scheme=authlib.SCHEME_ARGON2, password_changed_at=_now())
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered. Please login instead.")
        self.db.refresh(user)
        log.info("user created id=%s", user.id)
        return self._issue(user)

    # ── login ─────────────────────────────────────────────────────────────
    def login(self, email: str, password: str) -> dict:
        email = email.strip().lower()
        locked = throttle.seconds_locked(self.db, email)
        if locked:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many failed sign-in attempts. Try again later.",
                headers={"Retry-After": str(locked)},
            )

        user = self.db.query(User).filter(func.lower(User.email) == email).first()
        ok = False
        if user is None:
            authlib.burn_password_check(password)
        elif user.password_scheme == authlib.SCHEME_LEGACY:
            ok = authlib.verify_legacy(password, user.hashed_password)
            if not ok:
                authlib.burn_password_check(password)
        else:
            ok = authlib.verify_argon2(password, user.hashed_password)

        # Inactive accounts fail identically to wrong credentials.
        if not ok or not user.is_active:
            throttle.record_failure(self.db, email)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, GENERIC_LOGIN_ERROR)

        throttle.record_success(self.db, email)
        if user.password_scheme == authlib.SCHEME_LEGACY or authlib.needs_rehash(user.hashed_password):
            user.hashed_password = authlib.hash_password(password)
            user.password_scheme = authlib.SCHEME_ARGON2
            user.password_changed_at = _now()
            self.db.commit()
            log.info("password rehashed to argon2id for user id=%s", user.id)
        return self._issue(user)

    # ── logout ────────────────────────────────────────────────────────────
    def logout(self, session_id: str, user_id: int) -> None:
        self.db.execute(
            update(AuthSession)
            .where(AuthSession.id == session_id, AuthSession.user_id == user_id,
                   AuthSession.revoked_at.is_(None))
            .values(revoked_at=_now(), revoked_reason="logout")
        )
        self.db.commit()

    # ── recovery ──────────────────────────────────────────────────────────
    def request_reset(self, email: str) -> None:
        """Always returns without revealing whether the account exists."""
        email = email.strip().lower()
        user = self.db.query(User).filter(func.lower(User.email) == email).first()
        if not user or not user.is_active:
            return
        token = authlib.new_recovery_token()
        now = _now()
        self.db.add(PasswordResetToken(
            user_id=user.id, token_hash=authlib.digest_token(token), created_at=now,
            expires_at=now + timedelta(minutes=config.PASSWORD_RESET_MINUTES)))
        self.db.commit()
        try:
            recovery_delivery(user.email, token)
        except Exception:      # delivery failure must not change the response
            log.exception("recovery delivery failed")

    def confirm_reset(self, token: str, new_password: str) -> None:
        digest = authlib.digest_token(token or "")
        row = self.db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == digest).first()
        now = _now()
        invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired recovery token.")
        if not row or row.used_at is not None or row.expires_at <= now:
            raise invalid
        user = self.db.get(User, row.user_id)
        if not user or not user.is_active:
            raise invalid
        validate_new_password(new_password, user.email)
        # Atomic single-use claim: only one concurrent request can flip used_at.
        claimed = self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == row.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        ).rowcount
        if claimed != 1:
            self.db.rollback()
            raise invalid
        user.hashed_password = authlib.hash_password(new_password)
        user.password_scheme = authlib.SCHEME_ARGON2
        user.password_changed_at = now
        self.db.execute(   # invalidate any other outstanding recovery tokens
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now))
        self.revoke_user_sessions(user.id, "password_reset")
        throttle.record_success(self.db, user.email)
        self.db.commit()

    def list_sessions(self, user_id: int) -> list[AuthSession]:
        return self.db.query(AuthSession).filter(AuthSession.user_id == user_id).order_by(AuthSession.created_at.desc()).all()

    def revoke_session(self, user_id: int, session_id: str) -> None:
        row = self.db.query(AuthSession).filter_by(id=session_id, user_id=user_id).first()
        if row is None:
            raise HTTPException(404, "Session not found.")
        if row.revoked_at is None:
            row.revoked_at, row.revoked_reason = _now(), "user_revoked"
        self.db.commit()

    def reauthenticate(self, user: User, password: str) -> None:
        key = "reauth:" + str(user.id)
        locked = throttle.seconds_locked(self.db, key)
        if locked:
            raise HTTPException(429, "Try again later.", headers={"Retry-After": str(locked)})
        verify = authlib.verify_legacy if user.password_scheme == authlib.SCHEME_LEGACY else authlib.verify_argon2
        if not verify(password, user.hashed_password):
            throttle.record_failure(self.db, key)
            raise HTTPException(401, GENERIC_LOGIN_ERROR)
        throttle.record_success(self.db, key)

    def change_password(self, user: User, password: str, new_password: str) -> None:
        self.reauthenticate(user, password)
        validate_new_password(new_password, user.email)
        user.hashed_password = authlib.hash_password(new_password)
        user.password_scheme = authlib.SCHEME_ARGON2
        user.password_changed_at = _now()
        self.db.execute(update(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)).values(used_at=_now()))
        self.revoke_user_sessions(user.id, "password_change")
        self.db.commit()
