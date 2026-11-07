"""In-app only; event categories carry fixed safe copy, never balances or payloads.

Critical security messages continue through the existing auth recovery contract.
Quiet hours use Asia/Kolkata. Deferred events require an explicit later delivery call.
"""
from datetime import timedelta
from fastapi import HTTPException
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


def schedule(db, owner, event_key, category, when):
    """Schedule safe metadata in the shared outbox; caller commits business event."""
    from backend.workers.queue import enqueue
    if category not in COPY or not 1 <= len(event_key) <= 50:
        raise ValueError("Unsupported notification")
    if when.tzinfo is not None:
        from datetime import timezone
        when = when.astimezone(timezone.utc).replace(tzinfo=None)
    row = enqueue(db, owner, 'notice:' + category + ':' + event_key, 'notification')
    if row.state == 'queued':
        row.available_at = when
    return row


def run_scheduled(db, job_id, fence):
    from backend.workers.queue import complete
    from backend.models.models import WorkItem
    row = db.get(WorkItem, job_id)
    if not row or row.kind != 'notification':
        raise ValueError('Unsupported work')
    _, category, event_key = row.event_key.split(':', 2)
    def publish(db, owner):
        if category == 'reminder' and ':' in event_key:
            from backend.services import planning_service
            from backend.finance.ledger import lock_owner
            lock_owner(db, owner, bump=False)
            identity, revision = event_key.rsplit(':', 1)
            try:
                obligation = planning_service.get(db, owner, 'obligation', identity)
            except HTTPException as exc:
                # A deleted resource never authorizes a reminder.
                if exc.status_code == 404:
                    return
                raise
            data = obligation.data
            if str(obligation.revision) != revision or not data['reminder_opt_in'] or data['paused'] or data['archived']:
                return
            paid = sum(-planning_service.owned(db, planning_service.LedgerEntry, owner, s.data['entry_id']).amount_paise
                       for s in planning_service.current(db, owner, 'settlement') if
                       s.data['obligation_id'] == identity and planning_service.settlement_valid(db, owner, s))
            if paid >= data['amount_paise']:
                return
        notice = deliver(db, owner, event_key, category)
        if notice.state == 'deferred':
            if utcnow() - row.created_at >= timedelta(days=7):
                notice.state = 'suppressed'
                return
            # One finite retry per hour, bounded by current preferences at delivery.
            # The business queue remains the only scheduler.
            row.state = 'queued'
            row.available_at = utcnow() + timedelta(hours=1)
            row.attempts = 0
            row.lease_until = None
    complete(db, job_id, fence, publish)

