"""Lane G acceptance: fictional fixtures, real migrated SQLite, no integrations."""
import json
import sqlite3
import time
from datetime import datetime, timedelta
from uuid import uuid4
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from backend.core.config import config, Config, ConfigError
from backend.models.models import (Base, OperationalCounter, QuotaUsage, User, FinancialProfile,
    StatementDocument, PrivacyRequest, WorkItem, DeliveryAttempt, NotificationPreference, utcnow)
from backend.services.privacy.lifecycle import SuppressionJournal, delete_owned, export_owned, resume_delete
from backend.services import planning_service as planning, notification_service as notices
from backend.schemas import planning as p
from backend.workers import queue
from backend.workers.operations import run_once
from backend.finance.storage import configured_storage, LocalEncryptedStorage
from tests.test_stage_b import signup
from tests.test_stage_c_statements import synthetic_config, setup, imported, publish, load
from tests.test_stage_c_platform import auth
from tests.test_stage_d import write


def test_migration_registry_and_reversible_aggregate_table(db_engine):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.owned_stores import validate_coverage, _registry
    validate_coverage()
    assert {c.name for c in Base.metadata.tables['operational_counters'].columns} == {
        c['name'] for c in inspect(db_engine).get_columns('operational_counters')}
    assert _registry['operations'].export(None, 1) == {}
    assert _registry['operations'].purge(None, 1) is None
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0110')
    assert 'operational_counters' not in inspect(db_engine).get_table_names()
    command.upgrade(cfg, 'head')
    assert 'operational_counters' in inspect(db_engine).get_table_names()


def test_retention_tick_due_idempotent_holds_and_safe_orphans(db_engine, tmp_path):
    from backend.services.privacy import exports
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        doc = db.get(StatementDocument, job.document_id)
        storage = configured_storage()
        doc.expires_at = utcnow() - timedelta(days=1)
        hold = journal.place_hold(owner.id, 'court_order', utcnow() + timedelta(days=1), 'account')
        receipt = exports.create(db, owner, 'Safe-fictional-pass-987')
        request = db.get(PrivacyRequest, receipt['id'])
        export_path = storage.path(owner.id, request.storage_key)
        first = run_once(db, journal)
        assert first['expired_sources'] == 0 and export_path.exists()
        assert storage.path(owner.id, doc.storage_key).exists()
        journal.release_hold(owner.id, hold)
        assert not run_once(db, journal)['retention_ran']
        row = db.get(OperationalCounter, ('retention_sweep', 'current'))
        row.updated_at = utcnow() - timedelta(days=1)
        request.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        second = run_once(db, journal)
        assert second['expired_sources'] == second['expired_exports'] == 1
        assert not export_path.exists() and not storage.path(owner.id, doc.storage_key).exists()
        # Ledger/source metadata survives expiration, new active export survives orphan scan.
        assert db.get(StatementDocument, doc.id)
        fresh = exports.create(db, owner, 'Safe-fictional-pass-987')
        result = run_once(db, journal, quiesced_orphans=True)
        assert result['orphan_objects'] == 0
        assert storage.path(owner.id, fresh['id']).exists()


def test_legal_hold_blocks_access_preserves_data_restore_and_receipt(db_engine, tmp_path):
    from deployment.recovery import backup, restore
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with Session(db_engine) as db:
        owner = signup(db)
        db.add(FinancialProfile(user_id=owner.id, monthly_income_paise=1234567))
        db.commit()
        identity = owner.id
        backup(db_engine.url.database, tmp_path / 'before.db')
        hold = journal.place_hold(identity, 'statutory_preservation', utcnow() + timedelta(days=1), 'account')
        result = delete_owned(db, owner, 'Safe-fictional-pass-987', journal)
        assert result['status'] == 'held' and not owner.is_active
        assert db.query(FinancialProfile).count() == 1
        receipt = journal.receipt(result['receipt_token'])
        assert receipt['status'] == 'held' and receipt['backup_status'] == 'expiry_unapproved'
        assert not {'user_id', 'email', 'basis'} & receipt.keys()
        with pytest.raises(HTTPException) as error:
            journal.receipt('wrong')
        assert error.value.status_code == 404
        restore(tmp_path / 'before.db', tmp_path / 'restored.db', journal)
        restored = create_engine('sqlite:///' + (tmp_path / 'restored.db').as_posix())
        with Session(restored) as recovered:
            assert not recovered.get(User, identity).is_active
            assert recovered.query(FinancialProfile).count() == 1
        restored.dispose()
        journal.release_hold(identity, hold)
        run_once(db, journal)
        assert db.query(FinancialProfile).count() == 0
        assert journal.receipt(result['receipt_token'])['status'] == 'live_complete'


@pytest.mark.parametrize('basis,days,scope', [('unknown', 1, 'account'), ('court_order', 91, 'account'),
    ('court_order', -1, 'account'), ('court_order', 1, '*')])
def test_invalid_holds_denied(tmp_path, basis, days, scope):
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with pytest.raises(ValueError):
        journal.place_hold(1, basis, utcnow() + timedelta(days=days), scope)


def test_journal_legacy_additive_upgrade_and_receipt_api(client, tmp_path, monkeypatch):
    path = tmp_path / 'journal.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE suppression(user_id INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE deletion_events(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(path))
    headers = auth(client)
    deleted = client.post('/privacy/deletion', headers=headers, json={'password': 'Fictional-safe-pass-987'})
    assert deleted.status_code == 202, deleted.text
    token = deleted.json()['receipt_token']
    assert deleted.headers['cache-control'] == 'no-store'
    assert client.get('/sessions', headers=headers).status_code == 401
    response = client.post('/privacy/deletion-receipt', json={'token': token})
    assert response.status_code == 200 and response.json()['status'] == 'live_complete'
    assert response.headers['cache-control'] == 'no-store'
    assert client.post('/privacy/deletion-receipt', json={'token': 'x' * 43}).status_code == 404
    assert token.encode() not in path.read_bytes()


def test_readiness_due_queue_worker_db_failure_and_safe_alerts(db_engine, tmp_path):
    from backend.observability.health import readiness
    from backend.core.operations import heartbeat
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with Session(db_engine) as db:
        owner = signup(db)
        future = notices.schedule(db, owner.id, 'future', 'reminder', utcnow() + timedelta(days=30))
        future.created_at = utcnow() - timedelta(days=30)
        db.commit()
        initial = readiness(db, journal=journal)
        assert not initial['ready'] and 'queue_stale' not in str(initial)
        for worker in ('notifications', 'statements', 'retention'):
            heartbeat(db, worker)
        db.commit()
        assert readiness(db, journal=journal)['ready']
        future.available_at = utcnow() - timedelta(seconds=601)
        row = db.get(OperationalCounter, ('worker:notifications', 'current'))
        row.updated_at = utcnow() - timedelta(seconds=601)
        journal.suppress(owner.id)
        journal.event(owner.id, 'access_blocked')
        with sqlite3.connect(journal.path) as raw:
            raw.execute("UPDATE deletion_events SET created_at='2020-01-01 00:00:00'")
        db.commit()
        health = readiness(db, journal=journal)
        assert {a['code'] for a in health['alerts']} >= {'queue_stale', 'worker_stale', 'deletion_stale'}
        assert all(a['owner'] and a['action'] for a in health['alerts'])
        assert owner.email not in str(health) and 'user_id' not in str(health)
    class Down:
        def execute(self, *_):
            raise RuntimeError('private DB address')
        def rollback(self):
            pass
    assert readiness(Down())['database_ready'] is False
    assert 'private' not in str(readiness(Down()))


def test_zero_default_and_atomic_owner_global_model_budgets(db_engine, monkeypatch):
    from backend.core.limits import reserve_model_attempt
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, 'budget-other')
        with pytest.raises(HTTPException) as error:
            reserve_model_attempt(db, a.id, 100, 10)
        assert error.value.status_code == 429
        db.rollback()
        for setting, value in [('MODEL_DAILY_TOKEN_LIMIT', 200), ('MODEL_DAILY_COST_PAISE', 20),
                               ('GLOBAL_MODEL_DAILY_COST_PAISE', 30)]:
            monkeypatch.setattr(config, setting, value)
        reserve_model_attempt(db, a.id, 100, 10)
        db.commit()  # failed provider consumes the reservation as well
        reserve_model_attempt(db, a.id, 100, 10)
        db.commit()
        with pytest.raises(HTTPException):
            reserve_model_attempt(db, a.id, 1, 1)
        db.rollback()
        reserve_model_attempt(db, b.id, 100, 10)
        db.commit()
        with pytest.raises(HTTPException):
            reserve_model_attempt(db, b.id, 1, 1)
        db.rollback()
        assert db.get(OperationalCounter, ('model_cost_paise', utcnow().date().isoformat())).used == 30
        assert db.query(QuotaUsage).filter_by(user_id=b.id, resource='model_tokens').one().used == 100
        assert export_owned(db, a, 'Safe-fictional-pass-987')['account']['id'] == a.id


def test_source_storage_cap_preserves_existing_access(db_engine, monkeypatch):
    from backend.services.statement_service import upload
    with Session(db_engine) as db:
        owner, account = setup(db)
        monkeypatch.setattr(config, 'SOURCE_STORAGE_LIMIT_BYTES', len(load()))
        first = upload(db, owner.id, account.id, load())
        assert upload(db, owner.id, account.id, load()).id == first.id
        db.get(StatementDocument, first.document_id).expires_at = utcnow() - timedelta(days=1)
        db.commit()  # expired bytes still occupy storage until the retention job
        with pytest.raises(HTTPException) as error:
            upload(db, owner.id, account.id, load() + b'\n')
        assert error.value.status_code == 429
        db.rollback()
        assert configured_storage().get(owner.id, first.document_id) == load()


def test_recovery_abuse_same_response_known_unknown_no_unbounded_tokens(client, monkeypatch):
    from backend.services import auth_service
    from backend.models.models import PasswordResetToken
    auth(client)
    sent = []
    monkeypatch.setattr(auth_service, 'recovery_delivery', lambda *args: sent.append(True))
    bodies = []
    for _ in range(config.LOGIN_MAX_FAILURES + 3):
        for email in ('lifecycle@example.com', 'unknown@example.com'):
            response = client.post('/auth/password-reset/request', json={'email': email})
            assert response.status_code == 202
            bodies.append(response.json())
    assert all(b == bodies[0] for b in bodies)
    assert len(sent) == config.LOGIN_MAX_FAILURES
    with client.session_factory() as db:
        assert db.query(PasswordResetToken).count() == config.LOGIN_MAX_FAILURES


def test_timed_export_delete_restore_and_key_rotation_drill(db_engine, tmp_path, capsys):
    from deployment.recovery import backup, restore
    journal = SuppressionJournal(tmp_path / 'journal.db')
    started = time.perf_counter()
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, 'survivor')
        aid, bid = a.id, b.id
        db.add_all([FinancialProfile(user_id=aid, monthly_income_paise=1234567),
                    FinancialProfile(user_id=bid, monthly_income_paise=7654321)])
        db.commit()
        before = export_owned(db, b, 'Safe-fictional-pass-987')
        backup(db_engine.url.database, tmp_path / 'backup.db')
        delete_owned(db, a, 'Safe-fictional-pass-987', journal)
    restore(tmp_path / 'backup.db', tmp_path / 'restored.db', journal)
    engine = create_engine('sqlite:///' + (tmp_path / 'restored.db').as_posix())
    with Session(engine) as db:
        assert not db.get(User, aid).is_active
        assert db.query(FinancialProfile).count() == 1
        assert db.query(FinancialProfile).one().monthly_income_paise == 7654321
        after = export_owned(db, db.get(User, bid), 'Safe-fictional-pass-987')
        assert before == after
    engine.dispose()
    key1, key2 = Fernet.generate_key(), Fernet.generate_key()
    identity = str(uuid4())
    storage = LocalEncryptedStorage(tmp_path / 'rotated', {'old': key1}, 'old')
    storage.put(bid, identity, b'fictional recovery marker')
    rotating = LocalEncryptedStorage(storage.root, {'old': key1, 'new': key2}, 'new')
    rotating.rotate(bid, identity)
    retired = LocalEncryptedStorage(storage.root, {'new': key2}, 'new')
    assert retired.get(bid, identity) == b'fictional recovery marker'
    with pytest.raises(FileNotFoundError):
        retired.get(aid, identity)
    old_identity = str(uuid4())
    storage.put(bid, old_identity, b'old ciphertext')
    with pytest.raises(ValueError):
        retired.get(bid, old_identity)
    assert storage.get(bid, old_identity) == b'old ciphertext'
    assert (time.perf_counter() - started) > 0
    with capsys.disabled():
        print(f'\nG restore/export/delete/key drill elapsed={time.perf_counter() - started:.3f}s; survivor_rows=1; survivor_total_paise=7654321; deleted_rows=0')


@pytest.mark.parametrize('kind', ['obligation', 'goal'])
def test_domain_reminder_optin_quiet_hours_outage_replay_metadata(db_engine, monkeypatch, kind):
    from backend.workers.notifications import run_once as work
    clock = datetime(2026, 11, 7, 4, 30)
    monkeypatch.setattr(notices, 'utcnow', lambda: clock)
    monkeypatch.setattr('backend.workers.queue.utcnow', lambda: clock)
    with Session(db_engine) as db:
        owner, account = setup(db)
        if kind == 'obligation':
            contract = p.ObligationWrite
            data = {'label': 'SECRET private bill', 'amount_paise': 123456, 'due_date': '2026-11-07'}
        else:
            contract = p.GoalWrite
            data = {'label': 'SECRET private goal', 'target_paise': 123456, 'target_date': '2026-11-07', 'funding_account_id': account.id}
        initial = planning.write(db, owner.id, kind, write(contract, data))
        assert db.query(WorkItem).filter_by(kind='notification').count() == 0
        payload = write(contract, {**data, 'reminder_opt_in': True}, 1)
        result = planning.write(db, owner.id, kind, payload, initial['id'])
        assert planning.write(db, owner.id, kind, payload, initial['id']) == result
        db.add(NotificationPreference(user_id=owner.id, enabled=True, categories=['reminder'], quiet_start=9, quiet_end=11))
        db.commit()
        job = db.query(WorkItem).filter_by(kind='notification').one()
        job.created_at = clock - timedelta(days=30)  # a long-planned goal is fresh at its due date
        db.commit()
        assert 'SECRET' not in job.event_key and '123456' not in job.event_key
        assert work(db)
        db.refresh(job)
        assert job.state == 'queued'
        assert db.query(DeliveryAttempt).one().state == 'deferred'
        clock = datetime(2026, 11, 7, 6, 0)
        original = notices.deliver
        def fail(*args):
            original(*args)
            raise RuntimeError('fictional worker outage')
        monkeypatch.setattr(notices, 'deliver', fail)
        claimed = queue.claim(db, kind='notification')
        with pytest.raises(RuntimeError):
            notices.run_scheduled(db, *claimed)
        assert db.query(DeliveryAttempt).one().state == 'deferred'
        monkeypatch.setattr(notices, 'deliver', original)
        clock += timedelta(minutes=1)
        assert work(db)
        assert db.query(DeliveryAttempt).count() == 1
        assert db.query(DeliveryAttempt).one().state == 'delivered'
        assert not work(db)
        assert notices.COPY['reminder'] == 'You have a reminder to review.'


@pytest.mark.parametrize('change', ['revision', 'global_optout', 'archived', 'funded', 'expired'])
def test_goal_delivery_rechecks_latest_owner_state(db_engine, monkeypatch, change):
    clock = datetime(2026, 11, 7, 6, 0)
    monkeypatch.setattr(notices, 'utcnow', lambda: clock)
    monkeypatch.setattr('backend.workers.queue.utcnow', lambda: clock)
    with Session(db_engine) as db:
        owner, account = setup(db)
        data = {'label': 'Private', 'target_paise': 500, 'target_date': '2026-11-07', 'funding_account_id': account.id, 'reminder_opt_in': True}
        goal = planning.write(db, owner.id, 'goal', write(p.GoalWrite, data))
        if change == 'global_optout':
            db.add(NotificationPreference(user_id=owner.id, enabled=False, categories=[]))
            db.commit()
        elif change == 'expired':
            clock += timedelta(days=8)
        else:
            update = {'revision': {'reminder_opt_in': False}, 'archived': {'archived': True}, 'funded': {'allocated_paise': 500}}[change]
            planning.write(db, owner.id, 'goal', write(p.GoalWrite, {**data, **update}, 1), goal['id'])
        while claimed := queue.claim(db, kind='notification'):
            notices.run_scheduled(db, *claimed)
        assert db.query(DeliveryAttempt).filter_by(state='delivered').count() == 0


def test_receipt_token_does_not_authorize_other_resources(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(tmp_path / 'journal.db'))
    headers = auth(client)
    result = client.post('/privacy/deletion', headers=headers, json={'password': 'Fictional-safe-pass-987'}).json()
    assert client.get('/sessions', headers={'Authorization': 'Bearer ' + result['receipt_token']}).status_code == 401


@pytest.mark.parametrize('setting,value', [('RETENTION_INTERVAL_SECONDS', 0), ('WORKER_STALE_SECONDS', 1), ('SOURCE_STORAGE_LIMIT_BYTES', -1), ('MODEL_DAILY_COST_PAISE', -1)])
def test_operations_config_invalid_bounds(setting, value, monkeypatch):
    c = Config()
    monkeypatch.setattr(c, setting, value)
    with pytest.raises(ConfigError):
        c.validate()


def test_runnable_operations_cli_uses_temp_db_only(db_engine, tmp_path):
    import os
    import subprocess
    import sys
    env = dict(os.environ, DATABASE_URL=str(db_engine.url), APP_ENV='test',
        SUPPRESSION_JOURNAL=str(tmp_path / 'journal.db'), PRIVATE_STORAGE_ROOT=str(tmp_path / 'objects'),
        STORAGE_ACTIVE_KEY='v1', STORAGE_KEYS_JSON=json.dumps({'v1': Fernet.generate_key().decode()}))
    completed = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'backend.workers.operations'],
        env=env, capture_output=True, text=True, timeout=30, check=True)
    result = json.loads(completed.stdout)
    assert result['retention_ran'] and result['expired_sources'] == result['expired_exports'] == 0
    assert 'journal' not in completed.stdout and 'user_id' not in completed.stdout


def test_recovery_atomic_admission_concurrent_and_window_expiry(db_engine):
    from concurrent.futures import ThreadPoolExecutor
    from backend.core.throttle import consume_attempt
    now = datetime(2026, 11, 7, 0, 0)
    def attempt(_):
        with Session(db_engine) as db:
            return consume_attempt(db, 'recovery:fictional@example.com', now)
    with ThreadPoolExecutor(max_workers=8) as pool:
        result = list(pool.map(attempt, range(12)))
    assert sum(result) == config.LOGIN_MAX_FAILURES
    with Session(db_engine) as db:
        assert consume_attempt(db, 'recovery:fictional@example.com', now + timedelta(seconds=config.LOGIN_WINDOW_SECONDS + config.LOGIN_LOCK_SECONDS + 1))


def test_deferred_quiet_overnight_and_optout_on_resume(db_engine, monkeypatch):
    clock = datetime(2026, 11, 7, 18, 0)  # 23:30 Kolkata
    monkeypatch.setattr(notices, 'utcnow', lambda: clock)
    monkeypatch.setattr('backend.workers.queue.utcnow', lambda: clock)
    with Session(db_engine) as db:
        owner = signup(db)
        db.add(NotificationPreference(user_id=owner.id, enabled=True, categories=['reminder'], quiet_start=22, quiet_end=7))
        notices.schedule(db, owner.id, 'fictional-event', 'reminder', clock)
        db.commit()
        notices.run_scheduled(db, *queue.claim(db, kind='notification'))
        assert db.query(DeliveryAttempt).one().state == 'deferred'
        db.get(NotificationPreference, owner.id).enabled = False
        db.commit()
        clock += timedelta(hours=1)
        notices.run_scheduled(db, *queue.claim(db, kind='notification'))
        assert db.query(DeliveryAttempt).one().state == 'suppressed'


def test_legal_hold_expiry_resumes_without_false_backup_erasure(db_engine, tmp_path):
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with Session(db_engine) as db:
        owner = signup(db)
        journal.place_hold(owner.id, 'court_order', utcnow() + timedelta(seconds=10), 'account')
        result = delete_owned(db, owner, 'Safe-fictional-pass-987', journal)
        assert result['status'] == 'held'
        with sqlite3.connect(journal.path) as raw:
            row = raw.execute("SELECT id,metadata_json FROM deletion_events WHERE state='legal_hold'").fetchone()
            metadata = json.loads(row[1])
            metadata['expires_at'] = '2020-01-01T00:00:00'
            raw.execute('UPDATE deletion_events SET metadata_json=? WHERE id=?', (json.dumps(metadata), row[0]))
        run_once(db, journal)
        receipt = journal.receipt(result['receipt_token'])
        assert receipt['status'] == 'live_complete' and receipt['backup_status'] == 'expiry_unapproved'
