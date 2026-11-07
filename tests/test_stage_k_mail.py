"""Synthetic only: real migrated SQLite, mocked HTTP, no live key/network."""
from datetime import timedelta
import hashlib
import json

from cryptography.fernet import Fernet
import httpx
import pytest
from sqlalchemy.orm import Session

from backend.core.config import config
from backend.models.models import MailMessage, NotificationPreference, OperationalCounter, User, WorkItem, utcnow
from backend.services import mail_service as mail, notification_service as notices


@pytest.fixture(autouse=True)
def mail_config(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'MAIL_PROVIDER', 'fake')
    monkeypatch.setattr(config, 'MAIL_LIVE_ENABLED', False)
    monkeypatch.setattr(config, 'RESEND_API_KEY', '')
    monkeypatch.setattr(config, 'MAIL_FROM', 'advisor@example.com')
    monkeypatch.setattr(config, 'MAIL_DAILY_LIMIT', 100)
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', False)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'test': Fernet.generate_key().decode()}))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'test')
    mail.fake_messages.clear()
    yield
    mail.fake_messages.clear()


def owner(db):
    user = User(email='fictional@example.com', full_name='Fictional', hashed_password='!')
    db.add(user)
    db.commit()
    return user


def notice(db, user, key='event'):
    db.add(NotificationPreference(user_id=user.id, email_enabled=True,
        verified_email_hash=hashlib.sha256(user.email.encode()).hexdigest()))
    db.flush()
    return notices.deliver(db, user.id, key, 'report_ready')


@pytest.mark.parametrize('recipient', ['a@example.com\r\nBcc: b@example.com', 'a@example.com,b@example.com', 'Name <a@example.com>', 'a@example.com\x00'])
def test_header_injection(recipient):
    with pytest.raises(ValueError):
        mail.FakeMail('test').send(recipient, 'reminder', {})


@pytest.mark.parametrize('template,variables', [('html', {}), ('reminder', {'html': '<b>x</b>'}), ('password_reset', {'token': 'x\r\nHeader: x'})])
def test_fixed_templates(template, variables):
    with pytest.raises(ValueError):
        mail.FakeMail('test').send('a@example.com', template, variables)


def test_recovery_queued_encrypted_and_delivered_once(client, caplog):
    from backend.models.models import PasswordResetToken
    client.post('/auth/signup', json={'email': 'reset@example.com', 'full_name': 'Test', 'password': 'Fictional-pass-987'})
    assert client.post('/auth/password-reset/request', json={'email': 'reset@example.com'}).status_code == 202
    with client.session_factory() as db:
        msg = db.query(MailMessage).one()
        assert 'reset@example.com' not in msg.payload and 'token' not in msg.payload
        assert db.query(PasswordResetToken).count() == 1
        assert mail.run_once(db)
        assert not mail.run_once(db)
        assert msg.state == 'sent' and msg.payload is None
    sent = list(mail.fake_messages.values())
    assert len(sent) == 1 and sent[0][:2] == ('reset@example.com', 'password_reset')
    assert sent[0][2]['token'] not in caplog.text and 'reset@example.com' not in caplog.text
    assert client.post('/auth/password-reset/confirm', json={'token': sent[0][2]['token'], 'new_password': 'Changed-fictional-987'}).status_code == 200


def test_notification_gates_and_delivery_preference_recheck(db_engine, monkeypatch):
    with Session(db_engine) as db:
        user = owner(db)
        row = notice(db, user)
        db.commit()
        assert db.query(MailMessage).count() == 0  # live channel switch defaults off
        monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
        notices.deliver(db, user.id, 'new', 'report_ready')
        db.commit()
        assert db.query(MailMessage).count() == 1
        db.get(NotificationPreference, user.id).enabled = False
        db.commit()
        mail.run_once(db)
        assert db.query(MailMessage).one().state == 'suppressed'
        assert not mail.fake_messages


def test_fake_duplicate_and_global_cap_defer(db_engine, monkeypatch):
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    monkeypatch.setattr(config, 'MAIL_DAILY_LIMIT', 1)
    with Session(db_engine) as db:
        user = owner(db)
        row = notice(db, user)
        notices.deliver(db, user.id, 'second', 'report_ready')
        db.commit()
        assert mail.run_once(db)
        assert mail.run_once(db)
        assert sorted(m.state for m in db.query(MailMessage)) == ['deferred', 'sent']
        deferred = db.query(MailMessage).filter_by(state='deferred').one()
        job = db.get(WorkItem, deferred.id)
        assert job.state == 'queued' and job.attempts == 0 and job.available_at.date() > utcnow().date()
        assert db.get(OperationalCounter, ('mail', utcnow().date().isoformat())).used == 1
        assert len(mail.fake_messages) == 1
        assert notices.deliver(db, user.id, 'event', 'report_ready').id == row.id
        assert db.query(MailMessage).count() == 2


def test_resend_missing_key_never_calls_http(monkeypatch):
    monkeypatch.setattr(httpx.Client, 'post', lambda *a, **k: pytest.fail('network forbidden'))
    with pytest.raises(ValueError):
        mail.ResendMail('test')


def test_resend_mocked_http_retry_idempotency_and_redaction(db_engine, monkeypatch, caplog):
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    monkeypatch.setattr(config, 'MAIL_PROVIDER', 'resend')
    monkeypatch.setattr(config, 'MAIL_LIVE_ENABLED', True)
    monkeypatch.setattr(config, 'RESEND_API_KEY', 'synthetic-not-a-real-key')
    calls = []
    def post(self, url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 1:
            raise httpx.ReadTimeout('SENSITIVE provider exception fictional@example.com')
        return httpx.Response(200, json={'id': 'synthetic'})
    monkeypatch.setattr(httpx.Client, 'post', post)
    with Session(db_engine) as db:
        user = owner(db)
        notice(db, user)
        db.commit()
        mail.run_once(db)
        msg = db.query(MailMessage).one()
        assert msg.state == 'retryable'
        job = db.get(WorkItem, msg.id)
        job.available_at = utcnow() - timedelta(seconds=1)
        db.commit()
        mail.run_once(db)
        assert msg.state == 'sent' and msg.payload is None
        assert len(calls) == 2
        assert calls[0][1]['headers']['Idempotency-Key'] == calls[1][1]['headers']['Idempotency-Key'] == msg.id
        assert calls[0][0] == 'https://api.resend.com/emails'
        assert set(calls[0][1]['json']) == {'from', 'to', 'subject', 'text'}
        assert db.get(OperationalCounter, ('mail', utcnow().date().isoformat())).used == 2
        assert 'SENSITIVE' not in caplog.text and user.email not in caplog.text


def test_mail_store_export_purge_and_key_binding(db_engine, monkeypatch):
    from backend.core.owned_stores import _registry, validate_coverage
    from backend.finance.storage import configured_storage
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    with Session(db_engine) as db:
        user = owner(db)
        notice(db, user)
        db.commit()
        msg = db.query(MailMessage).one()
        with pytest.raises(ValueError):
            configured_storage().unseal(user.id + 1, 'mail:' + msg.id, msg.payload)
        validate_coverage()
        assert 'payload' not in _registry['mail'].export(db, user.id)['mail_messages'][0]
        _registry['mail'].purge(db, user.id)
        _registry['queue'].purge(db, user.id)
        db.commit()
        assert db.query(MailMessage).count() == 0


def test_mail_migration_roundtrip(tmp_path):
    from backend.core.migrations_runner import migrate, _alembic_cfg
    from alembic import command
    from sqlalchemy import create_engine, inspect
    url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    migrate(url, target='0180')
    engine = create_engine(url)
    assert 'mail_messages' in inspect(engine).get_table_names()
    engine.dispose()
    command.downgrade(_alembic_cfg(url), '0141')
    engine = create_engine(url)
    assert 'mail_messages' not in inspect(engine).get_table_names()
    engine.dispose()
    migrate(url, target='0180')


def test_quiet_hours_defer_without_spending_and_eventually_send(db_engine, monkeypatch):
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    with Session(db_engine) as db:
        user = owner(db)
        notice(db, user)
        pref = db.get(NotificationPreference, user.id)
        hour = (utcnow() + timedelta(hours=5, minutes=30)).hour
        pref.quiet_start, pref.quiet_end = hour, (hour + 1) % 24
        db.commit()
        mail.run_once(db)
        msg = db.query(MailMessage).one()
        assert msg.state == 'deferred' and msg.first_attempt_at is None
        assert db.query(OperationalCounter).count() == 0
        pref.quiet_start = pref.quiet_end = None
        db.get(WorkItem, msg.id).available_at = utcnow() - timedelta(seconds=1)
        db.commit()
        mail.run_once(db)
        assert msg.state == 'sent' and len(mail.fake_messages) == 1


def test_ambiguous_old_attempt_requires_review(db_engine, monkeypatch):
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    with Session(db_engine) as db:
        user = owner(db)
        notice(db, user)
        msg = db.query(MailMessage).one()
        msg.first_attempt_at = utcnow() - timedelta(hours=23)
        db.commit()
        mail.run_once(db)
        assert msg.state == 'review_required'
        assert db.get(WorkItem, msg.id).state == 'dead_letter'
        assert not mail.fake_messages


def test_expiry_and_cancelled_owner_never_send(db_engine, monkeypatch):
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    with Session(db_engine) as db:
        user = owner(db)
        notice(db, user)
        msg = db.query(MailMessage).one()
        msg.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        mail.run_once(db)
        assert msg.state == 'expired' and msg.payload is None
        notices.deliver(db, user.id, 'another', 'report_ready')
        user.is_active = False
        db.commit()
        mail.run_once(db)
        assert db.query(WorkItem).filter_by(state='cancelled').count() == 1
        assert not mail.fake_messages


@pytest.mark.parametrize('kind', ['obligation', 'goal'])
@pytest.mark.parametrize('changed', [False, True])
def test_planning_reminders_mail_rechecks_domain(db_engine, monkeypatch, kind, changed):
    from datetime import datetime
    from backend.services import planning_service as planning
    from backend.schemas import planning as p
    from backend.workers.notifications import run_once
    from tests.test_stage_c_statements import setup
    from tests.test_stage_d import write
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    clock = utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    monkeypatch.setattr(notices, 'utcnow', lambda: clock)
    monkeypatch.setattr(mail, 'utcnow', lambda: clock)
    monkeypatch.setattr('backend.workers.queue.utcnow', lambda: clock)
    monkeypatch.setattr(config, 'NOTIFICATION_EMAIL_ENABLED', True)
    with Session(db_engine) as db:
        user, account = setup(db)
        if kind == 'obligation':
            contract = p.ObligationWrite
            data = {'label': 'SECRET private bill', 'amount_paise': 123456, 'due_date': clock.date().isoformat()}
        else:
            contract = p.GoalWrite
            data = {'label': 'SECRET private goal', 'target_paise': 123456, 'target_date': clock.date().isoformat(), 'funding_account_id': account.id}
        item = planning.write(db, user.id, kind, write(contract, {**data, 'reminder_opt_in': True}))
        db.add(NotificationPreference(user_id=user.id, email_enabled=True,
            verified_email_hash=hashlib.sha256(user.email.encode()).hexdigest()))
        db.commit()
        assert run_once(db)
        assert db.query(MailMessage).count() == 1
        if changed:
            planning.write(db, user.id, kind, write(contract, {**data, 'reminder_opt_in': False}, 1), item['id'])
        assert mail.run_once(db)
        assert db.query(MailMessage).one().state == ('suppressed' if changed else 'sent')
        assert len(mail.fake_messages) == (0 if changed else 1)
        assert 'SECRET' not in str(mail.fake_messages) and '123456' not in str(mail.fake_messages)
