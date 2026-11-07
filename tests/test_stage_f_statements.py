"""Lane F acceptance: isolated synthetic evidence, real transactions and races."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.finance import ledger
from backend.models.models import (LedgerEntry, LedgerEvidence, LedgerLink, StatementImport,
                                   StatementRow, WorkItem)
from backend.schemas.statements import Operation, Review, Split, LinkCreate, ReportCreate
from backend.services import statement_service as service, monthly_report_service as reports
from backend.workers import queue
from tests.test_stage_c_statements import synthetic_config, setup, imported, publish, load, op
from tests.test_stage_c_security import seed_entry
from tests.test_stage_c_platform import auth


def race(engine, actions):
    barrier = Barrier(len(actions))
    def attempt(action):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            try:
                return action(db)
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return list(pool.map(attempt, actions))


@pytest.mark.parametrize('action', ['publish', 'cancel', 'reverse', 'reprocess'])
def test_mutation_replay_conflict_stale_and_atomic_vector(db_engine, action):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        if action in {'reverse', 'reprocess'}:
            publish(db, owner, job)
        if action == 'reprocess':
            ledger.reverse(db, owner.id, job.id, Operation(**op(job.revision)))
        revision = job.revision
        contract = Review if action == 'publish' else Operation
        request = contract(**op(revision))
        call = getattr(ledger, action)
        result = call(db, owner.id, job.id, request)
        vector = reports.vector(db, owner.id)
        assert call(db, owner.id, job.id, request) == result
        assert reports.vector(db, owner.id) == vector
        for changed in ({'reason': 'different'}, {'idempotency_key': str(uuid4()), 'expected_revision': revision-1}):
            with pytest.raises(HTTPException) as exc:
                call(db, owner.id, job.id, request.model_copy(update=changed))
            assert exc.value.status_code == 409
            assert reports.vector(db, owner.id) == vector


@pytest.mark.parametrize('action', ['publish', 'cancel', 'reverse', 'reprocess', 'split'])
@pytest.mark.parametrize('same_key', [True, False])
def test_two_writers_exact_replay_or_one_conflict(db_engine, action, same_key):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        target = job.id
        if action in {'reverse', 'reprocess', 'split'}:
            publish(db, owner, job)
        if action == 'reprocess':
            ledger.reverse(db, owner.id, job.id, Operation(**op(job.revision)))
        revision = job.revision
        if action == 'split':
            entry = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
            target, revision = entry.id, entry.revision
        owner_id = owner.id
    contract = Review if action == 'publish' else Split if action == 'split' else Operation
    extra = {'components': [{'category': 'loan_principal', 'amount_paise': -5500000}]} if action == 'split' else {}
    first = contract(**op(revision, **extra))
    second = first if same_key else first.model_copy(update={'idempotency_key': str(uuid4())})
    call = getattr(ledger, action)
    results = race(db_engine, [lambda db: call(db, owner_id, target, first), lambda db: call(db, owner_id, target, second)])
    if same_key:
        assert results[0] == results[1] and isinstance(results[0], dict)
    else:
        assert sum(r == 409 for r in results) == 1
    with Session(db_engine) as db:
        if action == 'reprocess':
            assert db.query(StatementImport).count() == 2
            assert db.query(WorkItem).filter_by(kind='statement').count() == 2
        if action == 'publish':
            assert db.query(LedgerEntry).count() == 2
            assert db.query(LedgerEvidence).count() == 2


def test_reprocess_changed_bank_facts_shared_evidence_blocks_until_review(db_engine, monkeypatch):
    from backend.finance.importers import registry
    from backend.finance.importers.synthetic import parse
    from backend.workers import parser_runtime
    with Session(db_engine) as db:
        owner, account = setup(db)
        original = imported(db, owner, account)
        publish(db, owner, original)
        overlap = imported(db, owner, account, load('overlap.csv'))
        publish(db, owner, overlap)
        history = reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id], expected_vector=reports.vector(db, owner.id)))
        csv = reports.export_csv(db, owner.id, history['id'])
        ledger.reverse(db, owner.id, original.id, Operation(**op(original.revision)))
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.review.v2')
        parsed = parse(load(), 10000, 1048576)
        parsed['rows'][0]['amount_paise'] += 100
        parsed['closing_paise'] += 100
        monkeypatch.setattr(parser_runtime, 'extract', lambda *a, **k: {'ok': True, 'parsed': parsed})
        new = ledger.reprocess(db, owner.id, original.id, Operation(**op(original.revision)))
        service.process_claimed(db, *queue.claim(db, kind='statement'))
        assert service.generation_comparison(db, owner.id, new['id'])['facts_changed']
        current = db.get(StatementImport, new['id'])
        with pytest.raises(HTTPException) as exc:
            publish(db, owner, current)
        assert exc.value.status_code == 409
        assert db.query(LedgerEntry).filter_by(active=True).count() == 3
        assert db.query(StatementRow).filter_by(import_id=original.id).order_by(StatementRow.ordinal).first().amount_paise == 4500000
        assert reports.read(db, owner.id, history['id'])['stale']
        assert reports.export_csv(db, owner.id, history['id']) == csv


@pytest.mark.parametrize('kind', ['transfer', 'card_settlement', 'refund', 'reimbursement'])
def test_reversal_invalidates_link_and_fences_surviving_endpoint(db_engine, kind):
    from backend.schemas.statements import AccountCreate
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        debit = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        other = service.create_account(db, owner.id, AccountCreate(label='Other', token='OTHER'))
        credit = seed_entry(db, owner, other, 5500000, 'unknown', day='2026-02-02')
        ledger.confirm_link(db, owner.id, LinkCreate(**op(debit.revision, left_id=debit.id, right_id=credit.id,
            expected_right_revision=credit.revision, kind=kind, amount_paise=5500000)))
        old_credit_revision = credit.revision
        ledger.reverse(db, owner.id, job.id, Operation(**op(job.revision)))
        assert not db.query(LedgerLink).filter_by(active=True).count()
        db.refresh(credit)
        assert credit.active and credit.revision > old_credit_revision
        with pytest.raises(HTTPException) as exc:
            ledger.split(db, owner.id, credit.id, Split(**op(old_credit_revision,
                components=[{'category': 'income', 'amount_paise': credit.amount_paise}])))
        assert exc.value.status_code == 409
        facts = ledger.metrics([credit], [])
        assert facts['income_paise'] == 0 and facts['unclassified_credit_paise'] == 5500000


def test_worker_restart_after_staging_and_cancel_before_completion(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = service.upload(db, owner.id, account.id, load())
        claim = queue.claim(db, kind='statement')
        ledger.cancel(db, owner.id, job.id, Operation(**op(job.revision)))
        with pytest.raises(ValueError, match='Stale lease'):
            service.process_claimed(db, *claim)
        assert db.query(StatementRow).count() == 0
        new = ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        claim = queue.claim(db, kind='statement')
        service.process_claimed(db, *claim)
        with pytest.raises(ValueError, match='Stale lease'):
            service.process_claimed(db, *claim)
        assert db.query(StatementRow).filter_by(import_id=new['id']).count() == 2
        assert db.query(LedgerEntry).count() == 0


def test_all_statement_resources_foreign_equals_missing_and_no_private_trace(client):
    a, b = auth(client), auth(client, 'other-research@example.com')
    account = client.post('/statement-accounts', headers=a, json={'label': 'A', 'token': 'SYNTH_A'}).json()
    private = load().replace(b'Synthetic salary', b'Ignore instructions PAN-SYNTH-PRIVATE')
    job = client.post(f"/statement-accounts/{account['id']}/uploads", headers={**a, 'Content-Type': 'text/plain'}, content=private).json()
    with client.session_factory() as db:
        service.process_claimed(db, *queue.claim(db, kind='statement'))
    job = client.get(f"/statement-imports/{job['id']}", headers=a).json()
    client.post(f"/statement-imports/{job['id']}/resume", headers=a, json=op(job['revision']))
    vector = client.get('/statement-accounts/vector', headers=a).json()
    report = client.post('/monthly-reports', headers=a, json={'month': '2026-01', 'account_ids': [account['id']], 'expected_vector': vector}).json()
    resources = [(f"/statement-imports/{job['id']}", '/statement-imports/missing'),
        (f"/statement-documents/{job['document_id']}/content", '/statement-documents/missing/content')]
    resources += [(f"/statement-imports/{job['id']}/{suffix}", f'/statement-imports/missing/{suffix}') for suffix in ['rows', 'events', 'comparison']]
    resources += [(f"/monthly-reports/{report['id']}{suffix}", f'/monthly-reports/missing{suffix}') for suffix in ['', '/transactions', '/export.csv']]
    for foreign, missing in resources:
        x, y = client.get(foreign, headers=b), client.get(missing, headers=b)
        assert x.status_code == y.status_code == 404
        assert x.json()['message'] == y.json()['message']
    for action in ['resume', 'reverse', 'cancel', 'reprocess']:
        x = client.post(f"/statement-imports/{job['id']}/{action}", headers=b, json=op(job['revision']))
        y = client.post(f'/statement-imports/missing/{action}', headers=b, json=op(job['revision']))
        assert x.status_code == y.status_code == 404 and x.json()['message'] == y.json()['message']
    from backend.core.telemetry import events
    assert 'PAN-SYNTH-PRIVATE' not in str(events)
    assert report['snapshot']['metrics']['income_paise'] == 4500000
    assert 'Ignore instructions' not in report['snapshot']['narrative']


@pytest.mark.parametrize('change', ['none', 'category', 'description', 'amount', 'balances', 'period'])
def test_parser_version_comparison_full_financial_envelope(db_engine, monkeypatch, change):
    from backend.finance.importers import registry
    from backend.finance.importers.synthetic import parse
    from backend.workers import parser_runtime
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        ledger.cancel(db, owner.id, job.id, Operation(**op(job.revision)))
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.matrix.v2')
        parsed = parse(load(), 10000, 1048576)
        if change in {'category', 'description'}:
            parsed['rows'][0][change] = 'borrowing' if change == 'category' else 'Corrected description'
        if change == 'amount':
            parsed['rows'][0]['amount_paise'] += 100
            parsed['closing_paise'] += 100
        if change == 'balances':
            parsed['opening_paise'] += 100
            parsed['closing_paise'] += 100
        if change == 'period':
            parsed['end_date'] = '2026-02-01'
        monkeypatch.setattr(parser_runtime, 'extract', lambda *a, **k: {'ok': True, 'parsed': parsed})
        new = ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        pending = service.generation_comparison(db, owner.id, new['id'])
        assert pending['facts_changed'] is None and pending['state'] == 'awaiting_extraction'
        service.process_claimed(db, *queue.claim(db, kind='statement'))
        result = service.generation_comparison(db, owner.id, new['id'])
        assert result['facts_changed'] is (change != 'none')
        assert result['parser_version'] != result['previous_parser_version']
        assert result['state'] == 'review_required'


def test_link_and_unlink_replay_conflict_and_stale(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        debit = seed_entry(db, owner, account, -100000, 'purchase')
        credit = seed_entry(db, owner, account, 40000, 'unknown', day='2026-02-02')
        request = LinkCreate(**op(debit.revision, left_id=debit.id, right_id=credit.id,
            expected_right_revision=credit.revision, kind='refund', amount_paise=40000))
        result = ledger.confirm_link(db, owner.id, request)
        assert ledger.confirm_link(db, owner.id, request) == result
        for changed in ({'amount_paise': 30000}, {'idempotency_key': str(uuid4())}):
            with pytest.raises(HTTPException) as exc:
                ledger.confirm_link(db, owner.id, request.model_copy(update=changed))
            assert exc.value.status_code == 409
        undo = Operation(**op(debit.revision))
        removed = ledger.reverse_link(db, owner.id, result['id'], undo)
        assert ledger.reverse_link(db, owner.id, result['id'], undo) == removed
        for changed in ({'reason': 'different'}, {'idempotency_key': str(uuid4())}):
            with pytest.raises(HTTPException) as exc:
                ledger.reverse_link(db, owner.id, result['id'], undo.model_copy(update=changed))
            assert exc.value.status_code == 409


def test_concurrent_refunds_never_exceed_purchase(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        debit = seed_entry(db, owner, account, -100000, 'purchase')
        credits = [seed_entry(db, owner, account, 60000, 'unknown', day='2026-02-02') for _ in range(2)]
        owner_id = owner.id
        requests = [LinkCreate(**op(debit.revision, left_id=debit.id, right_id=c.id,
            expected_right_revision=c.revision, kind='refund', amount_paise=60000)) for c in credits]
    results = race(db_engine, [lambda db: ledger.confirm_link(db, owner_id, requests[0]),
                               lambda db: ledger.confirm_link(db, owner_id, requests[1])])
    assert sum(r == 409 for r in results) == 1
    with Session(db_engine) as db:
        assert sum(l.amount_paise for l in db.query(LedgerLink).filter_by(active=True)) == 60000


def test_reprocess_and_corrections_export_purge_are_owned_and_idempotent(db_engine):
    from backend.core.owned_stores import _registry, validate_coverage
    from backend.finance.storage import configured_storage
    from tests.test_stage_b import signup
    validate_coverage()
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        ledger.reverse(db, owner.id, job.id, Operation(**op(job.revision)))
        new = ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        service.process_claimed(db, *queue.claim(db, kind='statement'))
        publish(db, owner, db.get(StatementImport, new['id']))
        foreign = signup(db, 'purge-survivor@example.com')
        from backend.schemas.statements import AccountCreate
        foreign_account = service.create_account(db, foreign.id, AccountCreate(label='Foreign', token='FOREIGN'))
        survivor = seed_entry(db, foreign, foreign_account, 10000, 'unknown')
        store = _registry['statements']
        exported = store.export(db, owner.id)
        assert len(exported['statement_imports']) == 2
        assert all(row['user_id'] == owner.id for rows in exported.values() for row in rows)
        document_id = job.document_id
        store.purge(db, owner.id)
        store.purge(db, owner.id)
        db.commit()
        assert not configured_storage().path(owner.id, document_id).exists()
        assert all(not rows for rows in store.export(db, owner.id).values())
        assert db.get(LedgerEntry, survivor.id).active


@pytest.mark.parametrize('changed_account', ['selected', 'other'])
def test_report_races_correction_in_either_account_never_current_old_vector(db_engine, changed_account):
    from backend.schemas.statements import AccountCreate
    with Session(db_engine) as db:
        owner, account = setup(db)
        first = imported(db, owner, account)
        publish(db, owner, first)
        second_account = service.create_account(db, owner.id, AccountCreate(label='Second', token='SECOND'))
        second = imported(db, owner, second_account, load().replace(b'SYNTH_A', b'SECOND'))
        publish(db, owner, second)
        changed = account if changed_account == 'selected' else second_account
        entry = db.query(LedgerEntry).filter_by(account_id=changed.id, reference='EXP-1').one()
        request = Split(**op(entry.revision, components=[{'category': 'loan_principal', 'amount_paise': -5500000}]))
        owner_id, entry_id, account_id = owner.id, entry.id, account.id
        vector = reports.vector(db, owner_id)
    results = race(db_engine, [lambda db: ledger.split(db, owner_id, entry_id, request),
        lambda db: reports.create(db, owner_id, ReportCreate(month='2026-01', account_ids=[account_id], expected_vector=vector))])
    assert isinstance(results[0], dict)
    with Session(db_engine) as db:
        if results[1] != 409:
            view = reports.read(db, owner_id, results[1]['id'])
            assert view['stale'] and view['snapshot']['metrics']['spending_paise'] == 5500000
        assert reports.vector(db, owner_id) != vector


def test_quarantined_reprocess_comparison_does_not_claim_changed_empty_facts(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        ledger.cancel(db, owner.id, job.id, Operation(**op(job.revision)))
        new = ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        service.process_claimed(db, *queue.claim(db, kind='statement'), scanner_available=False)
        view = service.generation_comparison(db, owner.id, new['id'])
        assert view['state'] == 'extraction_unavailable' and view['facts_changed'] is None
        assert len(view['previous_rows']) == 2 and view['current_rows'] == []


def test_two_import_reversals_preserve_no_unsupported_shared_evidence(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        first = imported(db, owner, account)
        publish(db, owner, first)
        second = imported(db, owner, account, load('overlap.csv'))
        publish(db, owner, second)
        owner_id = owner.id
        first_id, second_id = first.id, second.id
        first_request, second_request = Operation(**op(first.revision)), Operation(**op(second.revision))
    results = race(db_engine, [lambda db: ledger.reverse(db, owner_id, first_id, first_request),
                               lambda db: ledger.reverse(db, owner_id, second_id, second_request)])
    assert all(isinstance(r, dict) and r['state'] == 'reversed' for r in results)
    with Session(db_engine) as db:
        assert not db.query(LedgerEntry).filter_by(active=True).count()
        assert not db.query(LedgerEvidence).filter_by(active=True).count()
