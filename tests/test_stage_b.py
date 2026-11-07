from sqlalchemy.orm import Session
from backend.models.models import AuthSession, User, ConsentRecord, WorkItem, utcnow
from backend.services.auth_service import AuthService
from backend.services.consent_service import allowed
from backend.core import owned_stores
from backend.workers import queue
import pytest
from datetime import timedelta

def signup(db, name="fictional"):
    result = AuthService(db).signup(name + "@example.test", name, "Safe-fictional-pass-987")
    return db.get(User, result["user_id"])

def test_session_password_controls(db_engine):
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, "other")
        service = AuthService(db)
        sid = service.list_sessions(a.id)[0].id
        with pytest.raises(Exception) as error:
            service.revoke_session(b.id, sid)
        assert error.value.status_code == 404
        service.change_password(a, "Safe-fictional-pass-987", "Changed-fictional-987")
        assert all(s.revoked_at for s in service.list_sessions(a.id))
        assert service.login(a.email, "Changed-fictional-987")

def test_consent_queue_and_registry(db_engine):
    with Session(db_engine) as db:
        a = signup(db)
        db.add(ConsentRecord(user_id=a.id, purpose="model_inference", granted=True, notice_version="v1"))
        row = queue.enqueue(db, a.id, "synthetic-event", "report", "model_inference")
        db.commit()
        assert queue.enqueue(db, a.id, "synthetic-event", "report", "model_inference").id == row.id
        job, fence = queue.claim(db)
        db.add(ConsentRecord(user_id=a.id, purpose="model_inference", granted=False, notice_version="v1"))
        db.commit()
        assert not allowed(db, a.id, "model_inference")
        queue.complete(db, job, fence, lambda *_: pytest.fail("withdrawn job published"))
        assert db.get(WorkItem, job).state == "cancelled"
        owned_stores.validate_coverage()

def test_expired_lease_fences_old_worker(db_engine):
    with Session(db_engine) as db:
        a = signup(db)
        row = queue.enqueue(db, a.id, "event", "synthetic")
        db.commit()
        job, old = queue.claim(db)
        row.lease_until = utcnow() - timedelta(seconds=1)
        db.commit()
        job, new = queue.claim(db)
        with pytest.raises(ValueError):
            queue.complete(db, job, old, lambda *_: pytest.fail("stale publication"))
        seen = []
        queue.complete(db, job, new, lambda _, owner: seen.append(owner))
        assert seen == [a.id]

def test_migration_roundtrip(tmp_path):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    cfg = _alembic_cfg(url)
    command.upgrade(cfg, 'head')
    from sqlalchemy import create_engine, inspect
    engine = create_engine(url)
    assert {'consent_records', 'work_items'} <= set(inspect(engine).get_table_names())
    command.downgrade(cfg, '0003')
    assert 'work_items' not in inspect(engine).get_table_names()
    command.upgrade(cfg, 'head')
    assert 'work_items' in inspect(engine).get_table_names()
    engine.dispose()


def test_notifications(db_engine):
    from backend.services.notification_service import deliver, preferences
    from backend.models.models import NotificationPreference
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, 'second')
        assert preferences(db, a.id).enabled
        first = deliver(db, a.id, 'notice-1', 'report_ready')
        db.commit()
        assert deliver(db, a.id, 'notice-1', 'report_ready').id == first.id
        db.add(NotificationPreference(user_id=b.id, enabled=False, categories=[]))
        db.commit()
        assert deliver(db, b.id, 'notice-1', 'report_ready').state == 'suppressed'
        with pytest.raises(ValueError):
            deliver(db, a.id, 'bad', 'private balance')
        owned_stores.validate_coverage()

def test_account_api(client):
    def auth(email):
        response = client.post('/auth/signup', json={'email': email, 'full_name': 'Fictional User', 'password': 'Fictional-safe-pass-987'})
        assert response.status_code == 200, response.text
        return {'Authorization': 'Bearer ' + response.json()['access_token']}
    a, b = auth('a@example.com'), auth('b@example.com')
    sid = client.get('/sessions', headers=a).json()[0]['id']
    assert client.delete('/sessions/' + sid, headers=b).status_code == 404
    assert client.put('/preferences', headers=a, json={'enabled': False, 'categories': []}).status_code == 200
    assert client.get('/preferences', headers=b).json()['enabled'] is True
    assert client.put('/preferences', headers=a, json={'quiet_start': 23}).status_code == 422
    assert client.post('/privacy/consents', headers=a, json={'purpose': 'tracing', 'granted': False, 'notice_version': 'v1'}).status_code == 201
    assert client.post('/auth/password-change', headers=a, json={'password': 'Fictional-safe-pass-987', 'new_password': 'Changed-fictional-pass-987'}).status_code == 204
    assert client.get('/sessions', headers=a).status_code == 401


def test_queue_heartbeat_and_dead_letter(db_engine):
    with Session(db_engine) as db:
        a = signup(db)
        row = queue.enqueue(db, a.id, 'expire', 'synthetic')
        db.commit()
        for _ in range(queue.MAX_ATTEMPTS):
            job, fence = queue.claim(db)
            assert queue.heartbeat(db, job, fence)
            assert not queue.heartbeat(db, job, fence + 1)
            db.refresh(row)
            row.lease_until = utcnow() - timedelta(seconds=1)
            db.commit()
        assert queue.claim(db) is None
        assert queue.sweep_exhausted(db) == 1
        assert queue.metrics(db) == {'dead_letter': 1}

def test_export_delete_restore_drill(db_engine, tmp_path):
    from backend.services.privacy.lifecycle import SuppressionJournal, export_owned, delete_owned
    from deployment.recovery import backup, restore
    from backend.models.models import FinancialProfile
    from sqlalchemy import create_engine
    journal = SuppressionJournal(tmp_path / 'separate-journal.db')
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, 'survivor')
        aid, bid = a.id, b.id
        db.add(FinancialProfile(user_id=aid, monthly_income_paise=1234567))
        db.add(FinancialProfile(user_id=bid, monthly_income_paise=7654321))
        db.commit()
        data = export_owned(db, a, 'Safe-fictional-pass-987')
        assert data['stores']['finance']['financial_profiles'][0]['monthly_income_paise'] == 1234567
        source = db_engine.url.database
        backup(source, tmp_path / 'pre-delete.db')
        assert delete_owned(db, a, 'Safe-fictional-pass-987', journal)['status'] == 'live_complete'
        assert db.query(FinancialProfile).filter_by(user_id=aid).count() == 0
    restore(tmp_path / 'pre-delete.db', tmp_path / 'restored.db', journal)
    restored = create_engine('sqlite:///' + (tmp_path / 'restored.db').as_posix())
    with Session(restored) as db:
        assert not db.get(User, aid).is_active
        assert db.query(FinancialProfile).filter_by(user_id=aid).count() == 0
        assert db.query(FinancialProfile).filter_by(user_id=bid).one().monthly_income_paise == 7654321
    restored.dispose()

def test_quotas_are_atomic_and_owner_scoped(db_engine):
    from backend.core.limits import reserve
    from backend.models.models import QuotaUsage
    with Session(db_engine) as db:
        a, b = signup(db), signup(db, 'quota-other')
        reserve(db, a.id, 'jobs', 2, 2)
        db.commit()
        with pytest.raises(Exception) as error:
            reserve(db, a.id, 'jobs', 1, 2)
        assert error.value.status_code == 429
        reserve(db, b.id, 'jobs', 1, 2)
        db.rollback()
        assert db.query(QuotaUsage).filter_by(user_id=a.id).one().used == 2
        with pytest.raises(ValueError):
            reserve(db, a.id, 'jobs', -1, 2)
