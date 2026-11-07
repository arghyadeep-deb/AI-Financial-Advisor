"""In-app first; event categories carry fixed safe copy, never balances or payloads.

Optional verified email uses the shared mail outbox; critical recovery is separate.
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


def delivery_state(pref, category):
    hour = (utcnow() + timedelta(hours=5, minutes=30)).hour
    start, end = pref.quiet_start, pref.quiet_end
    quiet = start is not None and (start <= hour < end if start < end else hour >= start or hour < end)
    return 'suppressed' if not pref.enabled or category not in pref.categories else 'deferred' if quiet else 'delivered'

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
    state = delivery_state(pref, category)
    if row is None:
        row = DeliveryAttempt(id=str(uuid4()), user_id=owner, event_key=event_key, category=category, state=state)
        db.add(row)
    else:
        row.state = state
    db.flush()
    # Channel verification is server-owned; public preferences cannot assert it.
    from backend.core.config import config
    from backend.models.models import NotificationPreference
    import hashlib
    channel = db.get(NotificationPreference, owner)
    if state == 'delivered' and config.NOTIFICATION_EMAIL_ENABLED and channel and channel.email_enabled and channel.verified_email_hash == hashlib.sha256(user.email.encode()).hexdigest():
        from backend.services import mail_service
        mail_service.enqueue(db, owner, row.id, category, {}, utcnow() + timedelta(days=7), event_key)
    return row


def event_deadline(db, owner, category, event_key, default_deadline):
    """Recheck the same current domain evidence before an external delivery."""
    if category != 'reminder' or ':' not in (event_key or ''):
        return default_deadline
    if event_key.startswith('p:'):
        # Household protection renewal reminder (lane J): recheck the current book and opt-in.
        from backend.services import household_service
        from backend.finance.ledger import lock_owner as _lock
        from backend.core.config import config
        from datetime import datetime as _dt, time as _t
        if not config.SYNTHETIC_HOUSEHOLDS_ENABLED or config.is_production_like:
            return None
        _lock(db, owner, bump=False)
        _, identity, ordinal = event_key.split(':')
        book = household_service.latest(db, owner, 'protection')
        if not book or book.id != identity:
            return None
        policy = book.data['policies'][int(ordinal)]
        if not policy['reminder_opt_in'] or policy['archived'] or policy['renewal_date'] is None:
            return None
        deadline = _dt.combine(_dt.fromisoformat(policy['renewal_date']).date(), _t(3, 30)) + timedelta(days=7)
        return deadline if utcnow() < deadline else None
    from backend.services import planning_service as planning
    from backend.finance.ledger import lock_owner
    from datetime import datetime, time
    lock_owner(db, owner, bump=False)
    identity, revision = event_key.rsplit(':', 1)
    kind = 'goal' if identity.startswith('goal:') else 'obligation'
    identity = identity.removeprefix('goal:') if kind == 'goal' else identity
    try:
        item = planning.get(db, owner, kind, identity)
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise
    data = item.data
    if str(item.revision) != revision or not data.get('reminder_opt_in', False) or data.get('paused', False) or data['archived']:
        return None
    if kind == 'goal' and data['allocated_paise'] >= data['target_paise']:
        return None
    paid = sum(-planning.owned(db, planning.LedgerEntry, owner, s.data['entry_id']).amount_paise
        for s in planning.current(db, owner, 'settlement') if kind == 'obligation' and
        s.data['obligation_id'] == identity and planning.settlement_valid(db, owner, s))
    if kind == 'obligation' and paid >= data['amount_paise']:
        return None
    due = datetime.combine(datetime.fromisoformat(data['target_date'] if kind == 'goal' else data['due_date']).date(), time(3, 30))
    deadline = due + timedelta(days=7)
    return deadline if utcnow() < deadline else None


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
        deadline = event_deadline(db, owner, category, event_key, row.created_at + timedelta(days=7))
        if deadline is None:
            return
        notice = deliver(db, owner, event_key, category)
        if notice.state == 'deferred':
            if utcnow() >= deadline:
                notice.state = 'suppressed'
                return
            # One finite retry per hour, bounded by current preferences at delivery.
            # The business queue remains the only scheduler.
            row.state = 'queued'
            row.available_at = utcnow() + timedelta(hours=1)
            row.attempts = 0
            row.lease_until = None
    complete(db, job_id, fence, publish)

