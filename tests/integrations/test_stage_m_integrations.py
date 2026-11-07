"""T504/T508/T509: test-only bank adapter, consent and replay, race and unknown-outcome tests. All fictional."""
import json
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.integrations import service as integ
from backend.integrations.fake_bank import FakeBank
from backend.models.models import IntegrationEvent, IntegrationOperation, StatementImport, StatementRow
from backend.schemas.statements import AccountCreate
from backend.services import statement_service
from tests.test_stage_b import signup


@pytest.fixture(autouse=True)
def synthetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))


def ev(n, day='2025-10-01', amount=-10000, text='Shop'):
    return {'event_id': f'E{n}', 'posting_date': day, 'description': text, 'amount_paise': amount}


def setup(db, name='fictional'):
    owner = signup(db, name)
    account = statement_service.create_account(db, owner.id, AccountCreate(label='Synthetic A', token='SYNTH_A'))
    consent = integ.grant(db, owner.id, 'fake-bank', account.id, ['transactions'])
    return owner, account, consent


def row_count(db, owner):
    return db.query(StatementRow).filter_by(user_id=owner.id).count()


def test_sync_creates_one_reviewable_import_and_events(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        bank = FakeBank([ev(1), ev(2, '2025-10-02', 500000, 'Salary')])
        result = integ.sync(db, owner.id, consent.id, bank)
        assert result['accepted'] == 2 and result['duplicates'] == 0 and result['import']['state'] == 'queued'
        assert db.query(IntegrationEvent).filter_by(user_id=owner.id).count() == 2
        assert db.query(StatementImport).filter_by(user_id=owner.id).count() == 1


def test_replay_and_overlap_never_duplicate(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        first = FakeBank([ev(1), ev(2, '2025-10-02')])
        integ.sync(db, owner.id, consent.id, first)
        again = integ.sync(db, owner.id, consent.id, first)                       # exact replay
        assert again == {'accepted': 0, 'duplicates': 2, 'import': None}
        overlap = FakeBank([ev(2, '2025-10-02'), ev(3, '2025-10-03'), ev(3, '2025-10-03')])   # overlap + in-batch repeat
        result = integ.sync(db, owner.id, consent.id, overlap)
        assert result['accepted'] == 1 and result['duplicates'] == 2
        assert db.query(IntegrationEvent).filter_by(user_id=owner.id).count() == 3
        assert db.query(StatementImport).filter_by(user_id=owner.id).count() == 2


def test_out_of_order_arrival_gives_identical_evidence(db_engine):
    with Session(db_engine) as db:
        a, _, ca = setup(db, 'alpha')
        b, _, cb = setup(db, 'beta')
        rows = [ev(1, '2025-10-01'), ev(2, '2025-10-02'), ev(3, '2025-10-03')]
        ja = integ.sync(db, a.id, ca.id, FakeBank(rows))['import']
        jb = integ.sync(db, b.id, cb.id, FakeBank(list(reversed(rows))))['import']
        from backend.finance.storage import configured_storage
        da = statement_service.read_document(db, a.id, ja['document_id'])
        dbb = statement_service.read_document(db, b.id, jb['document_id'])
        assert da == dbb and da.splitlines()[0].startswith(b'SYNTHETIC-INR-v1,SYNTH_A,2025-10-01,2025-10-03')


def test_revocation_during_fetch_commits_nothing(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        cid = consent.id

        def revoke_midway():
            with Session(db_engine) as other:
                integ.revoke(other, owner.id, cid)
        with pytest.raises(HTTPException) as err:
            integ.sync(db, owner.id, cid, FakeBank([ev(1)], before_return=revoke_midway))
        assert err.value.status_code == 409
        db.rollback()
        assert db.query(IntegrationEvent).filter_by(user_id=owner.id).count() == 0
        assert db.query(StatementImport).filter_by(user_id=owner.id).count() == 0
        with pytest.raises(HTTPException):                                        # revoked consent cannot sync again
            integ.sync(db, owner.id, cid, FakeBank([ev(1)]))


def test_consent_is_owner_scoped_and_validated(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db, 'one')
        other = signup(db, 'two')
        for call in (lambda: integ.sync(db, other.id, consent.id, FakeBank([ev(1)])),
                     lambda: integ.revoke(db, other.id, consent.id),
                     lambda: integ.grant(db, other.id, 'fake-bank', account.id, ['transactions'])):
            with pytest.raises(HTTPException) as err:
                call()
            assert err.value.status_code == 404
        with pytest.raises(HTTPException) as err:
            integ.grant(db, owner.id, 'fake-bank', account.id, ['payments'])
        assert err.value.status_code == 422
        with pytest.raises(HTTPException):
            integ.sync(db, owner.id, consent.id, type('Wrong', (FakeBank,), {'name': 'other-bank'})([ev(1)]))


@pytest.mark.parametrize('bad', [{'amount_paise': 0}, {'amount_paise': 1.5}, {'posting_date': '2999-01-01'},
                                 {'posting_date': 'yesterday'}, {'description': ''}, {'event_id': 'x' * 81}])
def test_invalid_provider_records_commit_nothing(db_engine, bad):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        with pytest.raises(HTTPException) as err:
            integ.sync(db, owner.id, consent.id, FakeBank([ev(1), {**ev(2), **bad}]))
        assert err.value.status_code == 502
        assert db.query(IntegrationEvent).filter_by(user_id=owner.id).count() == 0


def test_formula_text_from_provider_is_neutralised(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        job = integ.sync(db, owner.id, consent.id, FakeBank([ev(1, text='=cmd|calc')]))['import']
        assert b"'=cmd|calc" in statement_service.read_document(db, owner.id, job['document_id'])


def test_fake_bank_refuses_to_exist_outside_sandbox(monkeypatch):
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', False)
    with pytest.raises(RuntimeError):
        FakeBank()


def test_operation_ok_failed_and_idempotent_repeat(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        bank = FakeBank()
        op = integ.submit(db, owner.id, consent.id, 'refresh_request', 'key-0001-aaaa', bank)
        assert op.state == 'submitted' and bank.applied == {op.id: 1}
        again = integ.submit(db, owner.id, consent.id, 'refresh_request', 'key-0001-aaaa', bank)
        assert again.id == op.id and bank.applied == {op.id: 1}
        rejected = integ.submit(db, owner.id, consent.id, 'link_check', 'key-0002-aaaa', FakeBank(submit_mode='reject'))
        assert rejected.state == 'failed'
        with pytest.raises(HTTPException) as err:                                  # same key, different request
            integ.submit(db, owner.id, consent.id, 'link_check', 'key-0001-aaaa', bank)
        assert err.value.status_code == 409


@pytest.mark.parametrize('mode,expected', [('timeout_after_apply', 'confirmed'), ('timeout_before_apply', 'failed')])
def test_timeout_is_reconciled_never_duplicated(db_engine, mode, expected):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        bank = FakeBank(submit_mode=mode)
        op = integ.submit(db, owner.id, consent.id, 'refresh_request', 'key-0003-aaaa', bank)
        assert op.state == 'unknown' and integ.describe_operation(op)['needs_reconciliation']
        # A retry with the same key must not submit again; it asks the provider instead.
        before = dict(bank.applied)
        again = integ.submit(db, owner.id, consent.id, 'refresh_request', 'key-0003-aaaa', bank)
        assert again.id == op.id and again.state == expected and bank.applied == before
        assert db.query(IntegrationOperation).filter_by(user_id=owner.id).count() == 1


def test_still_unknown_stays_unknown_until_definite_answer(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        bank = FakeBank(submit_mode='timeout_after_apply', status_script=['unknown', 'pending', 'confirmed'])
        op = integ.submit(db, owner.id, consent.id, 'refresh_request', 'key-0004-aaaa', bank)
        assert integ.reconcile(db, owner.id, op.id, bank).state == 'unknown'
        assert integ.reconcile(db, owner.id, op.id, bank).state == 'unknown'
        assert integ.reconcile(db, owner.id, op.id, bank).state == 'confirmed'
        assert integ.reconcile(db, owner.id, op.id, FakeBank(status_script=['failed'])).state == 'confirmed'   # final is final


def test_operation_needs_active_consent_and_owner(db_engine):
    with Session(db_engine) as db:
        owner, account, consent = setup(db)
        other = signup(db, 'intruder')
        with pytest.raises(HTTPException) as err:
            integ.submit(db, other.id, consent.id, 'link_check', 'key-0005-aaaa', FakeBank())
        assert err.value.status_code == 404
        integ.revoke(db, owner.id, consent.id)
        with pytest.raises(HTTPException) as err:
            integ.submit(db, owner.id, consent.id, 'link_check', 'key-0006-aaaa', FakeBank())
        assert err.value.status_code == 409
        for bad in ('short', 'has space in key!', 'x' * 65):
            with pytest.raises(HTTPException):
                integ.submit(db, owner.id, consent.id, 'link_check', bad, FakeBank())
