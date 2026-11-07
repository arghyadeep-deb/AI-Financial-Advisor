from datetime import timedelta
import pytest
from sqlalchemy.orm import Session
from backend.core.config import config, Config, ConfigError
from backend.models.models import WorkItem, utcnow
from backend.services import notification_service as notices
from backend.workers import queue
from tests.test_stage_b import signup


def auth(client, email='lifecycle@example.com'):
    result = client.post('/auth/signup', json={'email': email, 'full_name': 'Synthetic Person',
                          'password': 'Fictional-safe-pass-987'})
    assert result.status_code == 200, result.text
    return {'Authorization': 'Bearer ' + result.json()['access_token']}


def test_lifecycle_api(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(tmp_path / 'separate.db'))
    a, b = auth(client), auth(client, 'survivor@example.com')
    assert client.get('/privacy/consents', headers=a).json() == {'model_inference': False, 'tracing': False}
    assert client.post('/privacy/export', headers=a, json={'password': 'wrong'}).status_code == 401
    exported = client.post('/privacy/export', headers=a, json={'password': 'Fictional-safe-pass-987'})
    assert exported.status_code == 200 and exported.headers['cache-control'] == 'no-store'
    assert 'hashed_password' not in exported.text and 'token_hash' not in exported.text
    deleted = client.post('/privacy/deletion', headers=a, json={'password': 'Fictional-safe-pass-987'})
    assert deleted.status_code == 202 and deleted.json()['backup_status'] == 'expiry_unapproved'
    assert client.get('/sessions', headers=a).status_code == 401
    assert client.get('/sessions', headers=b).status_code == 200


@pytest.mark.parametrize('path,body,setting', [('/analysis', {'analysis_type': 'quick'}, 'ANALYSIS_DAILY_LIMIT'),
    ('/chat', {'message': 'hello', 'client_message_id': 'quota-001'}, 'CHAT_DAILY_LIMIT'),
    ('/chat/stream', {'message': 'hello', 'client_message_id': 'quota-002'}, 'CHAT_DAILY_LIMIT')])
def test_api_quota_before_expensive_work(client, monkeypatch, path, body, setting):
    a = auth(client)
    monkeypatch.setattr(config, setting, 0)
    response = client.post(path, headers=a, json=body)
    assert response.status_code == 429, response.text
    assert int(response.headers['retry-after']) > 0
    assert response.json()['code'] == 'rate_limited'


def test_config_bounds(monkeypatch):
    c = Config()
    monkeypatch.setattr(c, 'SOURCE_RETENTION_DAYS', 0)
    with pytest.raises(ConfigError):
        c.validate()


def test_scheduled_notification_and_alert(db_engine, monkeypatch):
    from backend.observability.health import snapshot
    with Session(db_engine) as db:
        owner = signup(db)
        job = notices.schedule(db, owner.id, 'synthetic', 'reminder', utcnow() - timedelta(seconds=400))
        job.created_at = utcnow() - timedelta(seconds=400)
        db.commit()
        health = snapshot(db)
        assert health['alerts'][0]['code'] == 'queue_stale'
        assert 'user_id' not in str(health) and owner.email not in str(health)
        claimed = queue.claim(db)
        notices.run_scheduled(db, *claimed)
        assert db.get(WorkItem, job.id).state == 'complete'


def test_deletion_failure_resumes_and_suppresses(db_engine, tmp_path, monkeypatch):
    from backend.services.privacy.lifecycle import SuppressionJournal, delete_owned, resume_delete
    from backend.core.owned_stores import _registry
    from backend.models.models import User
    journal = SuppressionJournal(tmp_path / 'journal.db')
    with Session(db_engine) as db:
        owner = signup(db)
        store = _registry['finance']
        original = store.purge
        def fail(*args):
            raise RuntimeError('synthetic interruption')
        object.__setattr__(store, 'purge', fail)
        try:
            with pytest.raises(RuntimeError):
                delete_owned(db, owner, 'Safe-fictional-pass-987', journal)
        finally:
            object.__setattr__(store, 'purge', original)
        assert not db.get(User, owner.id).is_active
        assert owner.id in journal.owners()
        resume_delete(db, owner.id, journal)
        assert db.get(User, owner.id).full_name == 'Deleted account'


def test_chat_quota_owner_scope_and_completed_replay(client, monkeypatch):
    monkeypatch.setattr(config, 'CHAT_DAILY_LIMIT', 1)
    a, b = auth(client), auth(client, 'quota-second@example.com')
    payload = {'message': 'Hello synthetic', 'client_message_id': 'quota-message-001'}
    first = client.post('/chat', headers=a, json=payload)
    assert first.status_code == 200
    replay = client.post('/chat', headers=a, json=payload)
    assert replay.status_code == 200 and replay.json()['replayed']
    assert client.post('/chat', headers=a, json={**payload, 'client_message_id': 'quota-message-002'}).status_code == 429
    assert client.post('/chat', headers=b, json=payload).status_code == 200

