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
from sqlalchemy import update, case
from sqlalchemy.exc import IntegrityError

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


def _record_attempt(db: Session, email: str, now=None, *, bounded=False,
                    max_attempts=None, window_seconds=None, lock_seconds=None) -> bool:
    now = now or _now()
    maximum = config.LOGIN_MAX_FAILURES if max_attempts is None else max_attempts
    window = config.LOGIN_WINDOW_SECONDS if window_seconds is None else window_seconds
    lock = config.LOGIN_LOCK_SECONDS if lock_seconds is None else lock_seconds
    if type(maximum) is not int or not 1 <= maximum <= 10**6 or any(type(v) is not int or not 1 <= v <= 86400 for v in (window, lock)):
        raise ValueError('Invalid throttle bounds')
    k = key_for(email)
    if db.get(LoginThrottle, k) is None:
        try:
            with db.begin_nested():
                db.add(LoginThrottle(key=k, failures=0, window_start=now))
                db.flush()
        except IntegrityError:
            pass
    expired = LoginThrottle.window_start < now - timedelta(seconds=window)
    failures = case((expired, 1), else_=LoginThrottle.failures + 1)
    statement = update(LoginThrottle).where(LoginThrottle.key == k)
    if bounded:
        statement = statement.where(
            (LoginThrottle.locked_until.is_(None)) | (LoginThrottle.locked_until <= now),
            expired | (LoginThrottle.failures < maximum))
    count = db.execute(statement.values(
        failures=failures, window_start=case((expired, now), else_=LoginThrottle.window_start),
        locked_until=case((failures >= maximum, now + timedelta(seconds=lock)),
                          (expired, None), else_=LoginThrottle.locked_until))).rowcount
    db.commit()
    return count == 1


def record_failure(db: Session, email: str, now: Optional[datetime] = None) -> None:
    _record_attempt(db, email, now)


def consume_attempt(db: Session, key: str, now: Optional[datetime] = None, *,
                    max_attempts=None, window_seconds=None, lock_seconds=None) -> bool:
    """Atomic bounded admission for generic recovery responses, known or unknown."""
    return _record_attempt(db, key, now, bounded=True, max_attempts=max_attempts,
                           window_seconds=window_seconds, lock_seconds=lock_seconds)


def record_success(db: Session, email: str) -> None:
    row = db.get(LoginThrottle, key_for(email))
    if row:
        db.delete(row)
        db.commit()
