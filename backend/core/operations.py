"""Fixed-key aggregate operations metadata; all writes join caller transactions."""
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from backend.models.models import OperationalCounter, utcnow

WORKERS = {'notifications', 'statements', 'retention'}


def _row(db, key, period):
    row = db.get(OperationalCounter, (key, period))
    if row is None:
        try:
            with db.begin_nested():
                db.add(OperationalCounter(key=key, period=period, used=0))
                db.flush()
        except IntegrityError:
            pass
    return db.get(OperationalCounter, (key, period))


def heartbeat(db, worker):
    if worker not in WORKERS:
        raise ValueError('Unsupported worker')
    row = _row(db, 'worker:' + worker, 'current')
    row.updated_at = utcnow()
    db.flush()


def reserve_global(db, resource, units, limit):
    if resource not in {'model_cost_paise', 'mail'} or type(units) is not int or type(limit) is not int or not 0 < units <= 10**13 or not 0 <= limit <= 10**13:
        raise ValueError('Invalid global reservation')
    period = utcnow().date().isoformat()
    _row(db, resource, period)
    count = db.execute(update(OperationalCounter).where(OperationalCounter.key == resource,
        OperationalCounter.period == period, OperationalCounter.used <= limit - units).values(
        used=OperationalCounter.used + units, updated_at=utcnow())).rowcount
    if count != 1:
        raise HTTPException(429, 'Global resource budget exhausted.', headers={'Retry-After': '86400'})
