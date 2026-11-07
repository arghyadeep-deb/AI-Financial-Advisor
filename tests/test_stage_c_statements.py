import json
from pathlib import Path
from uuid import uuid4
from datetime import timedelta
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from backend.core.config import config
from backend.models.models import (Base, StatementAccount, StatementDocument, StatementImport, StatementRow,
    LedgerEntry, LedgerEvidence, LedgerCorrection, LedgerLink, WorkItem, MonthlyReport, utcnow)
from backend.services import statement_service as service, monthly_report_service as reports
from backend.finance import ledger
from backend.schemas.statements import AccountCreate, Review, Operation, Split, LinkCreate, ReportCreate
from backend.workers import queue
from tests.test_stage_b import signup
from tests.test_stage_c_platform import auth

FIXTURES = Path(__file__).parent / 'fixtures' / 'statements'


@pytest.fixture(autouse=True)
def synthetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))


def load(name='supported.csv'):
    return (FIXTURES / name).read_bytes()


def op(revision, key=None, **extra):
    return dict(expected_revision=revision, idempotency_key=key or str(uuid4()), reason='Synthetic verification', **extra)


def imported(db, owner, account, content=None):
    job = service.upload(db, owner.id, account.id, load() if content is None else content)
    claimed = queue.claim(db, kind='statement')
    assert claimed
    service.process_claimed(db, *claimed)
    db.refresh(job)
    return job


def setup(db):
    owner = signup(db)
    account = service.create_account(db, owner.id, AccountCreate(label='Synthetic A', token='SYNTH_A'))
    return owner, account


def publish(db, owner, job, **extra):
    return ledger.publish(db, owner.id, job.id, Review(**op(job.revision, **extra)))


def test_migration_model_sync_and_roundtrip(tmp_path):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.database import create_db_engine
    url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    cfg = _alembic_cfg(url)
    command.upgrade(cfg, 'head')
    engine = create_db_engine(url)
    dbinfo = inspect(engine)
    new = [t for t in Base.metadata.tables if t.startswith(('statement_', 'ledger_', 'monthly_'))]
    assert len(new) == 9
    for table in new + ['privacy_requests']:
        assert {c.name for c in Base.metadata.tables[table].columns} == {c['name'] for c in dbinfo.get_columns(table)}
        assert {tuple(c.columns.keys()) for c in Base.metadata.tables[table].constraints if c.__class__.__name__ == 'UniqueConstraint'} == {
            tuple(c['column_names']) for c in dbinfo.get_unique_constraints(table)}
    command.downgrade(cfg, '0051')
    assert not set(new) & set(inspect(engine).get_table_names())
    command.upgrade(cfg, 'head')
    assert set(new) <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_exact_import_idempotency_report_and_overlap_reversal(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        assert job.state == 'needs_review' and job.difference_paise == 0
        assert service.upload(db, owner.id, account.id, load()).id == job.id
        request = Review(**op(job.revision))
        result = ledger.publish(db, owner.id, job.id, request)
        assert ledger.publish(db, owner.id, job.id, request) == result
        assert db.query(LedgerEntry).count() == 2
        report = reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id], expected_vector=reports.vector(db, owner.id)))
        metrics = report['snapshot']['metrics']
        assert (metrics['income_paise'], metrics['spending_paise'], metrics['recognized_surplus_paise'], metrics['shortfall_paise'], metrics['eligible_contribution_paise']) == (4500000, 5500000, -1000000, 1000000, 0)
        assert report['snapshot']['selected_scope_complete']
        original_export = reports.export_csv(db, owner.id, report['id'])
        overlap = imported(db, owner, account, load('overlap.csv'))
        publish(db, owner, overlap)
        assert db.query(LedgerEntry).filter_by(active=True).count() == 3
        assert db.query(LedgerEvidence).filter_by(active=True).count() == 5
        db.refresh(job)
        reversal = Operation(**op(job.revision))
        first = ledger.reverse(db, owner.id, job.id, reversal)
        assert ledger.reverse(db, owner.id, job.id, reversal) == first
        assert db.query(LedgerEntry).filter_by(active=True).count() == 3
        db.refresh(overlap)
        ledger.reverse(db, owner.id, overlap.id, Operation(**op(overlap.revision)))
        assert db.query(LedgerEntry).filter_by(active=True).count() == 0
        assert reports.read(db, owner.id, report['id'])['stale']
        assert reports.export_csv(db, owner.id, report['id']) == original_export
        with pytest.raises(Exception):
            db.execute(text("UPDATE monthly_reports SET rule_version='changed'"))
        db.rollback()


@pytest.mark.parametrize('fixture,state,error', [('mismatch.csv', 'needs_review', 'balance_mismatch'),
    ('unsupported.txt', 'quarantined', 'unsupported_format')])
def test_failed_reconciliation_never_publishes(db_engine, fixture, state, error):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account, load(fixture))
        assert (job.state, job.error_code) == (state, error)
        with pytest.raises(Exception) as exc:
            publish(db, owner, job)
        assert exc.value.status_code == 409
        assert db.query(LedgerEntry).count() == 0


def test_distinct_rows_overlap_review_and_splits(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        first = imported(db, owner, account, load('distinct.csv'))
        publish(db, owner, first)
        assert db.query(LedgerEntry).count() == 2
        content = load('distinct.csv').replace(b'2000.00,1000.00', b'3000.00,2000.00')
        overlap = imported(db, owner, account, content)
        with pytest.raises(Exception) as exc:
            publish(db, owner, overlap)
        assert exc.value.status_code == 409
        decisions = [{'row_id': row.id, 'category': row.category, 'distinct': True} for row in ledger.source_rows(db, owner.id, overlap.id)]
        publish(db, owner, overlap, decisions=decisions)
        assert db.query(LedgerEntry).count() == 4
        entry = db.query(LedgerEntry).first()
        invalid = Split(**op(entry.revision, components=[{'category': 'purchase', 'amount_paise': -49999}]))
        with pytest.raises(Exception):
            ledger.split(db, owner.id, entry.id, invalid)
        valid = Split(**op(entry.revision, components=[{'category': 'purchase', 'amount_paise': -30000}, {'category': 'fee', 'amount_paise': -20000}]))
        result = ledger.split(db, owner.id, entry.id, valid)
        assert ledger.split(db, owner.id, entry.id, valid) == result
        assert sum(c['amount_paise'] for c in result['components']) == -50000


def test_distinct_stable_references_preserve_repeated_amounts(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        first = imported(db, owner, account)
        publish(db, owner, first)
        # A different reference is independent even with identical date/amount/text.
        later = imported(db, owner, account, load().replace(b'SAL-1', b'SAL-2').replace(b'EXP-1', b'EXP-2'))
        publish(db, owner, later)
        assert db.query(LedgerEntry).filter_by(active=True).count() == 4


def test_cancel_fences_worker_reprocess_generation(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = service.upload(db, owner.id, account.id, load())
        work_id, fence = queue.claim(db, kind='statement')
        result = ledger.cancel(db, owner.id, job.id, Operation(**op(job.revision)))
        with pytest.raises(ValueError):
            service.process_claimed(db, work_id, fence)
        db.refresh(job)
        replay = Operation(**op(job.revision))
        generation = ledger.reprocess(db, owner.id, job.id, replay)
        assert ledger.reprocess(db, owner.id, job.id, replay) == generation
        assert generation['generation'] == 2 and generation['document_id'] == job.document_id
        claimed = queue.claim(db, kind='statement')
        service.process_claimed(db, *claimed)
        next_job = db.get(StatementImport, generation['id'])
        publish(db, owner, next_job)
        assert db.query(LedgerEntry).count() == 2


def test_scanner_failure_and_expiry(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = service.upload(db, owner.id, account.id, load())
        service.process_claimed(db, *queue.claim(db, kind='statement'), scanner_available=False)
        db.refresh(job)
        assert job.state == 'quarantined' and job.error_code == 'scanner_unavailable'
        doc = db.get(StatementDocument, job.document_id)
        doc.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        with pytest.raises(Exception) as exc:
            service.read_document(db, owner.id, doc.id)
        assert exc.value.status_code == 410


def test_statement_api_owner_security_limits_and_revision(client, monkeypatch):
    a, b = auth(client), auth(client, 'foreign@example.com')
    account = client.post('/statement-accounts', headers=a, json={'label': 'Synthetic', 'token': 'SYNTH_A'}).json()
    assert 'id' in account, account
    response = client.post('/statement-accounts/' + account['id'] + '/uploads', headers={**a, 'Content-Type': 'text/csv'}, content=load())
    assert response.status_code == 202, response.text
    job = response.json()
    for suffix in ('', '/rows', '/events'):
        assert client.get('/statement-imports/' + job['id'] + suffix, headers=b).status_code == 404
    for action in ('resume', 'cancel', 'reverse', 'reprocess'):
        assert client.post('/statement-imports/' + job['id'] + '/' + action, headers=b, json=op(0)).status_code == 404
    assert client.get('/statement-documents/' + job['document_id'] + '/content', headers=b).status_code == 404
    assert client.post('/statement-accounts/' + account['id'] + '/uploads', headers={**b, 'Content-Type': 'text/csv'}, content=load()).status_code == 404
    with client.session_factory() as db:
        service.process_claimed(db, *queue.claim(db, kind='statement'))
    assert client.post('/statement-imports/' + job['id'] + '/resume', headers=a, json=op(0)).status_code == 409
    current = client.get('/statement-imports/' + job['id'], headers=a).json()
    rows = client.get('/statement-imports/' + job['id'] + '/rows', headers=a).json()
    invalid = op(current['revision'], decisions=[{'row_id': rows[0]['id'], 'category': 'purchase'}])
    assert client.post('/statement-imports/' + job['id'] + '/resume', headers=a, json=invalid).status_code == 422
    assert client.get('/statement-formats', headers=a).json()['max_pages'] == 0
    monkeypatch.setattr(config, 'STATEMENT_MAX_BYTES', 10)
    assert client.post('/statement-accounts/' + account['id'] + '/uploads', headers={**a, 'Content-Type': 'text/csv'}, content=load()).status_code == 413
