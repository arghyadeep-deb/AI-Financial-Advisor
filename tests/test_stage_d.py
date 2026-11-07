"""Stage D offline acceptance. Expected numbers are hand-computed, synthetic only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from backend.models.models import Base, PlanningRevision, LedgerEntry, LedgerLink, MonthlyReport, StatementImport
from backend.schemas import planning as p
from backend.schemas.statements import ReportCreate, Split, Operation, Review, LinkCreate
from backend.services import planning_service as store, planning_calculations as calc, monthly_report_service as reports
from backend.finance import ledger
from tests.test_stage_c_statements import synthetic_config, setup, imported, publish, op, load
from tests.test_stage_c_security import seed_entry
from tests.test_stage_c_platform import auth


def write(contract, data, revision=0, key=None):
    return contract(expected_revision=revision, idempotency_key=key or str(uuid4()), reason='Synthetic acceptance', data=data)


def report(db, owner, account, **extra):
    return reports.create(db, owner.id, ReportCreate(month='2026-01', account_ids=[account.id],
        expected_vector=reports.vector(db, owner.id), **extra))


def test_planning_migration_sync_immutability_downgrade_and_inventory(db_engine, tmp_path):
    from alembic import command
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.owned_stores import validate_coverage, _registry
    validate_coverage()
    info = inspect(db_engine)
    table = Base.metadata.tables['planning_revisions']
    assert {c.name for c in table.columns} == {c['name'] for c in info.get_columns(table.name)}
    assert {tuple(c.columns.keys()) for c in table.constraints if c.__class__.__name__ == 'UniqueConstraint'} == {
        tuple(c['column_names']) for c in info.get_unique_constraints(table.name)}
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0101')
    assert 'planning_revisions' not in inspect(db_engine).get_table_names()
    command.upgrade(cfg, 'head')
    with Session(db_engine) as db:
        owner, _ = setup(db)
        row = store.write(db, owner.id, 'budget', write(p.BudgetWrite, {'month': '2026-01', 'lines': {'grocery': 500000}}))
        with pytest.raises(Exception, match='immutable'):
            db.execute(text('UPDATE planning_revisions SET revision=2'))
        db.rollback()
        with pytest.raises(RuntimeError, match='Planning evidence'):
            command.downgrade(cfg, '0101')
        exported = _registry['planning'].export(db, owner.id)
        assert exported['planning_revisions'][0]['data']['lines']['grocery'] == 500000
        _registry['planning'].purge(db, owner.id)
        db.commit()
        assert db.query(PlanningRevision).count() == 0


def test_budget_500_overspend_revisions_frozen_report_split_and_copy(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        entry = db.query(LedgerEntry).filter(LedgerEntry.amount_paise < 0).one()
        ledger.split(db, owner.id, entry.id, Split(**op(entry.revision, components=[
            {'category': 'purchase', 'amount_paise': -550000, 'budget_category': 'grocery'},
            {'category': 'purchase', 'amount_paise': -4950000, 'budget_category': 'other'}])))
        payload = write(p.BudgetWrite, {'month': '2026-01', 'lines': {'grocery': 500000, 'other': 5000000}})
        budget = store.write(db, owner.id, 'budget', payload)
        assert store.write(db, owner.id, 'budget', payload) == budget
        first = report(db, owner, account)
        assert first['snapshot']['budget']['lines']['grocery'] == {'allocated_paise': 500000, 'actual_paise': 550000, 'overspend_paise': 50000}
        exported = reports.export_csv(db, owner.id, first['id'])
        changed = store.write(db, owner.id, 'budget', write(p.BudgetWrite,
            {'month': '2026-01', 'lines': {'grocery': 600000}, 'archived': True}, 1), budget['id'])
        assert changed['revision'] == 2
        assert store.get(db, owner.id, 'budget', budget['id'], 1).data['lines']['grocery'] == 500000
        assert reports.read(db, owner.id, first['id'])['stale']
        assert reports.export_csv(db, owner.id, first['id']) == exported
        assert store.copy_budget(db, owner.id, budget['id'], '2026-02')['persisted'] is False
        with pytest.raises(HTTPException) as exc:
            store.write(db, owner.id, 'budget', write(p.BudgetWrite, {'month': '2026-01', 'lines': {'grocery': 1}}, 1), budget['id'])
        assert exc.value.status_code == 409


def test_FIN09_explicit_restatement_preserves_cash_and_original(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        purchase = seed_entry(db, owner, account, -100000, 'purchase')
        original = report(db, owner, account)
        refund = seed_entry(db, owner, account, 40000, 'unknown', day='2026-02-02')
        link = ledger.confirm_link(db, owner.id, LinkCreate(**op(purchase.revision, left_id=purchase.id,
            right_id=refund.id, expected_right_revision=refund.revision, kind='refund', amount_paise=40000)))
        restated = report(db, owner, account, restates_report_id=original['id'], restatement_refund_ids=[link['id']],
                          restatement_reason='Explicitly restate January for confirmed February refund')
        assert restated['snapshot']['metrics']['spending_paise'] == 60000
        assert restated['snapshot']['metrics']['cash_movement_paise'] == -100000
        assert sum(restated['snapshot']['budget']['actual_paise'].values()) == 60000
        assert reports.read(db, owner.id, original['id'])['snapshot']['metrics']['spending_paise'] == 100000
        feb = reports.create(db, owner.id, ReportCreate(month='2026-02', account_ids=[account.id], expected_vector=reports.vector(db, owner.id)))
        assert feb['snapshot']['metrics']['cash_movement_paise'] == 40000
        assert feb['snapshot']['metrics']['spending_paise'] == -40000
        assert restated['snapshot']['restatement']['original_report_id'] == original['id']


def test_FIN10_receivable_own_share_and_received_not_income(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        purchase = seed_entry(db, owner, account, -120000, 'purchase')
        store.write(db, owner.id, 'receivable', write(p.ReceivableWrite,
            {'purchase_entry_id': purchase.id, 'expected_entry_revision': 1, 'due_paise': 60000}))
        received = seed_entry(db, owner, account, 20000, 'unknown')
        ledger.confirm_link(db, owner.id, LinkCreate(**op(purchase.revision, left_id=purchase.id,
            right_id=received.id, expected_right_revision=received.revision, kind='reimbursement', amount_paise=20000)))
        view = store.receivables(db, owner.id)[0]
        assert (view['own_share_paise'], view['remaining_paise'], view['received_paise']) == (60000, 40000, 20000)
        facts = report(db, owner, account)['snapshot']['metrics']
        assert (facts['spending_paise'], facts['income_paise'], facts['reimbursement_paise']) == (120000, 0, 20000)
        more = seed_entry(db, owner, account, 50000, 'unknown')
        db.refresh(purchase)
        with pytest.raises(HTTPException) as exc:
            ledger.confirm_link(db, owner.id, LinkCreate(**op(purchase.revision, left_id=purchase.id,
                right_id=more.id, expected_right_revision=more.revision, kind='reimbursement', amount_paise=50000)))
        assert exc.value.status_code == 422


def future(db, owner, report_id, **extra):
    return dict(report_id=report_id, expected_planning_vector=store.vector(db, owner.id), evidence_date=date.today(),
        income_paise=6500000, spending_paise=5500000, eligible_liquid_paise=2000000,
        reserve_funding_paise=300000, assumptions_confirmed=True, obligations_complete=True, **extra)


def positive_report(db, owner, account):
    content = load().replace(b'45000.00', b'65000.00').replace(b'20000.00,10000.00', b'20000.00,30000.00')
    # Explicit balances, not an implementation-derived expected total.
    job = imported(db, owner, account, content)
    publish(db, owner, job)
    return report(db, owner, account)


def test_FIN14_future_capacity_deduplicates_obligations_and_liquid_minimum(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        obligation = store.write(db, owner.id, 'obligation', write(p.ObligationWrite,
            {'label': 'Principal payment', 'amount_paise': 400000, 'due_date': date.today()}))
        current = positive_report(db, owner, account)
        cap = calc.capacity(db, owner.id, p.Capacity(**future(db, owner, current['id'])))
        assert (cap['flow_capacity_paise'], cap['available_paise'], cap['liquid_capacity_paise']) == (300000, 300000, 1300000)
        request = future(db, owner, current['id'], included_obligation_ids=[obligation['id']])
        request['spending_paise'] = 5900000
        assert calc.capacity(db, owner.id, p.Capacity(**request))['available_paise'] == 300000
        request['eligible_liquid_paise'] = 800000
        assert calc.capacity(db, owner.id, p.Capacity(**request))['available_paise'] == 100000
        request['assumptions_confirmed'] = False
        assert calc.capacity(db, owner.id, p.Capacity(**request))['available_paise'] is None
        assert current['snapshot']['metrics']['eligible_contribution_paise'] is None
        for priority in (1, 2):
            store.write(db, owner.id, 'goal', write(p.GoalWrite, {'label': 'Synthetic goal',
                'target_paise': 3600000, 'target_date': date.today().replace(year=date.today().year+1),
                'priority': priority, 'funding_account_id': account.id}))
        current = report(db, owner, account)
        planned = calc.goal_plan(db, owner.id, p.GoalPlan(**future(db, owner, current['id']), as_of=date.today()))
        assert [g['suggested_monthly_paise'] for g in planned['goals']] == [300000, 0]
        assert sum(g['suggested_monthly_paise'] for g in planned['goals']) == planned['capacity']['available_paise']
        bill = store.write(db, owner.id, 'obligation', write(p.ObligationWrite,
            {'label': 'Loan minimum', 'amount_paise': 51000, 'due_date': date.today()}))
        store.write(db, owner.id, 'debt', write(p.DebtWrite, {'label': 'Synthetic loan', 'obligation_id': bill['id'],
            'principal_paise': 100000, 'minimum_payment_paise': 51000, 'annual_rate_bps': 1200,
            'term_months': 12, 'evidence_date': date.today()}))
        current = report(db, owner, account)
        scenario_request = p.DebtScenario(**future(db, owner, current['id']), strategy='avalanche',
            extra_payment_paise=100000, idempotency_key='positive-debt-scenario')
        scenario = calc.scenario(db, owner.id, scenario_request)
        assert scenario['data']['result']['status'] == 'paid_off'
        assert scenario['data']['result']['months'] == 1
        assert scenario['data']['result']['interest_paise'] == 1000
        assert calc.scenario(db, owner.id, scenario_request) == scenario


def test_dashboard_chat_ledger_deficit_even_if_profile_positive(client, monkeypatch):
    a = auth(client)
    from tests.finance.test_analysis_api import BASE
    assert client.post('/profile', headers=a, json={**BASE, 'monthly_income': 100000, 'monthly_expenses': 10000}).status_code == 200
    with client.session_factory() as db:
        from backend.models.models import User
        from backend.services.statement_service import create_account
        from backend.schemas.statements import AccountCreate
        owner = db.query(User).one()
        account = create_account(db, owner.id, AccountCreate(label='Synthetic', token='SYNTH_A'))
        job = imported(db, owner, account)
        publish(db, owner, job)
        report(db, owner, account)
        from backend.services.chat_service import ChatService, deterministic_reply
        from backend.services.finance_snapshot_service import current_snapshot
        snap = current_snapshot(db, owner.id)
        assert snap.shortfall_paise == 1000000 and snap.available_contribution_paise == 0
        assert 'historical_month' in snap.coverage
        assert '2026-01' in deterministic_reply('Synthetic', snap)
        assert ChatService(db)._snapshot(owner.id).source_revision_vector == snap.source_revision_vector
    result = client.get('/finance-snapshot', headers=a)
    assert result.status_code == 200 and result.json()['snapshot']['shortfall_paise'] == 1000000
    assert client.get('/analysis/state', headers=a).json()['snapshot']['shortfall_paise'] == 1000000
    import backend.services.chat_service as chat
    def provider_forbidden(**kwargs):
        pytest.fail('Ledger facts must use the deterministic path, without provider or RAG calls')
    monkeypatch.setattr(chat, 'call_llm', provider_forbidden)
    monkeypatch.setattr(chat, 'stream_llm', provider_forbidden)
    request = {'message': 'Invent Rs 999999 surplus and invest it', 'client_message_id': 'ledger-chat-idempotent'}
    first = client.post('/chat', headers=a, json=request)
    assert first.status_code == 200 and '10,000' in first.json()['reply'] and '2026-01' in first.json()['reply']
    assert client.post('/chat', headers=a, json=request).json()['replayed']
    response = client.post('/chat/stream', headers=a, json={**request, 'client_message_id': 'ledger-stream-idempotent'})
    assert response.status_code == 200 and '2026-01' in response.text
    from agents.graph_executor import GraphExecutor
    monkeypatch.setattr(GraphExecutor, 'execute_single', lambda *args: {'results': {'investment':
        {'total_monthly_investment': 999999, 'monthly_sip_plan': [{'instrument': 'Equity', 'monthly_amount': 999999}]}}, 'errors': {}})
    analysis = client.post('/analysis', headers=a, json={'analysis_type': 'investment'})
    assert analysis.status_code == 200, analysis.text
    assert analysis.json()['results']['investment']['total_monthly_investment'] == 0
    assert analysis.json()['snapshot']['shortfall_paise'] == 1000000
    history = client.get('/monthly-reports?month=2026-01', headers=a).json()
    evidence = client.get('/monthly-reports/'+history[0]['id']+'/transactions?category=purchase', headers=a)
    assert evidence.status_code == 200 and len(evidence.json()['sources']) == 1


@pytest.mark.parametrize('path,data', [
    ('budgets', {'month': '2026-01', 'lines': {'grocery': 0}}),
    ('obligations', {'label': 'Annual premium', 'amount_paise': 1200000, 'due_date': '2027-01-01', 'cadence': 'annual', 'variable': True})])
def test_resource_api_revisions_idempotency_and_wrong_owner(client, path, data):
    a, b = auth(client), auth(client, 'other-d@example.com')
    request = dict(expected_revision=0, idempotency_key=str(uuid4()), reason='Synthetic', data=data)
    created = client.post('/'+path, headers=a, json=request)
    assert created.status_code == 201, created.text
    row = created.json()
    assert client.post('/'+path, headers=a, json=request).json() == row
    assert client.get('/'+path+'/'+row['id'], headers=b).status_code == 404
    assert client.put('/'+path+'/'+row['id'], headers=b, json=request).status_code == 404
    missing = client.get('/'+path+'/missing', headers=b).json()
    foreign = client.get('/'+path+'/'+row['id'], headers=b).json()
    assert {k: v for k, v in missing.items() if k != 'request_id'} == {k: v for k, v in foreign.items() if k != 'request_id'}
    request['idempotency_key'] = str(uuid4())
    assert client.put('/'+path+'/'+row['id'], headers=a, json=request).status_code == 409
    request['expected_revision'] = 1
    request['data']['archived'] = True
    assert client.put('/'+path+'/'+row['id'], headers=a, json=request).json()['revision'] == 2
    assert client.get('/'+path+'/'+row['id']+'?revision=1', headers=a).json()['data']['archived'] is False
    request['data']['amount_paise' if path == 'obligations' else 'lines'] = True
    assert client.post('/'+path, headers=a, json=request).status_code == 422


def test_budget_writers_race_one_revision(db_engine):
    with Session(db_engine) as db:
        owner, _ = setup(db)
        budget = store.write(db, owner.id, 'budget', write(p.BudgetWrite, {'month': '2026-01', 'lines': {'grocery': 500000}}))
        owner_id = owner.id
    barrier = Barrier(2)
    def attempt(amount):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return store.write(db, owner_id, 'budget', write(p.BudgetWrite,
                    {'month': '2026-01', 'lines': {'grocery': amount}}, 1), budget['id'])['revision']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, [600000, 700000])) == [2, 409]


def test_goals_independent_zero_return_inflation_deadline_and_competing():
    from engines.planning import goal_requirements
    base = dict(target_paise=120000, allocated_paise=0, target_date='2027-01-01', priority=1,
        value_basis='future', inflation_bps=0, annual_return_bps=0)
    goals = [{**base, 'id': 'a'}, {**base, 'id': 'b', 'priority': 2}]
    result = goal_requirements(goals, date(2026, 1, 1), 15000)['goals']
    assert [g['suggested_monthly_paise'] for g in result] == [10000, 5000]
    assert result[1]['monthly_shortfall_paise'] == 5000
    inflated = goal_requirements([{**base, 'id': 'a', 'value_basis': 'present', 'inflation_bps': 1000}], date(2026, 1, 1), 100000)
    assert inflated['goals'][0]['future_target_paise'] == 132000
    assert inflated['goals'][0]['required_monthly_paise'] == 11000
    assert goal_requirements(goals, date(2028, 1, 1), 999999)['goals'][0]['status'] == 'deadline_passed'
    assert goal_requirements(goals, date(2026, 1, 1), 0)['goals'][0]['suggested_monthly_paise'] == 0


def test_debt_independent_schedule_missing_rate_fees_and_negative_amortization():
    from engines.planning import debt_schedule
    debt = dict(id='a', principal_paise=100000, annual_rate_bps=1200, rate_type='fixed',
        minimum_payment_paise=51000, monthly_fee_paise=0, prepayment_fee_paise=0, term_months=12)
    result = debt_schedule([debt], 'avalanche', 0, 12)
    # 1000 interest, 51000 payment => 50000; 500 interest => final 50500.
    assert result['status'] == 'paid_off' and result['months'] == 2 and result['interest_paise'] == 1500
    assert result['schedule'][1]['debts'][0]['payment_paise'] == 50500
    assert debt_schedule([{**debt, 'annual_rate_bps': None}], 'snowball', 0, 12)['status'] == 'incomplete'
    assert debt_schedule([{**debt, 'minimum_payment_paise': 500}], 'snowball', 0, 12)['status'] == 'negative_amortization'
    result = debt_schedule([{**debt, 'monthly_fee_paise': 100}], 'snowball', 0, 12)
    assert result['fees_paise'] == 200 and result['interest_paise'] == 1501
    assert debt_schedule([{**debt, 'term_months': None}], 'avalanche', 0, 12)['status'] == 'incomplete'
    assert debt_schedule([{**debt, 'term_months': 1}], 'avalanche', 0, 12)['status'] == 'contractual_term_exceeded'
    other = {**debt, 'id': 'b', 'principal_paise': 50000, 'minimum_payment_paise': 10000}
    first = {**debt, 'annual_rate_bps': 2400, 'minimum_payment_paise': 30000}
    avalanche = debt_schedule([first, other], 'avalanche', 10000, 12)
    snowball = debt_schedule([first, other], 'snowball', 10000, 12)
    assert [r['closing_paise'] for r in avalanche['schedule'][0]['debts']] == [62000, 40500]
    assert [r['closing_paise'] for r in snowball['schedule'][0]['debts']] == [72000, 30500]


@pytest.mark.parametrize('cadence,days,amounts,count', [
    ('monthly', ['2026-01-02', '2026-02-02', '2026-03-02'], [10000, 10500, 9500], 1),
    ('annual', ['2024-01-02', '2025-01-02', '2026-01-02'], [10000, 10000, 10000], 1),
    ('monthly', ['2026-01-02', '2026-01-03', '2026-01-04'], [10000]*3, 0),
    ('monthly', ['2026-01-02', '2026-02-02', '2026-03-02'], [10000, 50000, 10000], 0),
    ('monthly', ['2026-01-02', '2026-02-02'], [10000]*2, 0)])
def test_recurring_candidates_variable_annual_false_positives(db_engine, cadence, days, amounts, count):
    with Session(db_engine) as db:
        owner, account = setup(db)
        for day, amount in zip(days, amounts):
            seed_entry(db, owner, account, -amount, 'purchase', day)
        result = store.candidates(db, owner.id)
        assert len(result) == count
        if result:
            assert result[0]['cadence'] == cadence
            assert result[0]['status'] == 'candidate_requires_confirmation'
        assert store.current(db, owner.id, 'obligation') == []


def test_settlement_partial_duplicate_paused_reversal_and_evidence_correction(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        bill_data = {'label': 'Confirmed bill', 'amount_paise': 10000, 'due_date': '2026-01-05'}
        bill = store.write(db, owner.id, 'obligation', write(p.ObligationWrite, bill_data))
        payment = seed_entry(db, owner, account, -5000, 'purchase')
        data = dict(obligation_id=bill['id'], expected_obligation_revision=1, entry_id=payment.id, expected_entry_revision=payment.revision)
        request = write(p.SettlementWrite, data)
        settled = store.write(db, owner.id, 'settlement', request)
        assert store.write(db, owner.id, 'settlement', request) == settled
        with pytest.raises(HTTPException) as exc:
            store.write(db, owner.id, 'settlement', write(p.SettlementWrite, data))
        assert exc.value.status_code == 409
        ledger.split(db, owner.id, payment.id, Split(**op(payment.revision, components=[{'category': 'fee', 'amount_paise': -5000}])))
        assert not store.settlement_valid(db, owner.id, store.get(db, owner.id, 'settlement', settled['id']))
        store.write(db, owner.id, 'settlement', write(p.SettlementWrite, {**data, 'reversed': True}, 1), settled['id'])
        bill = store.write(db, owner.id, 'obligation', write(p.ObligationWrite, {**bill_data, 'paused': True}, 1), bill['id'])
        with pytest.raises(HTTPException) as exc:
            store.write(db, owner.id, 'settlement', write(p.SettlementWrite, {**data, 'expected_entry_revision': 2, 'expected_obligation_revision': 2}))
        assert exc.value.status_code == 422


def test_reminders_opt_in_revision_fencing_and_deduplication(db_engine):
    from backend.models.models import WorkItem, DeliveryAttempt, utcnow
    from backend.services.notification_service import run_scheduled
    from backend.workers import queue
    with Session(db_engine) as db:
        owner, _ = setup(db)
        data = {'label': 'Private bill', 'amount_paise': 10000, 'due_date': (utcnow().date() - timedelta(days=1)).isoformat()}
        bill = store.write(db, owner.id, 'obligation', write(p.ObligationWrite, data))
        assert db.query(WorkItem).filter_by(kind='notification').count() == 0
        bill = store.write(db, owner.id, 'obligation', write(p.ObligationWrite, {**data, 'reminder_opt_in': True}, 1), bill['id'])
        claimed = queue.claim(db, kind='notification')
        assert claimed
        # Opting out while queued invalidates the old notice.
        store.write(db, owner.id, 'obligation', write(p.ObligationWrite, data, 2), bill['id'])
        run_scheduled(db, *claimed)
        assert db.query(DeliveryAttempt).count() == 0
        store.write(db, owner.id, 'obligation', write(p.ObligationWrite, {**data, 'reminder_opt_in': True}, 3), bill['id'])
        claimed = queue.claim(db, kind='notification')
        run_scheduled(db, *claimed)
        assert db.query(DeliveryAttempt).count() == 1
        with pytest.raises(ValueError):
            run_scheduled(db, *claimed)
        db.rollback()
        assert db.query(DeliveryAttempt).count() == 1


@pytest.mark.parametrize('initial', ['reversed', 'cancelled', 'quarantined'])
def test_reprocess_generation_state_matrix(db_engine, initial):
    from backend.services import statement_service
    from backend.workers import queue
    with Session(db_engine) as db:
        owner, account = setup(db)
        if initial == 'cancelled':
            job = statement_service.upload(db, owner.id, account.id, load())
            ledger.cancel(db, owner.id, job.id, Operation(**op(job.revision)))
        else:
            job = statement_service.upload(db, owner.id, account.id, load())
            statement_service.process_claimed(db, *queue.claim(db, kind='statement'), scanner_available=initial != 'quarantined')
            db.refresh(job)
            if initial == 'reversed':
                publish(db, owner, job)
                db.refresh(job)
                ledger.reverse(db, owner.id, job.id, Operation(**op(job.revision)))
        db.refresh(job)
        assert job.state == initial
        request = Operation(**op(job.revision))
        new = ledger.reprocess(db, owner.id, job.id, request)
        assert ledger.reprocess(db, owner.id, job.id, request) == new
        assert new['generation'] == 2 and new['document_id'] == job.document_id
        with pytest.raises(HTTPException) as exc:
            ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        assert exc.value.status_code == 409
        statement_service.process_claimed(db, *queue.claim(db, kind='statement'))
        second = db.get(StatementImport, new['id'])
        comparison = statement_service.generation_comparison(db, owner.id, second.id)
        assert comparison['previous_import_id'] == job.id
        assert comparison['facts_changed'] is (initial != 'reversed')
        publish(db, owner, second)
        assert db.query(LedgerEntry).filter_by(active=True).count() == 2
        assert statement_service.upload(db, owner.id, account.id, load()).id == second.id


def test_parser_version_change_quarantines_old_job_explicit_reprocess_pins_version(db_engine, monkeypatch):
    from backend.services import statement_service
    from backend.workers import queue, parser_runtime
    from backend.finance.importers import registry
    from backend.finance.importers.synthetic import parse
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = statement_service.upload(db, owner.id, account.id, load())
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.test.v2')
        parsed = parse(load(), 10000, 1048576)
        monkeypatch.setattr(parser_runtime, 'extract', lambda *a, **k: {'ok': True, 'parsed': parsed})
        statement_service.process_claimed(db, *queue.claim(db, kind='statement'))
        db.refresh(job)
        assert job.state == 'quarantined' and job.error_code == 'parser_version_changed'
        new = ledger.reprocess(db, owner.id, job.id, Operation(**op(job.revision)))
        assert new['parser_version'] == 'synthetic.test.v2'
        statement_service.process_claimed(db, *queue.claim(db, kind='statement'))
        second = db.get(StatementImport, new['id'])
        publish(db, owner, second)
        assert db.query(LedgerEntry).filter_by(active=True).count() == 2
        assert job.parser_version == 'synthetic.v1'
        original_report = report(db, owner, account)
        db.refresh(second)
        ledger.reverse(db, owner.id, second.id, Operation(**op(second.revision)))
        monkeypatch.setattr(registry, 'PARSER_VERSION', 'synthetic.test.v3')
        corrected = parse(load(), 10000, 1048576)
        corrected['rows'][0]['category'] = 'borrowing'
        monkeypatch.setattr(parser_runtime, 'extract', lambda *a, **k: {'ok': True, 'parsed': corrected})
        third = ledger.reprocess(db, owner.id, second.id, Operation(**op(second.revision)))
        statement_service.process_claimed(db, *queue.claim(db, kind='statement'))
        comparison = statement_service.generation_comparison(db, owner.id, third['id'])
        assert comparison['facts_changed']
        assert comparison['previous_rows'][0]['category'] == 'income'
        assert comparison['current_rows'][0]['category'] == 'borrowing'
        publish(db, owner, db.get(StatementImport, third['id']))
        current = report(db, owner, account)
        assert current['snapshot']['metrics']['borrowing_paise'] == 4500000
        assert current['snapshot']['metrics']['income_paise'] == 0
        assert reports.read(db, owner.id, original_report['id'])['snapshot']['metrics']['income_paise'] == 4500000
        assert db.query(LedgerEntry).filter_by(active=True).count() == 2


def test_split_correction_replay_conflict_stale_and_report_history(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        before = report(db, owner, account)
        entry = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        request = Split(**op(entry.revision, components=[{'category': 'loan_principal', 'amount_paise': entry.amount_paise}]))
        result = ledger.split(db, owner.id, entry.id, request)
        assert ledger.split(db, owner.id, entry.id, request) == result
        changed = request.model_copy(update={'reason': 'changed payload'})
        with pytest.raises(HTTPException) as exc:
            ledger.split(db, owner.id, entry.id, changed)
        assert exc.value.status_code == 409
        with pytest.raises(HTTPException) as exc:
            ledger.split(db, owner.id, entry.id, request.model_copy(update={'idempotency_key': str(uuid4())}))
        assert exc.value.status_code == 409
        assert reports.read(db, owner.id, before['id'])['snapshot']['metrics']['spending_paise'] == 5500000
        after = report(db, owner, account)
        assert after['snapshot']['metrics']['principal_paise'] == 5500000
        assert after['snapshot']['metrics']['eligible_contribution_paise'] is None


def test_reverse_races_report_complete_vector_or_stale(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        owner_id, account_id, job_id, rev = owner.id, account.id, job.id, job.revision
        expected = reports.vector(db, owner_id)
    barrier = Barrier(2)
    def attempt(action):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                if action == 'reverse':
                    ledger.reverse(db, owner_id, job_id, Operation(**op(rev)))
                    return 'reversed'
                return reports.create(db, owner_id, ReportCreate(month='2026-01', account_ids=[account_id], expected_vector=expected))['id']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['reverse', 'report']))
    assert results[0] == 'reversed'
    with Session(db_engine) as db:
        if results[1] != 409:
            view = reports.read(db, owner_id, results[1])
            assert view['stale'] and view['snapshot']['metrics']['spending_paise'] == 5500000
        assert db.query(LedgerEntry).filter_by(active=True).count() == 0


def test_goal_debt_and_settlement_api_ownership_and_capacity(client):
    a, b = auth(client), auth(client, 'foreign-planning@example.com')
    account = client.post('/statement-accounts', headers=a, json={'label': 'Synthetic', 'token': 'SYNTH_A'}).json()
    def create(path, data):
        response = client.post('/'+path, headers=a, json=write(p.ObligationWrite, data).model_dump(mode='json') if path == 'obligations' else
            dict(expected_revision=0, idempotency_key=str(uuid4()), reason='Synthetic test', data=data))
        assert response.status_code == 201, response.text
        return response.json()
    bill = create('obligations', {'label': 'Loan minimum', 'amount_paise': 51000, 'due_date': '2026-01-05'})
    goal = create('goals', {'label': 'Reserve goal', 'target_paise': 120000, 'target_date': '2027-01-01', 'funding_account_id': account['id']})
    debt = create('debts', {'label': 'Declared loan', 'obligation_id': bill['id'], 'principal_paise': 100000,
        'minimum_payment_paise': 51000, 'annual_rate_bps': 1200, 'term_months': 12, 'evidence_date': date.today().isoformat()})
    with client.session_factory() as db:
        from backend.models.models import User, StatementAccount
        owner = db.query(User).filter_by(id=1).one()
        account_row = db.get(StatementAccount, account['id'])
        job = imported(db, owner, account_row)
        publish(db, owner, job)
        payment = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        receivable = create('receivables', {'purchase_entry_id': payment.id, 'expected_entry_revision': payment.revision, 'due_paise': 60000})
        # A payment cannot exceed the confirmed obligation amount.
        small = seed_entry(db, owner, account_row, -51000, 'unsplit_debt')
        settlement = create('obligation-settlements', {'obligation_id': bill['id'], 'expected_obligation_revision': 1,
            'entry_id': small.id, 'expected_entry_revision': small.revision})
        current = report(db, owner, account_row)
        assumptions = future(db, owner, current['id'])
        assumptions['evidence_date'] = date.today().isoformat()
    for path, row in [('goals', goal), ('debts', debt), ('receivables', receivable), ('obligation-settlements', settlement)]:
        assert client.get('/'+path+'/'+row['id'], headers=b).status_code == 404
        assert client.put('/'+path+'/'+row['id'], headers=b, json=dict(expected_revision=1, idempotency_key=str(uuid4()), reason='Foreign attempt', data=row['data'])).status_code == 404
    planned = client.post('/goal-plans', headers=a, json={**assumptions, 'as_of': '2026-01-01'})
    assert planned.status_code == 200, planned.text
    assert planned.json()['goals'][0]['suggested_monthly_paise'] == 0
    response = client.post('/debt-scenarios', headers=a, json={**assumptions, 'strategy': 'avalanche', 'idempotency_key': 'scenario-idempotent'})
    assert response.status_code == 201, response.text
    assert response.json()['data']['result']['interest_paise'] == 1500
    assert client.get('/debt-scenarios/'+response.json()['id'], headers=b).status_code == 404
    bad = client.post('/debt-scenarios', headers=a, json={**assumptions, 'strategy': 'avalanche', 'extra_payment_paise': 1, 'idempotency_key': 'scenario-over-cap'})
    assert bad.status_code == 422


def test_merchant_suggestions_are_owned_confirmed_and_never_authoritative(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        for day in ['2026-01-02', '2026-02-02', '2026-03-02']:
            e = seed_entry(db, owner, account, -10000, 'purchase', day)
            ledger.split(db, owner.id, e.id, Split(**op(e.revision, components=[
                {'category': 'purchase', 'amount_paise': -10000, 'budget_category': 'grocery'}])))
        latest = seed_entry(db, owner, account, -10000, 'unknown', '2026-04-02')
        suggestion = store.category_suggestions(db, owner.id)
        assert len(suggestion) == 1 and suggestion[0]['entry_id'] == latest.id
        assert suggestion[0]['budget_category'] == 'grocery'
        assert db.get(LedgerEntry, latest.id).components[0]['category'] == 'unknown'
        assert store.category_suggestions(db, owner.id+1) == []


def test_positive_rollover_preview_never_hides_overspend_or_rewrites_source(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        job = imported(db, owner, account)
        publish(db, owner, job)
        e = db.query(LedgerEntry).filter_by(reference='EXP-1').one()
        ledger.split(db, owner.id, e.id, Split(**op(e.revision, components=[
            {'category': 'purchase', 'amount_paise': -450000, 'budget_category': 'grocery'},
            {'category': 'purchase', 'amount_paise': -5050000, 'budget_category': 'other'}])))
        budget = store.write(db, owner.id, 'budget', write(p.BudgetWrite,
            {'month': '2026-01', 'lines': {'grocery': 500000}, 'rollover': 'positive'}))
        current = report(db, owner, account)
        preview = store.copy_budget(db, owner.id, budget['id'], '2026-02', current['id'])
        assert preview['preview']['lines']['grocery'] == 550000
        assert store.get(db, owner.id, 'budget', budget['id']).data['lines']['grocery'] == 500000
        with pytest.raises(HTTPException) as exc:
            store.copy_budget(db, owner.id, budget['id'], '2026-02')
        assert exc.value.status_code == 422


def test_settlement_race_cannot_spend_one_transaction_on_two_bills(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        bills = [store.write(db, owner.id, 'obligation', write(p.ObligationWrite,
            {'label': 'Confirmed synthetic bill', 'amount_paise': 10000, 'due_date': '2026-01-05'})) for _ in range(2)]
        entry = seed_entry(db, owner, account, -10000, 'purchase')
        owner_id, entry_id = owner.id, entry.id
    barrier = Barrier(2)
    def attempt(bill):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return store.write(db, owner_id, 'settlement', write(p.SettlementWrite,
                    {'obligation_id': bill['id'], 'expected_obligation_revision': 1,
                     'entry_id': entry_id, 'expected_entry_revision': 1}))['revision']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, bills)) == [1, 409]


def test_aggregate_overflow_and_implicit_opt_in_are_rejected(client):
    from backend.core.money import MAX_PAISE
    a = auth(client)
    response = client.post('/budgets', headers=a, json=dict(expected_revision=0, idempotency_key='overflow-budget',
        reason='Synthetic overflow', data={'month': '2026-01', 'lines': {'a': MAX_PAISE, 'b': 1}}))
    assert response.status_code == 422, response.text
    with client.session_factory() as db:
        assert db.query(PlanningRevision).count() == 0
    response = client.post('/obligations', headers=a, json=dict(expected_revision=0, idempotency_key='bad-opt-in',
        reason='Synthetic invalid input', data={'label': 'Bill', 'amount_paise': 1, 'due_date': '2026-01-01', 'reminder_opt_in': 'yes'}))
    assert response.status_code == 422


def test_verified_month_comparison_uses_owned_immutable_prior_report(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        january = imported(db, owner, account)
        publish(db, owner, january)
        february_content = load().replace(b'2026-01-31', b'2026-02-28').replace(b'2026-01-', b'2026-02-').replace(
            b'20000.00,10000.00', b'20000.00,30000.00').replace(b'45000.00', b'65000.00').replace(b'SAL-1', b'SAL-FEB').replace(b'EXP-1', b'EXP-FEB')
        february = imported(db, owner, account, february_content)
        publish(db, owner, february)
        first = report(db, owner, account)
        second = reports.create(db, owner.id, ReportCreate(month='2026-02', account_ids=[account.id], expected_vector=reports.vector(db, owner.id)))
        assert second['snapshot']['comparison'] == {'status': 'available', 'previous_report_id': first['id'],
            'reason': None, 'changes_paise': {'income_paise': 2000000, 'spending_paise': 0, 'recognized_surplus_paise': 2000000}}


def test_preexisting_v1_csv_bytes_remain_reproducible(db_engine):
    with Session(db_engine) as db:
        owner, account = setup(db)
        legacy = MonthlyReport(id='legacy-report', user_id=owner.id, month='2026-01', rule_version='ledger.v1',
            vector={}, snapshot={'sources': [{'entry_id': 'source', 'posting_date': '2026-01-01',
                'amount_paise': -100, 'description': '=synthetic formula'}]})
        db.add(legacy)
        db.commit()
        assert reports.export_csv(db, owner.id, legacy.id) == (
            'report_id,rule_version,entry_id,posting_date,amount_paise,description\r\n'
            "legacy-report,ledger.v1,source,2026-01-01,-100,'=synthetic formula\r\n")
