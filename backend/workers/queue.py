"""Single queue contract. Call enqueue inside the business transaction, then commit.

Consumers execute only deterministic DB writes inside complete's transaction;
external side effects require a separately approved idempotent adapter.
"""
from datetime import timedelta
from uuid import uuid4
from sqlalchemy import or_, update
from backend.models.models import WorkItem, User, utcnow
from backend.services.consent_service import allowed
from backend.core.owned_stores import register_database_store

MAX_ATTEMPTS = 3

def enqueue(db, owner, event_key, kind, consent_purpose=None):
    user = db.get(User, owner)
    if not user or not user.is_active:
        raise ValueError("Owner unavailable")
    existing = db.query(WorkItem).filter_by(user_id=owner, event_key=event_key).first()
    if existing:
        if (existing.kind, existing.consent_purpose) != (kind, consent_purpose):
            raise ValueError("Idempotency conflict")
        return existing
    row = WorkItem(id=str(uuid4()), user_id=owner, event_key=event_key, kind=kind,
                   consent_purpose=consent_purpose)
    db.add(row)
    db.flush()  # unique constraint also arbitrates concurrent enqueue; caller retries transaction
    return row

def claim(db, seconds=30):
    if not 1 <= seconds <= 300:
        raise ValueError("Invalid lease")
    now = utcnow()
    eligible = or_(WorkItem.state == "queued", (WorkItem.state == "running") & (WorkItem.lease_until <= now))
    row = db.query(WorkItem).filter(eligible, WorkItem.available_at <= now,
            WorkItem.attempts < MAX_ATTEMPTS).order_by(WorkItem.created_at).first()
    if row is None:
        return None
    fence = row.fence
    count = db.execute(update(WorkItem).where(WorkItem.id == row.id, WorkItem.fence == fence,
        eligible).values(state="running", fence=fence + 1, attempts=WorkItem.attempts + 1,
                         lease_until=now + timedelta(seconds=seconds))).rowcount
    db.commit()
    if count != 1:
        return None
    db.refresh(row)
    return row.id, row.fence

def complete(db, job_id, fence, publish):
    now = utcnow()
    # UPDATE obtains a write lock through publication commit; stale workers cannot publish.
    count = db.execute(update(WorkItem).where(WorkItem.id == job_id, WorkItem.fence == fence,
        WorkItem.state == "running", WorkItem.lease_until > now).values(state="complete")).rowcount
    if count != 1:
        db.rollback()
        raise ValueError("Stale lease")
    row = db.get(WorkItem, job_id)
    user = db.query(User).filter_by(id=row.user_id).with_for_update().first()
    if not user or not user.is_active or (row.consent_purpose and not allowed(db, row.user_id, row.consent_purpose)):
        row.state = "cancelled"
    else:
        try:
            publish(db, row.user_id)
        except Exception:
            db.rollback()
            raise
    db.commit()


def heartbeat(db, job_id, fence, seconds=30):
    if not 1 <= seconds <= 300:
        raise ValueError("Invalid lease")
    now = utcnow()
    count = db.execute(update(WorkItem).where(WorkItem.id == job_id, WorkItem.fence == fence,
        WorkItem.state == "running", WorkItem.lease_until > now).values(
        lease_until=now + timedelta(seconds=seconds))).rowcount
    db.commit()
    return count == 1

def sweep_exhausted(db):
    now = utcnow()
    count = db.execute(update(WorkItem).where(WorkItem.state == "running",
        WorkItem.lease_until <= now, WorkItem.attempts >= MAX_ATTEMPTS).values(state="dead_letter")).rowcount
    db.commit()
    return count

def metrics(db):
    from sqlalchemy import func
    # Aggregate metadata only. No owner, event key, payload or secret labels.
    return dict(db.query(WorkItem.state, func.count()).group_by(WorkItem.state).all())
