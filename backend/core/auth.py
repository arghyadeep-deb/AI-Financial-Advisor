"""Password hashing and access-token primitives (T108 / F001-FR06, FR09, FR12).

* Passwords: Argon2id with a per-password random salt.  The token signing key
  is never involved.  The historical unsalted ``HMAC-SHA256(SECRET_KEY, pw)``
  scheme is *verify-only* and exists solely to migrate legacy accounts: a
  successful legacy login is rehashed immediately.
* Tokens: short-lived HS256 JWTs with required claims
  ``sub, sid, jti, iat, nbf, exp, iss, aud, typ``.  ``sid`` binds the token
  to a server-side ``auth_sessions`` row so logout / password reset revoke it.
* Key rotation: new tokens are signed with ``SECRET_KEY``; tokens signed with
  a key listed in ``SECRET_KEY_PREVIOUS`` still verify until that key is
  removed from the list (which revokes them).
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.core.config import config

SCHEME_ARGON2 = "argon2id"
SCHEME_LEGACY = "legacy_hmac_sha256"

REQUIRED_CLAIMS = ["sub", "sid", "jti", "iat", "nbf", "exp", "iss", "aud", "typ"]

_hasher = PasswordHasher()   # argon2-cffi defaults: Argon2id, random 16-byte salt

# Pre-computed hash used to equalise work when the account does not exist.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


# ── Passwords ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_argon2(password: str, stored: str) -> bool:
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    try:
        return _hasher.check_needs_rehash(stored)
    except InvalidHashError:
        return True


def verify_legacy(password: str, stored: str) -> bool:
    """Verify the historical unsalted HMAC scheme (migration only)."""
    secret = config.LEGACY_PASSWORD_SECRET
    if not secret:
        return False
    digest = hmac.new(secret.encode(), password.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, stored or "")


def burn_password_check(password: str) -> None:
    """Spend comparable time when no account matches (enumeration resistance)."""
    verify_argon2(password, _DUMMY_HASH)


# ── Tokens ─────────────────────────────────────────────────────────────────

def new_session_id() -> str:
    return str(uuid.uuid4())


def create_access_token(user_id: int, session_id: str,
                        now: Optional[datetime] = None, minutes: Optional[int] = None) -> str:
    now = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": session_id,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=minutes if minutes is not None else config.ACCESS_TOKEN_MINUTES),
        "iss": config.TOKEN_ISSUER,
        "aud": config.TOKEN_AUDIENCE,
        "typ": "access",
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Return validated claims, or None for any problem (never raises)."""
    if not token or not isinstance(token, str):
        return None
    keys = [config.SECRET_KEY, *config.SECRET_KEY_PREVIOUS]
    for key in keys:
        try:
            claims = jwt.decode(
                token, key, algorithms=[config.ALGORITHM],
                audience=config.TOKEN_AUDIENCE, issuer=config.TOKEN_ISSUER,
                leeway=5, options={"require": REQUIRED_CLAIMS},
            )
        except jwt.InvalidSignatureError:
            continue            # try the next (previous) key
        except jwt.PyJWTError:
            return None
        if claims.get("typ") != "access":
            return None
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.isdigit():
            return None
        if not isinstance(claims.get("sid"), str) or not claims["sid"]:
            return None
        return claims
    return None


# ── Recovery tokens ────────────────────────────────────────────────────────

def new_recovery_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
