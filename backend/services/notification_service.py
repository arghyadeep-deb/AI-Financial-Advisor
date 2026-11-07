"""In-app only; event categories carry fixed safe copy, never balances or payloads.

Critical security messages continue through the existing auth recovery contract.
Quiet hours use Asia/Kolkata. Deferred events require an explicit later delivery call.
"""
from datetime import timedelta
from uuid import uuid4
from backend.models.models import NotificationPreference, DeliveryAttempt, User, utcnow
from backend.schemas.platform import Preferences
from backend.core.owned_stores import register_database_store

COPY = {"report_ready": "Your report is ready.", "reminder": "You have a reminder to review."}

def preferences(db, owner):
    row = db.get(NotificationPreference, owner)
    return Preferences.model_validate({k: getattr(row, k) for k in Preferences.model_fields}) if row else Preferences()

def deliver(db, owner, event_key, category):
    if category not in COPY or not 1 <= len(event_key) <= 100:
        raise ValueError("Unsupported notification")
    user = db.get(User, owner)
    if not user or not user.is_active:
        raise ValueError("Owner unavailable")
    row = db.query(DeliveryAttempt).filter_by(user_id=owner, event_key=event_key).first()
    if row and row.category != category:
        raise ValueError("Idempotency conflict")
    if row and row.state in {"delivered", "suppressed"}:
        return row
    pref = preferences(db, owner)
    hour = (utcnow() + timedelta(hours=5, minutes=30)).hour
    start, end = pref.quiet_start, pref.quiet_end
    quiet = start is not None and (start <= hour < end if start < end else hour >= start or hour < end)
    state = "suppressed" if not pref.enabled or category not in pref.categories else "deferred" if quiet else "delivered"
    if row is None:
        row = DeliveryAttempt(id=str(uuid4()), user_id=owner, event_key=event_key, category=category, state=state)
        db.add(row)
    else:
        row.state = state
    db.flush()
    return row

