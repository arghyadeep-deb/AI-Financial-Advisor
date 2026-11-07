"""Fixed plain-text templates, encrypted payloads and the shared leased outbox.

No address, token, provider body or exception text may enter logs. The fake is
the default and is process-local synthetic test evidence, never a live channel.
"""
from collections import OrderedDict
from datetime import timedelta
import hashlib
import logging
import re
from typing import Protocol

import httpx
from fastapi import HTTPException
from backend.core.config import config
from backend.core.operations import reserve_global
from backend.finance.storage import configured_storage
from backend.models.models import MailMessage, PasswordResetToken, User, WorkItem, utcnow
from backend.workers import queue

log = logging.getLogger('advisor.mail')
TEMPLATES = {
    'password_reset': ('Reset your password', 'Use this single-use recovery code in the password recovery form: {token}'),
    'report_ready': ('Report ready', 'Your report is ready. Open the app to review it.'),
    'reminder': ('Reminder', 'You have a reminder to review. Open the app for details.'),
}


def address(value):
    # Exactly one mailbox, no display names, headers, controls or address lists.
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise ValueError('Invalid mail address')
    return value


def render(to, template_id, variables):
    address(to)
    if template_id not in TEMPLATES or not isinstance(variables, dict):
        raise ValueError('Unsupported template')
    expected = {'token'} if template_id == 'password_reset' else set()
    if set(variables) != expected or (expected and (not isinstance(variables['token'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', variables['token']))):
        raise ValueError('Invalid template variables')
    subject, text = TEMPLATES[template_id]
    return subject, text.format(**variables)


class MailAdapter(Protocol):
    def send(self, to: str, template_id: str, variables: dict) -> None: ...


class FakeMail:
    def __init__(self, message_id):
        self.message_id = message_id

    def send(self, to, template_id, variables):
        render(to, template_id, variables)
        fake_messages.setdefault(self.message_id, (to, template_id, dict(variables)))
        while len(fake_messages) > 1000:
            fake_messages.popitem(last=False)


fake_messages = OrderedDict()


class ResendMail:
    def __init__(self, message_id):
        if not config.MAIL_LIVE_ENABLED or not config.RESEND_API_KEY:
            raise ValueError('Live mail disabled or credentials unavailable')
        address(config.MAIL_FROM)
        if any(ord(c) < 33 or ord(c) > 126 for c in config.RESEND_API_KEY):
            raise ValueError('Invalid mail credentials')
        self.message_id = message_id

    def send(self, to, template_id, variables):
        subject, body = render(to, template_id, variables)
        # No redirects: credentials/payload cannot be forwarded to another host.
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.post('https://api.resend.com/emails',
                headers={'Authorization': 'Bearer ' + config.RESEND_API_KEY, 'Idempotency-Key': self.message_id},
                json={'from': config.MAIL_FROM, 'to': [to], 'subject': subject, 'text': body})
        if response.status_code not in {200, 201, 202}:
            raise ValueError('Mail provider refused delivery')


def enqueue(db, owner, event_key, template_id, variables, expires_at, source_event=None):
    user = db.get(User, owner)
    if not user or not user.is_active or not 1 <= len(event_key) <= 95:
        raise ValueError('Invalid mail event or owner')
    render(user.email, template_id, variables)
    work = queue.enqueue(db, owner, 'mail:' + event_key, 'mail')
    message = db.get(MailMessage, work.id)
    if message:
        if message.template_id != template_id:
            raise ValueError('Mail idempotency conflict')
        return message
    payload = configured_storage().seal(owner, 'mail:' + work.id, {'to': user.email, 'variables': variables})
    message = MailMessage(id=work.id, user_id=owner, template_id=template_id, payload=payload,
        expires_at=expires_at, source_event=source_event)
    db.add(message)
    db.flush()
    return message


def _eligible(db, message, data):
    if message.template_id == 'password_reset':
        digest = hashlib.sha256(data['variables']['token'].encode()).hexdigest()
        return db.query(PasswordResetToken).filter_by(user_id=message.user_id, token_hash=digest,
            used_at=None).filter(PasswordResetToken.expires_at > utcnow()).first() is not None
    from backend.services import notification_service as notices
    from backend.models.models import NotificationPreference
    pref = db.get(NotificationPreference, message.user_id)
    if not config.NOTIFICATION_EMAIL_ENABLED or not pref or not pref.email_enabled or pref.verified_email_hash != hashlib.sha256(data['to'].encode()).hexdigest():
        return False
    return notices.event_deadline(db, message.user_id, message.template_id, message.source_event, message.expires_at) is not None


def run_once(db):
    claimed = queue.claim(db, kind='mail')
    if claimed is None:
        return False
    job_id, fence = claimed
    work = db.get(WorkItem, job_id)
    message = db.get(MailMessage, job_id)
    now = utcnow()
    admission = None
    data = None
    adapter = None
    if message and message.expires_at > now:
        try:
            data = configured_storage().unseal(message.user_id, 'mail:' + job_id, message.payload)
            if not _eligible(db, message, data):
                admission = 'suppressed'
            elif message.template_id != 'password_reset':
                from backend.services.notification_service import delivery_state, preferences
                state = delivery_state(preferences(db, message.user_id), message.template_id)
                if state != 'delivered':
                    admission = 'quiet' if state == 'deferred' else 'suppressed'
            if not admission and message.first_attempt_at and now - message.first_attempt_at >= timedelta(hours=23):
                admission = 'review_required'
            if not admission:
                adapter = FakeMail(job_id) if config.MAIL_PROVIDER == 'fake' else ResendMail(job_id)
                reserve_global(db, 'mail', 1, min(100, config.MAIL_DAILY_LIMIT))
                message.first_attempt_at = message.first_attempt_at or now
                # Durable admission BEFORE external side effects. A crash cannot
                # reset the daily budget or the provider idempotency deadline.
                db.commit()
        except HTTPException as exc:
            db.rollback()
            admission = 'deferred' if exc.status_code == 429 else 'configuration_error'
        except (ValueError, KeyError, TypeError):
            db.rollback()
            admission = 'configuration_error'

    def publish(db, owner):
        # This transaction fences deletion/cancellation and serializes delivery.
        if not message or message.expires_at <= now:
            if message:
                message.state, message.payload = 'expired', None
            return
        if admission == 'deferred':
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=1, microsecond=0)
            _defer(work, message, tomorrow)
            return
        if admission == 'quiet':
            _defer(work, message, now + timedelta(hours=1))
            return
        if admission == 'suppressed':
            message.state, message.payload = 'suppressed', None
            return
        if admission:
            message.state, work.state = admission, 'dead_letter'
            log.warning('mail delivery requires operator review')
            return
        try:
            if data['to'] != db.get(User, owner).email or not _eligible(db, message, data):
                message.state, message.payload = 'suppressed', None
                return
            if message.template_id != 'password_reset':
                from backend.services.notification_service import delivery_state, preferences
                current_state = delivery_state(preferences(db, owner), message.template_id)
                if current_state != 'delivered':
                    if current_state == 'deferred':
                        _defer(work, message, now + timedelta(hours=1))
                    else:
                        message.state, message.payload = 'suppressed', None
                    return
        except (ValueError, KeyError, TypeError):
            message.state, work.state = 'configuration_error', 'dead_letter'
            log.warning('mail delivery configuration unavailable')
            return
        # Hold the publication fence/owner lock during the bounded HTTPS call.
        try:
            adapter.send(data['to'], message.template_id, data['variables'])
        except Exception:
            message.state = 'retryable' if work.attempts < queue.MAX_ATTEMPTS else 'review_required'
            work.state = 'queued' if work.attempts < queue.MAX_ATTEMPTS else 'dead_letter'
            work.available_at = now + timedelta(minutes=5 * work.attempts)
            log.warning('mail delivery attempt failed')
            return
        message.state, message.payload = 'sent', None
        log.info('mail delivery accepted')
    queue.complete(db, job_id, fence, publish)
    return True


def _defer(work, message, when):
    work.state, work.available_at, work.attempts, work.lease_until = 'queued', when, 0, None
    message.state = 'deferred'
