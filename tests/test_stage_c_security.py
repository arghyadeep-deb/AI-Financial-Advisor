import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import subprocess
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.finance.storage import LocalEncryptedStorage, configured_storage
from backend.finance.importers.synthetic import parse, ParseError
from backend.workers.parser_runtime import extract
from backend.models.models import LedgerEntry, StatementImport, StatementDocument, LedgerLink, utcnow
from backend.schemas.statements import Operation, Review, LinkCreate, ReportCreate
from backend.finance import ledger
from backend.services import monthly_report_service as reports
from tests.test_stage_c_statements import synthetic_config, setup, load, imported, publish, op


def test_private_storage_rotation_tamper_and_owner(tmp_path):
    old, new = Fernet.generate_key(), Fernet.generate_key()
    identity = str(uuid4())
    before = LocalEncryptedStorage(tmp_path, {'old': old}, 'old')
    before.put(1, identity, b'SYNTHETIC PRIVATE CONTENT')
    assert b'SYNTHETIC PRIVATE CONTENT' not in before.path(1, identity).read_bytes()
    with pytest.raises(FileNotFoundError): before.get(2, identity)
    with pytest.raises(ValueError): before.get(1, '../outside')
    rotation = LocalEncryptedStorage(tmp_path, {'old': old, 'new': new}, 'new')
    assert rotation.get(1, identity) == b'SYNTHETIC PRIVATE CONTENT'
    retired = LocalEncryptedStorage(tmp_path, {'new': new}, 'new')
    with pytest.raises(ValueError): retired.get(1, identity)
    rotation.rotate(1, identity)
    assert retired.get(1, identity) == b'SYNTHETIC PRIVATE CONTENT'
    path = retired.path(1, identity)
    path.write_bytes(path.read_bytes()[:-5] + b'xxxxx')
    with pytest.raises(ValueError): retired.get(1, identity)


@pytest.mark.parametrize('content,error', [(b'%PDF-1.7 synthetic', 'unsupported_pdf'),
    (b'EICAR synthetic test', 'quarantined_scan'), (b'\0synthetic', 'quarantined_scan'),
    (load().replace(b'45000.00', b'45000.001'), 'invalid_statement'),
    (load().replace(b'2026-01-02', b'02/01/2026'), 'invalid_date'),
    (load().replace(b'SAL-1', b'EXP-1'), 'duplicate_reference')])
def test_bounded_parser_rejection(content, error):
    result = extract(content)
    assert not result['ok'] and result['error_code'] == error


def test_parser_row_byte_timeout_and_scanner_caps(monkeypatch):
    with pytest.raises(ParseError, match='row_limit'): parse(load(), 1, len(load()))
    with pytest.raises(ParseError, match='file_too_large'): parse(load(), 10, 5)
    assert extract(load(), scanner_available=False)['error_code'] == 'scanner_unavailable'
    def timeout(*args, **kwargs):
        assert not any('KEY' in key for key in kwargs['env'])
        raise subprocess.TimeoutExpired('synthetic', 1)
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert extract(load())['error_code'] == 'parser_timeout'


def test_source_retention_and_orphan_cleanup(db_engine, tmp_path):
    from backend.finance.retention import sweep
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        storage = configured_storage()
        doc = db.get(StatementDocument, job.document_id)
        path = storage.path(owner.id, doc.storage_key)
        orphan = str(uuid4())
        storage.put(owner.id, orphan, b'SYNTHETIC ORPHAN')
        orphan_path = storage.path(owner.id, orphan)
        os.utime(orphan_path, (1, 1))
        assert sweep(db)['orphan_objects'] == 1
        assert path.exists()
        doc.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert sweep(db)['expired_sources'] == 1
        assert not path.exists()


def seed_entry(db, owner, account, amount, category, day='2026-01-05'):
    entry = LedgerEntry(id=str(uuid4()), user_id=owner.id, account_id=account.id,
        posting_date=day, amount_paise=amount, description='Synthetic fact',
        components=[{'category': category, 'amount_paise': amount}])
    db.add(entry)
    db.commit()
    return entry


def test_confirmed_links_partial_refunds_and_one_sided_scope(db_engine):
    from backend.services.statement_service import create_account
    from backend.schemas.statements import AccountCreate
    with Session(db_engine) as db:
        owner, account = setup(db)
        second = create_account(db, owner.id, AccountCreate(label='Synthetic B', token='SYNTH_B'))
        debit = seed_entry(db, owner, account, -500000, 'transfer')
        credit = seed_entry(db, owner, second, 500000, 'unknown')
        assert not ledger.metrics([debit])['classification_complete']
        link = ledger.confirm_link(db, owner.id, LinkCreate(**op(debit.revision,
            left_id=debit.id, right_id=credit.id, expected_right_revision=credit.revision, kind='transfer', amount_paise=500000)))
        links = db.query(LedgerLink).filter_by(active=True).all()
        facts = ledger.metrics([debit, credit], links)
        assert facts['income_paise'] == facts['spending_paise'] == facts['cash_movement_paise'] == 0
        purchase = seed_entry(db, owner, account, -100000, 'purchase')
        refund = seed_entry(db, owner, account, 40000, 'unknown', day='2026-02-01')
        request = LinkCreate(**op(purchase.revision, left_id=purchase.id, right_id=refund.id,
            expected_right_revision=refund.revision, kind='refund', amount_paise=40000))
        result = ledger.confirm_link(db, owner.id, request)
        assert ledger.confirm_link(db, owner.id, request) == result
        links = db.query(LedgerLink).filter_by(active=True).all()
        assert ledger.metrics([purchase], links)['spending_paise'] == 100000
        feb = ledger.metrics([refund], links)
        assert feb['spending_paise'] == -40000 and feb['income_paise'] == 0 and feb['cash_movement_paise'] == 40000
        assert ledger.metrics([purchase, refund], links)['spending_paise'] == 60000
        db.refresh(purchase)
        with pytest.raises(Exception) as exc:
            ledger.confirm_link(db, owner.id, LinkCreate(**op(purchase.revision,
                left_id=purchase.id, right_id=refund.id, expected_right_revision=refund.revision, kind='refund', amount_paise=1)))
        assert exc.value.status_code == 422
        db.refresh(purchase)
        ledger.reverse_link(db, owner.id, result['id'], Operation(**op(purchase.revision)))
        assert ledger.metrics([refund], db.query(LedgerLink).all())['unclassified_credit_paise'] == 40000


@pytest.mark.parametrize('amount,category,metric,expected', [
    (10000000, 'borrowing', 'borrowing_paise', 10000000),
    (-500000, 'investment', 'investment_paise', 500000),
    (600000, 'disposal', 'disposal_paise', 600000),
    (-200000, 'withdrawal', 'unclassified_debit_paise', 200000),
    (4500000, 'unknown', 'unclassified_credit_paise', 4500000)])
def test_FIN04_06_07_11_16_never_infer_income(amount, category, metric, expected):
    entry = SimpleNamespace(id='synthetic', active=True, amount_paise=amount,
        components=[{'amount_paise': amount, 'category': category}])
    facts = ledger.metrics([entry])
    assert facts[metric] == expected and facts['income_paise'] == facts['spending_paise'] == 0
    assert facts['eligible_contribution_paise'] is None


def test_FIN05_emi_split_interest_and_principal():
    entry = SimpleNamespace(id='emi', active=True, amount_paise=-1000000,
        components=[{'amount_paise': -800000, 'category': 'loan_principal'}, {'amount_paise': -200000, 'category': 'interest'}])
    facts = ledger.metrics([entry])
    assert facts['principal_paise'] == 800000 and facts['spending_paise'] == 200000
    assert facts['cash_movement_paise'] == -1000000


def test_concurrent_publish_one_business_commit(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        owner_id, job_id, revision = owner.id, job.id, job.revision
    barrier = Barrier(2)
    def attempt(key):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return ledger.publish(db, owner_id, job_id, Review(**op(revision, key)))['state']
            except Exception as exc:
                return getattr(exc, 'status_code', type(exc).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ['concurrent-1', 'concurrent-2']))
    assert sorted(outcomes, key=str) == [409, 'completed']
    with Session(db_engine) as db:
        assert db.query(LedgerEntry).count() == 2
        assert db.get(StatementImport, job_id).business_commit_id


def test_other_account_revision_invalidates_report_and_stale_publish(db_engine):
    from backend.services.statement_service import create_account
    from backend.schemas.statements import AccountCreate
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        expected = reports.vector(db, owner.id)
        first = reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id], expected_vector=expected))
        create_account(db, owner.id, AccountCreate(label='Synthetic B', token='SYNTH_B'))
        assert reports.read(db, owner.id, first['id'])['stale']
        with pytest.raises(Exception) as exc:
            reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id], expected_vector=expected))
        assert exc.value.status_code == 409


def test_private_export_expiry_and_wrong_owner(client):
    from tests.test_stage_c_platform import auth
    from backend.models.models import PrivacyRequest
    from backend.services.privacy.exports import expire
    a, b = auth(client), auth(client, 'private-other@example.com')
    created = client.post('/privacy/exports', headers=a, json={'password': 'Fictional-safe-pass-987'})
    assert created.status_code == 201, created.text
    identity = created.json()['id']
    assert client.get('/privacy/requests/' + identity, headers=b).status_code == 404
    assert client.get('/privacy/exports/' + identity + '/download', headers=b).status_code == 404
    downloaded = client.get('/privacy/exports/' + identity + '/download', headers=a)
    assert downloaded.status_code == 200 and downloaded.headers['cache-control'] == 'no-store'
    assert 'hashed_password' not in downloaded.text and 'token_hash' not in downloaded.text
    with client.session_factory() as db:
        row = db.get(PrivacyRequest, identity)
        path = configured_storage().path(row.user_id, row.storage_key)
        assert path.exists() and b'account' not in path.read_bytes()
        row.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert expire(db) == 1 and not path.exists()
    assert client.get('/privacy/requests/' + identity, headers=a).json()['state'] == 'expired'
    assert client.get('/privacy/exports/' + identity + '/download', headers=a).status_code == 410


def test_graph_worker_restart_uses_business_checkpoint(db_engine):
    from backend.services.statement_service import upload
    from backend.workers.statements import run_once
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = upload(db, owner.id, account.id, load())
        job_id, owner_id = job.id, owner.id
    with Session(db_engine) as restarted:
        assert run_once(restarted)
        staged = restarted.get(StatementImport, job_id)
        assert staged.state == 'needs_review' and staged.checkpoint == 'reconciled'
        request = Review(**op(staged.revision))
        result = ledger.publish(restarted, owner_id, job_id, request)
    with Session(db_engine) as restarted:
        assert ledger.publish(restarted, owner_id, job_id, request) == result
        assert restarted.query(LedgerEntry).count() == 2


def test_restore_drill_replays_suppression_for_ledger_sources_and_exports(db_engine, tmp_path, monkeypatch):
    import shutil
    import time
    from sqlalchemy import create_engine
    from backend.services.privacy.lifecycle import SuppressionJournal, delete_owned
    from backend.services.privacy import exports
    from backend.core.owned_stores import validate_coverage
    from deployment.recovery import backup, restore
    journal = SuppressionJournal(tmp_path / 'independent-journal.db')
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        survivor = __import__('tests.test_stage_b', fromlist=['signup']).signup(db, 'survivor')
        exported = exports.create(db, owner, 'Safe-fictional-pass-987')
        owner_id, survivor_id, document_id = owner.id, survivor.id, job.document_id
        validate_coverage()
        backup(db_engine.url.database, tmp_path / 'backup.db')
        shutil.copytree(config.PRIVATE_STORAGE_ROOT, tmp_path / 'encrypted-backup')
        assert delete_owned(db, owner, 'Safe-fictional-pass-987', journal)['status'] == 'live_complete'
        assert not configured_storage().path(owner_id, document_id).exists()
        assert db.query(LedgerEntry).filter_by(user_id=owner_id).count() == 0
    # Simulate restoration of encrypted objects together with the pre-delete DB.
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'encrypted-backup'))
    started = time.monotonic()
    restore(tmp_path / 'backup.db', tmp_path / 'restored.db', journal)
    elapsed = time.monotonic() - started
    restored_engine = create_engine('sqlite:///' + (tmp_path / 'restored.db').as_posix())
    with Session(restored_engine) as db:
        from backend.models.models import User, PrivacyRequest
        assert not db.get(User, owner_id).is_active and db.get(User, survivor_id).is_active
        assert db.query(LedgerEntry).filter_by(user_id=owner_id).count() == 0
        assert db.query(PrivacyRequest).filter_by(user_id=owner_id).count() == 0
        assert not configured_storage().path(owner_id, document_id).exists()
    restored_engine.dispose()
    print(f'Synthetic restore and suppression replay: {elapsed:.3f}s; deleted ledger/export/source absent; survivor active')


def test_partial_shared_evidence_survives_reverse_and_invalidates_refund(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        first = imported(db, owner, account)
        publish(db, owner, first)
        # A has X,Y. B independently corroborates only X.
        corroboration = (b'SYNTHETIC-INR-v1,SYNTH_A,2026-01-01,2026-01-31,0,45000\n'
            b'date,description,reference,signed_rupees,category\n'
            b'2026-01-02,Synthetic salary,SAL-1,45000,income\n')
        second = imported(db, owner, account, corroboration)
        publish(db, owner, second)
        purchase = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        refund = seed_entry(db, owner, account, 40000, 'unknown', '2026-02-02')
        ledger.confirm_link(db, owner.id, LinkCreate(**op(purchase.revision,
            left_id=purchase.id, right_id=refund.id, expected_right_revision=refund.revision, kind='refund', amount_paise=40000)))
        db.refresh(first)
        ledger.reverse(db, owner.id, first.id, Operation(**op(first.revision)))
        assert db.query(LedgerEntry).filter_by(active=True, reference='SAL-1').count() == 1
        assert not db.get(LedgerEntry, purchase.id).active
        assert db.query(LedgerLink).filter_by(active=True).count() == 0
        assert ledger.metrics([refund], db.query(LedgerLink).all())['income_paise'] == 0


def test_FIN03_card_purchase_and_settlement_not_double_spent():
    purchase = SimpleNamespace(id='card-purchase', active=True, amount_paise=-200000,
        components=[{'amount_paise': -200000, 'category': 'purchase'}])
    settlement = SimpleNamespace(id='bank-settlement', active=True, amount_paise=-200000,
        components=[{'amount_paise': -200000, 'category': 'card_settlement'}])
    facts = ledger.metrics([purchase, settlement])
    assert facts['spending_paise'] == 200000
    assert facts['unclassified_debit_paise'] == 200000 and not facts['classification_complete']


def test_metadata_exporter_outage_has_no_ledger_effect(db_engine):
    from backend.observability.health import emit, snapshot
    with Session(db_engine) as db:
        owner, account = setup(db)
        mismatch = imported(db, owner, account, load('mismatch.csv'))
        assert snapshot(db)['alerts'][0]['code'] == 'reconciliation_blocked'
        def fail(_):
            raise RuntimeError('synthetic exporter outage')
        assert emit(db, fail) == {'exporter': 'unavailable'}
        db.refresh(mismatch)
        assert mismatch.state == 'needs_review' and db.query(LedgerEntry).count() == 0


def test_cancel_races_publication_one_final_result(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        owner_id, job_id, revision = owner.id, job.id, job.revision
    barrier = Barrier(2)
    def attempt(action):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                payload = Review(**op(revision)) if action == 'publish' else Operation(**op(revision))
                return getattr(ledger, action)(db, owner_id, job_id, payload)['state']
            except Exception as exc:
                return getattr(exc, 'status_code', type(exc).__name__)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ['publish', 'cancel']))
    assert 409 in outcomes and len(set(outcomes) & {'completed', 'cancelled'}) == 1
    with Session(db_engine) as db:
        job = db.get(StatementImport, job_id)
        assert db.query(LedgerEntry).count() == (2 if job.state == 'completed' else 0)
