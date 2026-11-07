"""Indexed external-journal receipt migration and bounded DB admission races."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.orm import Session
import pytest
from backend.core import throttle
from backend.core.config import config
from backend.models.models import LoginThrottle
from backend.controllers.platform_controller import receipt_admission
from backend.services.privacy.lifecycle import SuppressionJournal
from backend.services.privacy.journal_migrations import downgrade_receipt_lookup


@pytest.fixture(autouse=True)
def receipt_config(monkeypatch):
    monkeypatch.setattr(config, 'RECEIPT_SOURCE_LIMIT', 10)
    monkeypatch.setattr(config, 'RECEIPT_GLOBAL_LIMIT', 1000)
    monkeypatch.setattr(config, 'RECEIPT_WINDOW_SECONDS', 900)


def test_legacy_journal_migration_preserves_valid_tokens_and_uses_index(tmp_path):
    path = tmp_path / 'legacy.db'
    token = 's' * 43
    digest = hashlib.sha256(token.encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE deletion_events(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,metadata_json TEXT)')
        db.execute('INSERT INTO deletion_events(user_id,state,metadata_json) VALUES (1,?,?)', ('receipt', json.dumps({'digest': digest})))
        db.execute("INSERT INTO deletion_events(user_id,state) VALUES (1,'live_complete')")
        db.executemany('INSERT INTO deletion_events(user_id,state,metadata_json) VALUES (?,?,?)',
            [(i + 2, 'receipt', json.dumps({'digest': hashlib.sha256(str(i).encode()).hexdigest()})) for i in range(1000)])
    journal = SuppressionJournal(path)
    assert journal.receipt(token)['status'] == 'live_complete'
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM deletion_events').fetchone()[0] == 1002
        assert db.execute('SELECT receipt_digest FROM deletion_events WHERE id=1').fetchone()[0] == digest
        query = "SELECT user_id,receipt_digest FROM deletion_events WHERE receipt_digest=? AND state='receipt' LIMIT 1"
        plan = str(db.execute('EXPLAIN QUERY PLAN ' + query, (digest,)).fetchall())
        assert 'ix_deletion_receipt_digest' in plan and 'SCAN deletion_events' not in plan
        downgrade_receipt_lookup(db)
        assert 'receipt_digest' not in {r[1] for r in db.execute('PRAGMA table_info(deletion_events)')}
        assert db.execute('SELECT metadata_json FROM deletion_events WHERE id=1').fetchone()[0] == json.dumps({'digest': digest})
    assert SuppressionJournal(path).receipt(token)['status'] == 'live_complete'


def test_receipt_lookup_constant_compare_on_hit_and_miss(tmp_path, monkeypatch):
    import secrets
    journal = SuppressionJournal(tmp_path / 'journal.db')
    token = journal.issue_receipt(1)
    calls = []
    original = secrets.compare_digest
    def compare(a, b):
        calls.append((len(a), len(b)))
        return original(a, b)
    monkeypatch.setattr(secrets, 'compare_digest', compare)
    assert journal.receipt(token)['status'] == 'access_blocked'
    with pytest.raises(HTTPException) as exc:
        journal.receipt('x' * 43)
    assert exc.value.status_code == 404
    assert calls == [(64, 64), (64, 64)]


def test_api_uniform_throttle_before_existence_lookup(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(tmp_path / 'journal.db'))
    monkeypatch.setattr(config, 'RECEIPT_SOURCE_LIMIT', 2)
    journal = SuppressionJournal(config.SUPPRESSION_JOURNAL)
    token = journal.issue_receipt(1)
    journal.event(1, 'live_complete')
    valid = client.post('/privacy/deletion-receipt', json={'token': token})
    missing = client.post('/privacy/deletion-receipt', json={'token': 'x' * 43})
    assert valid.status_code == 200 and valid.json()['status'] == 'live_complete'
    assert missing.status_code == 404
    assert valid.headers['Cache-Control'] == missing.headers['Cache-Control'] == 'no-store'
    # No journal access when limited, regardless of whether the token exists.
    monkeypatch.setattr(SuppressionJournal, 'receipt', lambda *a: pytest.fail('throttled lookup'))
    for value in (token, 'x' * 43):
        r = client.post('/privacy/deletion-receipt', json={'token': value}, headers={'X-Forwarded-For': 'attacker-controlled'})
        assert r.status_code == 429 and r.headers['Retry-After'] == '900'
        assert r.headers['Cache-Control'] == 'no-store'


def request(source):
    return Request({'type': 'http', 'client': (source, 12345), 'headers': [], 'method': 'POST', 'path': '/privacy/deletion-receipt'})


@pytest.mark.parametrize('global_cap', [False, True])
def test_concurrent_source_and_global_exact_caps(db_engine, monkeypatch, global_cap):
    monkeypatch.setattr(config, 'RECEIPT_SOURCE_LIMIT', 3 if not global_cap else 4)
    monkeypatch.setattr(config, 'RECEIPT_GLOBAL_LIMIT', 4 if global_cap else 100)
    def attempt(index):
        with Session(db_engine) as db:
            try:
                receipt_admission(request('192.0.2.' + str(index) if global_cap else '192.0.2.1'), db)
                return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(12)))
    assert results.count(200) == (4 if global_cap else 3)
    assert results.count(429) == (8 if global_cap else 9)
    with Session(db_engine) as db:
        assert db.get(LoginThrottle, throttle.key_for('receipt-global')).failures == (4 if global_cap else 12)
        assert all(r.failures <= 4 for r in db.query(LoginThrottle) if r.key != throttle.key_for('receipt-global'))


def test_bounded_source_buckets_and_no_raw_source(db_engine, monkeypatch):
    monkeypatch.setattr(config, 'RECEIPT_SOURCE_LIMIT', 1000)
    monkeypatch.setattr(config, 'RECEIPT_GLOBAL_LIMIT', 1000)
    # Source hash prefix has fixed 4096 possible values, independent of token.
    original = hashlib.sha256
    # Choose two actual colliding sources rather than mocking hash/throttle.
    seen = {}
    pair = None
    for i in range(10000):
        source = 'synthetic-' + str(i)
        prefix = original(source.encode()).hexdigest()[:3]
        if prefix in seen:
            pair = (seen[prefix], source)
            break
        seen[prefix] = source
    assert pair is not None
    with Session(db_engine) as db:
        for source in pair:
            receipt_admission(request(source), db)
        rows = db.query(LoginThrottle).all()
        assert len(rows) == 2
        assert all(len(row.key) == 64 and source not in row.key for row in rows)


def test_concurrent_legacy_journal_open_and_new_receipts(tmp_path):
    path = tmp_path / 'journal.db'
    def open_and_issue(index):
        journal = SuppressionJournal(path)
        token = journal.issue_receipt(index + 1)
        assert journal.receipt(token)['status'] == 'access_blocked'
        return token
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(open_and_issue, range(12)))
    assert len(set(tokens)) == 12


def test_receipt_window_reopens_without_extending_on_denial(db_engine, monkeypatch):
    from datetime import datetime, timedelta
    now = datetime(2026, 1, 1)
    with Session(db_engine) as db:
        kwargs = {'max_attempts': 2, 'window_seconds': 60, 'lock_seconds': 60}
        assert throttle.consume_attempt(db, 'receipt-test', now, **kwargs)
        assert throttle.consume_attempt(db, 'receipt-test', now, **kwargs)
        for _ in range(3):
            assert not throttle.consume_attempt(db, 'receipt-test', now + timedelta(seconds=30), **kwargs)
        row = db.get(LoginThrottle, throttle.key_for('receipt-test'))
        assert row.failures == 2 and row.locked_until == now + timedelta(seconds=60)
        assert throttle.consume_attempt(db, 'receipt-test', now + timedelta(seconds=61), **kwargs)
