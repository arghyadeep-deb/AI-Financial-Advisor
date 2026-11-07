"""Atomic reservations; callers commit with business writes or roll back together.

Units: jobs/requests integers, storage bytes, model tokens. Paid model calls stay
disabled until D07; no monetary cap is invented here.
"""
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from backend.models.models import QuotaUsage, User, utcnow

RESOURCES = {'jobs', 'storage_bytes', 'model_tokens', 'model_cost_paise', 'uploads', 'analysis', 'chat', 'exports'}

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


def reserve_model_attempt(db, owner, maximum_tokens, maximum_cost_paise):
    """Reserve a conservative upper bound BEFORE EACH attempt, including failures.

    Caller commits admission before any provider call. No refunds: unknown usage
    must not reopen a budget. No provider is enabled by this helper. A future
    approved adapter must supply a verified price bound and enforce token limits.
    """
    from backend.core.config import config
    from backend.core.operations import reserve_global
    if type(maximum_tokens) is not int or type(maximum_cost_paise) is not int or min(maximum_tokens, maximum_cost_paise) <= 0:
        raise ValueError('Positive token and cost upper bounds required')
    # Savepoint ensures a refused global reservation cannot consume owner quota.
    with db.begin_nested():
        reserve_global(db, 'model_cost_paise', maximum_cost_paise, config.GLOBAL_MODEL_DAILY_COST_PAISE)
        reserve(db, owner, 'model_tokens', maximum_tokens, config.MODEL_DAILY_TOKEN_LIMIT)
        reserve(db, owner, 'model_cost_paise', maximum_cost_paise, config.MODEL_DAILY_COST_PAISE)
