"""Synthetic lane J acceptance; independent paise expectations, providers disabled."""
from uuid import uuid4
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.models.models import Base, HouseholdRevision
from backend.schemas import household as h
from backend.services import household_service as service
from tests.test_stage_c_statements import setup, synthetic_config


@pytest.fixture(autouse=True)
def households(monkeypatch, synthetic_config):
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', True)
    monkeypatch.setattr(config, 'SYNTHETIC_MANUAL_CASH_ENABLED', True)


def observation(ref='property', value=8000000, share=10000, kind='asset', **extra):
    return dict(reference=ref, value_paise=value, share_bps=share, kind=kind, valued_on='2026-01-31', **extra)


def book(items, revision=0, key=None):
    return h.NetWorthWrite(expected_revision=revision, idempotency_key=key or str(uuid4()),
                           reason='Synthetic acceptance', data={'observations': items})


def test_T1101_duplicate_partial_shares_money_and_history(db_engine):
    from fastapi import HTTPException
    with Session(db_engine) as db:
        user, _ = setup(db)
        property = observation(share=5000)
        payload = book([property, property, observation('cash', 2000000), observation('loan', 3000000, kind='liability')])
        original = service.write(db, user.id, 'networth', payload)
        assert service.write(db, user.id, 'networth', payload) == original
        snapshot = service.consolidate([original['data']])
        assert (snapshot['assets_paise'], snapshot['liabilities_paise'], snapshot['net_worth_paise']) == (6000000, 3000000, 3000000)
        assert snapshot['status'] == 'partial'
        service.write(db, user.id, 'networth', book([observation()], 1))
        assert service.latest(db, user.id, 'networth', 1).data == original['data']
        with pytest.raises(HTTPException) as exc:
            service.write(db, user.id, 'networth', book([], 1))
        assert exc.value.status_code == 409
        with pytest.raises(Exception, match='immutable'):
            db.execute(text('UPDATE household_revisions SET revision=99'))
        db.rollback()


@pytest.mark.parametrize('item', [observation(value=True), observation(value=-1), observation(share=10001),
    observation(value=1, share=5000), observation(currency='USD'), observation(projected=True),
    {**observation(), 'valued_on': '2099-01-01'}])
def test_T1101_invalid(item):
    with pytest.raises(ValueError):
        book([item])


def test_T1101_migration_registry_recovery(db_engine):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.owned_stores import validate_coverage, _registry
    validate_coverage()
    info = inspect(db_engine)
    table = Base.metadata.tables['household_revisions']
    assert set(table.columns.keys()) == {c['name'] for c in info.get_columns(table.name)}
    assert {tuple(c.columns.keys()) for c in table.constraints if c.__class__.__name__ == 'UniqueConstraint'} == {
        tuple(c['column_names']) for c in info.get_unique_constraints(table.name)}
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0141')
    command.upgrade(cfg, 'head')
    with Session(db_engine) as db:
        user, _ = setup(db)
        service.write(db, user.id, 'networth', book([observation()]))
        with pytest.raises(RuntimeError, match='Household evidence'):
            command.downgrade(cfg, '0141')
        assert _registry['household_books'].export(db, user.id)['household_revisions'][0]['data']['observations']
        _registry['household_books'].purge(db, user.id)
        db.commit()
        assert db.query(HouseholdRevision).count() == 0


def test_T1101_gate_and_private_api(client, monkeypatch):
    from tests.test_stage_c_platform import auth
    a = auth(client, 'house-a@example.com')
    b = auth(client, 'house-b@example.com')
    assert client.post('/networth', headers=a, json=book([observation()]).model_dump(mode='json')).status_code == 200
    assert client.get('/networth', headers=a).json()['snapshot']['net_worth_paise'] == 8000000
    assert client.get('/networth', headers=b).status_code == 404
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', False)
    assert client.get('/networth', headers=a).status_code == 404


def sharing(db):
    from tests.test_stage_b import signup
    a = signup(db, 'share-a@example.com')
    b = signup(db, 'share-b@example.com')
    c = signup(db, 'share-c@example.com')
    house = service.create_house(db, a.id, h.HouseholdCreate(label='Synthetic home', adult_confirmed=True))
    invite = service.invite(db, a.id, house['id'], h.InviteCreate(member_id=b.id, expected_revision=1, adult_confirmed=True))
    accepted = service.accept(db, b.id, invite['id'], h.InviteAccept(token=invite['token'], adult_confirmed=True))
    return a, b, c, house, invite, accepted


def permission(member, revision=0, granted=True, view='networth'):
    return h.GrantWrite(member_id=member, view=view, expected_revision=revision, granted=granted)


def test_T1102_invites_membership_is_not_permission(db_engine):
    from fastapi import HTTPException
    from backend.models.models import HouseholdMembership, utcnow
    from datetime import timedelta
    with Session(db_engine) as db:
        a, b, c, house, invite, _ = sharing(db)
        service.write(db, a.id, 'networth', book([observation()]))
        for actor in (b, c):
            with pytest.raises(HTTPException) as exc:
                service.shared_view(db, actor.id, house['id'], a.id, 'networth')
            assert exc.value.status_code == 404
        with pytest.raises(HTTPException) as exc:
            service.accept(db, b.id, invite['id'], h.InviteAccept(token=invite['token'], adult_confirmed=True))
        assert exc.value.status_code == 404
        second = service.invite(db, a.id, house['id'], h.InviteCreate(member_id=c.id, expected_revision=3, adult_confirmed=True))
        row = db.get(HouseholdMembership, second['id'])
        row.expires_at = utcnow()-timedelta(seconds=1)
        db.commit()
        with pytest.raises(HTTPException) as exc:
            service.accept(db, c.id, second['id'], h.InviteAccept(token=second['token'], adult_confirmed=True))
        assert exc.value.status_code == 404
        grant = service.grant(db, a.id, house['id'], permission(b.id))
        assert grant['revision'] == 1
        assert service.shared_view(db, b.id, house['id'], a.id, 'networth')['data']['observations']
        with pytest.raises(HTTPException) as exc:
            service.grant(db, c.id, house['id'], permission(b.id))
        assert exc.value.status_code == 404
        with pytest.raises(HTTPException) as exc:
            service.shared_view(db, b.id, house['id'], a.id, 'protection')
        assert exc.value.status_code == 404


def test_T1102_sharing_migration_privacy_and_purge(db_engine):
    from backend.core.owned_stores import _registry, validate_coverage
    from backend.models.models import Household, HouseholdMembership, HouseholdGrant
    validate_coverage()
    for model in (Household, HouseholdMembership, HouseholdGrant):
        assert set(model.__table__.columns.keys()) == {c['name'] for c in inspect(db_engine).get_columns(model.__tablename__)}
    with Session(db_engine) as db:
        a, b, _, house, _, _ = sharing(db)
        service.grant(db, a.id, house['id'], permission(b.id))
        data = _registry['household_sharing'].export(db, a.id)
        assert 'token_hash' not in data['household_memberships'][0]
        participant = _registry['household_sharing'].export(db, b.id)
        assert len(participant['household_memberships']) == len(participant['household_grants']) == 1
        assert participant['households'] == []  # no other owner's private household metadata
        assert 'token_hash' not in participant['household_memberships'][0]
        assert not _registry['household_books'].export(db, b.id)['household_revisions']
        _registry['household_sharing'].purge(db, b.id)
        db.commit()
        assert db.query(HouseholdGrant).count() == db.query(HouseholdMembership).count() == 0
        assert db.get(Household, house['id'])
        _registry['household_sharing'].purge(db, a.id)
        db.commit()
        assert db.query(Household).count() == 0


def test_T1103_revocation_rechecks_view_and_queued_export(db_engine):
    from fastapi import HTTPException
    from backend.core.owned_stores import _registry
    with Session(db_engine) as db:
        a, b, c, house, _, accepted = sharing(db)
        service.write(db, a.id, 'networth', book([observation()]))
        service.grant(db, a.id, house['id'], permission(b.id))
        cached = service.shared_view(db, b.id, house['id'], a.id, 'networth')
        ticket = service.request_export(db, b.id, house['id'], a.id, 'networth')
        assert service.fetch_export(db, b.id, ticket['id'])['data'] == cached['data']
        with pytest.raises(HTTPException) as exc:
            service.fetch_export(db, c.id, ticket['id'])
        assert exc.value.status_code == 404
        service.grant(db, a.id, house['id'], permission(b.id, 1, False))
        for action in (lambda: service.fetch_export(db, b.id, ticket['id']),
                       lambda: service.shared_view(db, b.id, house['id'], a.id, 'networth')):
            with pytest.raises(HTTPException) as exc:
                action()
            assert exc.value.status_code == 404
        # Regrant cannot resurrect an old queued export authorized at revision 1.
        service.grant(db, a.id, house['id'], permission(b.id, 2, True))
        with pytest.raises(HTTPException):
            service.fetch_export(db, b.id, ticket['id'])
        service.revoke_member(db, a.id, house['id'], b.id, h.MembershipRevoke(expected_revision=accepted['revision']))
        with pytest.raises(HTTPException):
            service.shared_view(db, b.id, house['id'], a.id, 'networth')
        exported = _registry['household_books'].export(db, b.id)
        assert exported == {'household_revisions': []}


def test_T1103_chat_and_api_never_receive_household_cache(client):
    from tests.test_stage_c_platform import auth
    a = auth(client, 'chat-house-a@example.com')
    b = auth(client, 'chat-house-b@example.com')
    with client.session_factory() as db:
        from backend.models.models import User
        a_id = db.query(User).filter_by(email='chat-house-a@example.com').one().id
        b_id = db.query(User).filter_by(email='chat-house-b@example.com').one().id
    house = client.post('/households', headers=a, json={'label': 'Synthetic', 'adult_confirmed': True}).json()['id']
    inv = client.post(f'/households/{house}/invites', headers=a,
        json={'member_id': b_id, 'expected_revision': 1, 'adult_confirmed': True}).json()
    assert client.post(f'/household-invites/{inv["id"]}/accept', headers=b,
        json={'token': inv['token'], 'adult_confirmed': True}).status_code == 200
    client.post('/networth', headers=a, json=book([observation('SECRET_PROPERTY', 987654321)]).model_dump(mode='json'))
    assert client.put(f'/households/{house}/grants', headers=a, json=permission(b_id).model_dump()).status_code == 200
    path = f'/households/{house}/views/{a_id}/networth'
    cached = client.get(path, headers=b)
    assert cached.status_code == 200 and cached.headers['cache-control'] == 'no-store'
    client.put(f'/households/{house}/grants', headers=a, json=permission(b_id, 1, False).model_dump())
    assert client.get(path, headers=b).status_code == 404
    chat = client.post('/chat', headers=b, json={'message': 'Show my partner net worth SECRET_PROPERTY', 'client_message_id': str(uuid4())})
    assert chat.status_code == 200
    assert '987654321' not in chat.text
    assert client.get('/finance-snapshot', headers=b).json()['snapshot'] is None


def protection(data, revision=0):
    return h.ProtectionWrite(expected_revision=revision, idempotency_key=str(uuid4()),
                             reason='Synthetic policy declaration', data={'policies': data})


def policy(**extra):
    from datetime import date
    return dict(reference='synthetic-policy', renewal_date=date.today().isoformat(),
                evidence={'renewal_date': 'User declaration, synthetic fixture'}, **extra)


def test_T1104_unknown_policy_fields_evidence_and_preferences(db_engine, monkeypatch):
    from datetime import timedelta
    from backend.models.models import WorkItem, DeliveryAttempt, NotificationPreference, utcnow
    from backend.services import notification_service as notices
    from backend.workers import queue
    with Session(db_engine) as db:
        a, _ = setup(db)
        initial = service.write(db, a.id, 'protection', protection([{'reference': 'unknown'}]))
        assert initial['data']['policies'][0]['coverage_paise'] is None
        assert initial['data']['policies'][0]['premium_paise'] is None
        assert initial['data']['policies'][0]['insurer'] is None
        assert db.query(WorkItem).filter_by(kind='notification').count() == 0
        payload = protection([policy(reminder_opt_in=True)], 1)
        service.write(db, a.id, 'protection', payload)
        service.write(db, a.id, 'protection', payload)
        assert db.query(WorkItem).filter_by(kind='notification').count() == 1
        db.add(NotificationPreference(user_id=a.id, enabled=False, categories=['reminder']))
        work = db.query(WorkItem).filter_by(kind='notification').one()
        work.available_at = utcnow()-timedelta(minutes=1)
        db.commit()
        notices.run_scheduled(db, *queue.claim(db, kind='notification'))
        assert db.query(DeliveryAttempt).one().state == 'suppressed'
        assert 'synthetic-policy' not in db.query(DeliveryAttempt).one().event_key


@pytest.mark.parametrize('data', [{'reference': 'bad', 'coverage_paise': 10000},
    {'reference': 'bad', 'reminder_opt_in': True}, {'reference': 'bad', 'beneficiary_id': 'not-collected'},
    {'reference': 'bad', 'premium_paise': -1}, {'reference': 'bad', 'evidence': {'secret': 'unrecognized'}}])
def test_T1104_invalid_policy(data):
    with pytest.raises(ValueError):
        protection([data])


def test_T1104_edited_policy_suppresses_old_event_and_new_delivery(db_engine):
    from datetime import timedelta
    from backend.models.models import WorkItem, DeliveryAttempt, utcnow
    from backend.services import notification_service as notices
    from backend.workers import queue
    with Session(db_engine) as db:
        a, _ = setup(db)
        service.write(db, a.id, 'protection', protection([policy(reminder_opt_in=True)]))
        job = db.query(WorkItem).filter_by(kind='notification').one()
        service.write(db, a.id, 'protection', protection([policy(reminder_opt_in=False)], 1))
        job.available_at = utcnow()-timedelta(minutes=1)
        db.commit()
        notices.run_scheduled(db, *queue.claim(db, kind='notification'))
        assert db.query(DeliveryAttempt).count() == 0
        service.write(db, a.id, 'protection', protection([policy(reminder_opt_in=True)], 2))
        new = db.query(WorkItem).filter_by(state='queued').one()
        new.available_at = utcnow()-timedelta(minutes=1)
        db.commit()
        notices.run_scheduled(db, *queue.claim(db, kind='notification'))
        assert db.query(DeliveryAttempt).one().state == 'delivered'


def test_T1104_policy_api_private_and_explicit_grant(db_engine):
    from fastapi import HTTPException
    with Session(db_engine) as db:
        a, b, _, house, _, _ = sharing(db)
        service.write(db, a.id, 'protection', protection([{'reference': 'unknown'}]))
        service.grant(db, a.id, house['id'], permission(b.id))
        with pytest.raises(HTTPException) as exc:
            service.shared_view(db, b.id, house['id'], a.id, 'protection')
        assert exc.value.status_code == 404
        service.grant(db, a.id, house['id'], permission(b.id, view='protection'))
        assert service.shared_view(db, b.id, house['id'], a.id, 'protection')['data']['policies'][0]['coverage_paise'] is None


def test_T1106_joint_consolidation_conflicts_and_no_shared_allocation(db_engine):
    from fastapi import HTTPException
    from backend.services import planning_service
    from backend.schemas.planning import GoalWrite
    with Session(db_engine) as db:
        a, b, _, house, _, _ = sharing(db)
        service.write(db, a.id, 'networth', book([observation(share=6000)]))
        service.write(db, b.id, 'networth', book([observation(share=4000)]))
        service.grant(db, a.id, house['id'], permission(b.id))
        snapshot = service.consolidated_view(db, b.id, house['id'])
        assert snapshot['net_worth_paise'] == 8000000  # 48,000 + 32,000, never 160,000
        assert snapshot['allocation_status'] == 'unavailable'
        goal = GoalWrite(expected_revision=0, idempotency_key=str(uuid4()), reason='Synthetic test',
            data={'label': 'Cannot allocate shared asset', 'target_paise': 10000, 'allocated_paise': 100,
                  'target_date': '2027-01-01', 'funding_account_id': 'property'})
        with pytest.raises(HTTPException) as exc:
            planning_service.write(db, b.id, 'goal', goal)
        assert exc.value.status_code == 404
        service.write(db, b.id, 'networth', book([observation(share=5000)], 1))
        with pytest.raises(HTTPException) as exc:
            service.consolidated_view(db, b.id, house['id'])
        assert exc.value.status_code == 409  # >100%, never silently cap
        service.grant(db, a.id, house['id'], permission(b.id, 1, False))
        assert service.consolidated_view(db, b.id, house['id'])['net_worth_paise'] == 4000000
        for view in ('tax', 'transactions', 'documents'):
            with pytest.raises(HTTPException) as exc:
                service.shared_view(db, b.id, house['id'], a.id, view)
            assert exc.value.status_code == 404


def test_T1106_concurrent_grant_changes_and_stale_export(db_engine):
    from tests.test_stage_f_statements import race
    with Session(db_engine) as db:
        a, b, _, house, _, _ = sharing(db)
        a_id, b_id = a.id, b.id
        service.write(db, a_id, 'networth', book([observation()]))
        service.grant(db, a_id, house['id'], permission(b_id))
        ticket = service.request_export(db, b_id, house['id'], a_id, 'networth')
    results = race(db_engine, [
        lambda db: service.grant(db, a_id, house['id'], permission(b_id, 1, False)),
        lambda db: service.grant(db, a_id, house['id'], permission(b_id, 1, False))])
    assert sum(item == 409 for item in results) == 1
    with Session(db_engine) as db:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            service.fetch_export(db, b_id, ticket['id'])
        assert exc.value.status_code == 404
        assert service.consolidated_view(db, b_id, house['id'])['vector'] == {}


def cash_account(db, owner):
    from backend.services.statement_service import create_account
    from backend.schemas.statements import AccountCreate
    return create_account(db, owner, AccountCreate(label='Synthetic cash', token='cash', account_type='synthetic_cash'))


def cash_payload(account, amount=-100000, category='purchase', posting_date='2026-01-02'):
    from backend.schemas.statements import ManualCash
    return ManualCash(expected_revision=account.revision, idempotency_key=str(uuid4()),
        reason='Synthetic cash evidence', account_id=account.id, posting_date=posting_date,
        amount_paise=amount, category=category, description='Synthetic cash entry')


def test_T1403_cash_withdrawal_split_and_manual_origin(db_engine):
    from backend.finance import ledger
    from backend.models.models import LedgerEntry
    from backend.schemas.statements import Split, LinkCreate
    from tests.test_stage_c_security import seed_entry
    from tests.test_stage_c_statements import op
    from backend.services.monthly_report_service import create, vector
    from backend.schemas.statements import ReportCreate
    with Session(db_engine) as db:
        a, bank = setup(db)
        cash = cash_account(db, a.id)
        funding = ledger.manual_cash(db, a.id, cash_payload(cash, 200000, 'transfer'))
        withdrawal = seed_entry(db, a, bank, -200000, 'withdrawal')
        ledger.confirm_link(db, a.id, LinkCreate(**op(withdrawal.revision, left_id=withdrawal.id,
            right_id=funding['id'], expected_right_revision=1, kind='transfer', amount_paise=200000)))
        db.refresh(cash)
        payload = cash_payload(cash)
        manual = ledger.manual_cash(db, a.id, payload)
        assert ledger.manual_cash(db, a.id, payload) == manual
        split = ledger.split(db, a.id, manual['id'], Split(**op(1, components=[
            {'category': 'purchase', 'amount_paise': -80000}, {'category': 'fee', 'amount_paise': -20000}])))
        assert sum(c['amount_paise'] for c in split['components']) == -100000
        facts = ledger.metrics(db.query(LedgerEntry).all(), db.query(ledger.LedgerLink).all())
        assert facts['spending_paise'] == 100000  # withdrawal/funding excluded, cash purchase counted once
        report = create(db, a.id, ReportCreate(month='2026-01', account_ids=[bank.id, cash.id], expected_vector=vector(db, a.id)))
        assert report['snapshot']['selected_scope_complete'] is False
        assert next(s for s in report['snapshot']['sources'] if s['entry_id'] == manual['id'])['origin'] == 'manual_cash'


def test_T1403_explicit_later_bank_match_and_reversal_restores_manual(db_engine):
    from backend.finance import ledger
    from backend.models.models import LedgerEntry, LedgerEvidence
    from backend.schemas.statements import ManualMatch, Operation
    from tests.test_stage_c_statements import imported, publish, op
    with Session(db_engine) as db:
        a, bank = setup(db)
        cash = cash_account(db, a.id)
        job = imported(db, a, bank)
        publish(db, a, job)
        bank_entry = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        manual = ledger.manual_cash(db, a.id, cash_payload(cash, bank_entry.amount_paise,
            'purchase', bank_entry.posting_date))
        before = ledger.metrics(db.query(LedgerEntry).all())
        assert before['spending_paise'] == 11000000  # both origins until explicit evidence review
        request = ManualMatch(**op(bank_entry.revision, manual_entry_id=manual['id'],
            expected_manual_revision=1, evidence='User confirms same purchase from dated synthetic receipt'))
        match = ledger.match_manual(db, a.id, bank_entry.id, request)
        assert ledger.match_manual(db, a.id, bank_entry.id, request) == match
        assert ledger.metrics(db.query(LedgerEntry).all())['spending_paise'] == 5500000
        assert db.get(LedgerEntry, manual['id']).origin == 'manual_cash'
        assert db.query(LedgerEvidence).filter_by(entry_id=bank_entry.id, active=True).count() == 1
        ledger.reverse(db, a.id, job.id, Operation(**op(job.revision)))
        assert db.get(LedgerEntry, manual['id']).active is True
        assert ledger.metrics(db.query(LedgerEntry).all())['spending_paise'] == 5500000


def test_T1403_manual_api_validation_owner_and_split(client, monkeypatch):
    from tests.test_stage_c_platform import auth
    a, b = auth(client, 'manual-a@example.com'), auth(client, 'manual-b@example.com')
    account = client.post('/statement-accounts', headers=a, json={'label': 'cash', 'token': 'cash', 'account_type': 'synthetic_cash'}).json()
    payload = dict(account_id=account['id'], expected_revision=account['revision'], idempotency_key=str(uuid4()), reason='Synthetic',
        amount_paise=-12345, posting_date='2026-01-02', description='Synthetic', category='purchase')
    assert client.post('/transactions/manual', headers=b, json=payload).status_code == 404
    out = client.post('/transactions/manual', headers=a, json=payload)
    assert out.status_code == 201, out.text
    entry = out.json()['id']
    split = dict(expected_revision=1, idempotency_key=str(uuid4()), reason='Synthetic',
                 components=[{'category': 'purchase', 'amount_paise': -12344}])
    assert client.post(f'/transactions/{entry}/split', headers=a, json=split).status_code == 422
    assert client.post(f'/transactions/{entry}/split', headers=b, json=split).status_code == 404
    assert client.post('/transactions/manual', headers=a, json={**payload, 'amount_paise': True}).status_code == 422
    assert client.post('/transactions/manual', headers=a, json={**payload, 'posting_date': '2099-01-01'}).status_code == 422
    assert client.post(f'/statement-accounts/{account["id"]}/uploads',
                       headers={**a, 'Content-Type': 'text/csv'}, content=b'test').status_code == 422
    monkeypatch.setattr(config, 'SYNTHETIC_MANUAL_CASH_ENABLED', False)
    assert client.post('/transactions/manual', headers=a, json=payload).status_code == 404


def test_T1403_migration_origin_recovery(db_engine):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.finance import ledger
    from backend.models.models import LedgerEntry
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0171')
    assert 'origin' not in {c['name'] for c in inspect(db_engine).get_columns('ledger_entries')}
    command.upgrade(cfg, 'head')
    assert set(LedgerEntry.__table__.columns.keys()) == {c['name'] for c in inspect(db_engine).get_columns('ledger_entries')}
    with Session(db_engine) as db:
        a, _ = setup(db)
        cash = cash_account(db, a.id)
        ledger.manual_cash(db, a.id, cash_payload(cash))
        with pytest.raises(RuntimeError, match='Manual origin'):
            command.downgrade(cfg, '0171')


def test_T1403_manual_race_idempotency_and_registry(db_engine):
    from tests.test_stage_f_statements import race
    from backend.finance import ledger
    from backend.models.models import LedgerEntry
    from backend.core.owned_stores import _registry
    with Session(db_engine) as db:
        a, _ = setup(db)
        cash = cash_account(db, a.id)
        payload = cash_payload(cash)
        owner = a.id
    results = race(db_engine, [lambda db: ledger.manual_cash(db, owner, payload),
                               lambda db: ledger.manual_cash(db, owner, payload)])
    assert results[0] == results[1] and isinstance(results[0], dict)
    with Session(db_engine) as db:
        assert db.query(LedgerEntry).count() == 1
        assert _registry['statements'].export(db, owner)['ledger_entries'][0]['origin'] == 'manual_cash'
        _registry['statements'].purge(db, owner)
        db.commit()
        assert db.query(LedgerEntry).count() == 0


def test_T1406_parser_drift_quarantine_rollback_and_immutable_snapshot(db_engine, monkeypatch):
    from backend.finance import ledger
    from backend.finance.importers import registry
    from backend.models.models import StatementImport, StatementRow, LedgerEntry
    from backend.schemas.statements import Operation, ReportCreate
    from backend.services import statement_service as statements, monthly_report_service as reports
    from tests.test_stage_c_statements import imported, publish, op, load
    from backend.workers import queue
    from fastapi import HTTPException
    with Session(db_engine) as db:
        owner, account = setup(db)
        original = imported(db, owner, account)
        publish(db, owner, original)
        report = reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id],
            expected_vector=reports.vector(db, owner.id)))
        original_snapshot = report['snapshot']
        original_csv = reports.export_csv(db, owner.id, report['id'])
        assert original_snapshot['metrics']['spending_paise'] == 5500000
        assert original_snapshot['metrics']['income_paise'] == 4500000
        with pytest.raises(HTTPException) as exc:
            ledger.reprocess(db, owner.id, original.id, Operation(**op(original.revision)))
        assert exc.value.status_code == 409  # explicit reversal required
        ledger.reverse(db, owner.id, original.id, Operation(**op(original.revision)))
        # Registry v2 with installed v1 runtime: drift never stages/publishes facts.
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.unapproved.v2')
        drift = ledger.reprocess(db, owner.id, original.id, Operation(**op(original.revision)))
        statements.process_claimed(db, *queue.claim(db, kind='statement'))
        drift_row = db.get(StatementImport, drift['id'])
        assert drift_row.state == 'quarantined' and drift_row.error_code == 'parser_version_changed'
        assert db.query(StatementRow).filter_by(import_id=drift_row.id).count() == 0
        with pytest.raises(HTTPException):
            publish(db, owner, drift_row)
        # Explicit rollback + reprocess the latest quarantined generation.
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.v1')
        restored = ledger.reprocess(db, owner.id, drift_row.id, Operation(**op(drift_row.revision)))
        statements.process_claimed(db, *queue.claim(db, kind='statement'))
        publish(db, owner, db.get(StatementImport, restored['id']))
        assert restored['generation'] == 3
        assert db.query(LedgerEntry).filter_by(active=True).count() == 2
        assert reports.read(db, owner.id, report['id'])['snapshot'] == original_snapshot
        assert reports.export_csv(db, owner.id, report['id']) == original_csv
        assert reports.read(db, owner.id, report['id'])['stale']
        assert statements.upload(db, owner.id, account.id, load()).id == restored['id']  # digest reuse


def test_T1406_reprocess_restart_lease_fencing_and_wrong_owner(db_engine):
    from backend.finance import ledger
    from backend.models.models import StatementImport, StatementRow, WorkItem, utcnow
    from backend.schemas.statements import Operation
    from backend.services import statement_service as statements
    from tests.test_stage_c_statements import imported, op
    from tests.test_stage_b import signup
    from backend.workers import queue
    from fastapi import HTTPException
    from datetime import timedelta
    with Session(db_engine) as db:
        owner, account = setup(db)
        other = signup(db, 'other-adapter')
        original = imported(db, owner, account)
        with pytest.raises(HTTPException) as exc:
            ledger.reprocess(db, other.id, original.id, Operation(**op(original.revision)))
        assert exc.value.status_code == 404
        ledger.cancel(db, owner.id, original.id, Operation(**op(original.revision)))
        payload = Operation(**op(original.revision))
        new = ledger.reprocess(db, owner.id, original.id, payload)
        assert ledger.reprocess(db, owner.id, original.id, payload) == new
        stale_claim = queue.claim(db, kind='statement')
        work = db.get(WorkItem, stale_claim[0])
        work.lease_until = utcnow()-timedelta(seconds=1)
        db.commit()
        owner_id, original_id, new_id = owner.id, original.id, new['id']
    # New DB session simulates worker process restart; new fence wins publication.
    with Session(db_engine) as db:
        fresh_claim = queue.claim(db, kind='statement')
        assert fresh_claim[0] == stale_claim[0] and fresh_claim[1] > stale_claim[1]
        with pytest.raises(ValueError, match='Stale lease'):
            statements.process_claimed(db, *stale_claim)
        statements.process_claimed(db, *fresh_claim)
        assert db.get(StatementImport, new_id).state == 'needs_review'
        assert db.query(StatementRow).filter_by(import_id=new_id).count() == 2
        assert db.query(StatementRow).filter_by(import_id=original_id).count() == 2


def test_household_inactive_owner_uniform_denial_and_shared_export_quota(db_engine, monkeypatch):
    from fastapi import HTTPException
    with Session(db_engine) as db:
        a, b, c, house, _, _ = sharing(db)
        service.write(db, a.id, 'networth', book([observation()]))
        service.grant(db, a.id, house['id'], permission(b.id))
        monkeypatch.setattr(config, 'EXPORT_DAILY_LIMIT', 1)
        ticket = service.request_export(db, b.id, house['id'], a.id, 'networth')
        with pytest.raises(HTTPException) as exc:
            service.request_export(db, b.id, house['id'], a.id, 'networth')
        assert exc.value.status_code == 429
        a.is_active = False  # held records can remain after access suppression
        db.commit()
        for actor in (b.id, c.id):
            for identity in (house['id'], 'missing'):
                with pytest.raises(HTTPException) as exc:
                    service.shared_view(db, actor, identity, a.id, 'networth')
                assert exc.value.status_code == 404
        with pytest.raises(HTTPException) as exc:
            service.fetch_export(db, b.id, ticket['id'])
        assert exc.value.status_code == 404


def test_empty_inventory_is_unknown_instead_of_zero():
    result = service.consolidate([])
    assert result['assets_paise'] is result['liabilities_paise'] is result['net_worth_paise'] is None
    assert result['status'] == 'partial' and 'declared_observations' in result['missing_inputs']
