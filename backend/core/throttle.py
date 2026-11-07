"""Database-backed login throttling (T108 / F001-FR09).

Counters are keyed by a SHA-256 digest of the normalised email so unknown
accounts are throttled exactly like known ones (no enumeration signal) and
no raw email is stored in this table.  Residual risk: an attacker can lock a
known victim email for ``LOGIN_LOCK_SECONDS`` (temporary denial of service);
the lock is short and a per-IP layer belongs to the 009 edge/WAF work.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.core.config import config
from backend.models.models import LoginThrottle


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def key_for(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def seconds_locked(db: Session, email: str, now: Optional[datetime] = None) -> int:
    now = now or _now()
    row = db.get(LoginThrottle, key_for(email))
    if row and row.locked_until and row.locked_until > now:
        return int((row.locked_until - now).total_seconds()) + 1
    return 0


def record_failure(db: Session, email: str, now: Optional[datetime] = None) -> None:
    now = now or _now()
    k = key_for(email)
    row = db.get(LoginThrottle, k)
    if row is None:
        row = LoginThrottle(key=k, failures=0, window_start=now)
        db.add(row)
    if now - row.window_start > timedelta(seconds=config.LOGIN_WINDOW_SECONDS):
        row.failures, row.window_start, row.locked_until = 0, now, None
    row.failures += 1
    if row.failures >= config.LOGIN_MAX_FAILURES:
        row.locked_until = now + timedelta(seconds=config.LOGIN_LOCK_SECONDS)
    db.commit()


def record_success(db: Session, email: str) -> None:
    row = db.get(LoginThrottle, key_for(email))
    if row:
        db.delete(row)
        db.commit()
