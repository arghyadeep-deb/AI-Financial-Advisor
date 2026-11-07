"""Atomic reservations; callers commit with business writes or roll back together.

Units: jobs/requests integers, storage bytes, model tokens. Paid model calls stay
disabled until D07; no monetary cap is invented here.
"""
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from backend.models.models import QuotaUsage, User, utcnow

RESOURCES = {'jobs', 'storage_bytes', 'model_tokens', 'uploads'}

def reserve(db, owner, resource, units, limit):
    if resource not in RESOURCES or type(units) is not int or type(limit) is not int or not 0 < units <= 10**13 or not 0 <= limit <= 10**13:
        raise ValueError('Invalid quota reservation')
    user = db.get(User, owner)
    if not user or not user.is_active:
        raise ValueError('Owner unavailable')
    period = utcnow().date().isoformat()
    bucket = dict(user_id=owner, resource=resource, period=period)
    if db.query(QuotaUsage).filter_by(**bucket).first() is None:
        try:
            with db.begin_nested():
                db.add(QuotaUsage(**bucket, used=0))
                db.flush()
        except IntegrityError:
            pass  # concurrent bucket creation; conditional UPDATE arbitrates limit
    count = db.execute(update(QuotaUsage).where(QuotaUsage.user_id == owner,
        QuotaUsage.resource == resource, QuotaUsage.period == period,
        QuotaUsage.used <= limit - units).values(used=QuotaUsage.used + units)).rowcount
    if count != 1:
        raise HTTPException(429, 'Daily resource limit reached.', headers={'Retry-After': '86400'})
