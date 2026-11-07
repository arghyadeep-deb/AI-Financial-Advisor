"""Offline lane E acceptance. Expected amounts are independent hand calculations."""
import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import pytest
from alembic import command
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from backend.core.migrations_runner import _alembic_cfg
from backend.models.models import PortfolioRevision, AllocationPlan
from backend.schemas.portfolio import HoldingsWrite, SuitabilityWrite, CSVPreview, AllocationScenario
from backend.services import portfolio_service as store, allocation_service as allocation
from engines.allocation.costs import rebalance
from engines.allocation.contracts import Holding
from engines.portfolio import metrics, Position
from engines.portfolio.returns import xirr, time_weighted
from engines.tax.sample_packs import load_pack, calculate, SampleCase, SamplePack, stale
from tests.allocation.test_allocation import seed, answers
from tests.test_stage_c_statements import synthetic_config

DAY = date(2026, 11, 7)


@pytest.fixture(autouse=True)
def fixed_day(monkeypatch):
    monkeypatch.setattr(store, 'today', lambda: DAY)


def observation(**change):
    return {**dict(account_ref='folio-A', instrument_id='synthetic-A', issuer_id='issuer-A',
        asset_class='equity', units='2.5', observation_date=DAY.isoformat(),
        price_paise=40000, price_date=DAY.isoformat(), price_source='owner-price',
        price_version=1, price_expires='2026-11-08', cost_basis_paise=80000,
        corporate_actions_supported=True), **change}


def book(rev=0, key=None, **change):
    data = {**dict(confirmed=True, source='manual', as_of=DAY.isoformat(), inventory_complete=True,
                  observations=[observation()]), **change}
    return HoldingsWrite(expected_revision=rev, idempotency_key=key or uuid4().hex, reason='Owner reviewed', data=data)


def save_inputs(db):
    seed(db)
    store.write(db, 1, 'holdings', book())
    store.write(db, 1, 'suitability', SuitabilityWrite(expected_revision=0, idempotency_key=uuid4().hex,
        reason='Answers confirmed', data=answers()))


def scenario(**changes):
    return AllocationScenario(**{**dict(expected_revision=0, idempotency_key=uuid4().hex,
        reason='Compare hypothetical classes', expected_profile_revision=1, expected_holdings_revision=1,
        expected_suitability_revision=1, expected_planning_vector={}, assumptions_accepted=True,
        eligible_liquid_paise=450000), **changes})


def test_holdings_arithmetic_history_closure_retry_and_no_inference(db_engine):
    with Session(db_engine) as db:
        seed(db)
        with pytest.raises(HTTPException) as err:
            store.get(db, 1, 'holdings')
        assert err.value.status_code == 404  # profile investment amount establishes no units
        request = book()
        first = store.write(db, 1, 'holdings', request)
        assert store.write(db, 1, 'holdings', request) == first
        values = store.valuation(db, 1, DAY)
        assert values['total_value_paise'] == 100000  # 2.5 * 40000
        assert values['absolute_gain_paise'] == 20000
        assert values['issuer_hhi'] == '1'
        assert values['verification'] == 'owner_confirmed_unverified'
        assert not values['verified_net_worth_eligible']
        with pytest.raises(HTTPException) as err:
            store.write(db, 1, 'holdings', book(key=request.idempotency_key, inventory_complete=False))
        assert err.value.status_code == 409
        with pytest.raises(HTTPException) as err:
            store.write(db, 1, 'holdings', book())
        assert err.value.status_code == 409
        store.write(db, 1, 'holdings', book(1, observations=[observation(closed=True, units='0')]))
        assert store.valuation(db, 1, DAY)['total_value_paise'] == 0  # explicitly confirmed closed inventory
        assert store.valuation(db, 1, DAY, 1)['total_value_paise'] == 100000
        with pytest.raises(Exception, match='immutable'):
            db.execute(text('UPDATE portfolio_revisions SET revision=100'))
        db.rollback()


def test_overlap_account_scope_and_fractional_group_conservation():
    with pytest.raises(ValidationError, match='Overlapping'):
        book(observations=[observation(), observation()])
    # Same security in different folios is distinct; duplicate CSV/manual rows in same folio refuse.
    assert len(book(observations=[observation(), observation(account_ref='folio-B')]).data.observations) == 2
    positions = tuple(Position(observation_id=str(i), instrument_id=str(i), units=Decimal('.5'),
        price_paise=1, price_date=DAY, expires=DAY+timedelta(days=1), source_id='synthetic',
        source_version=1, asset_class=a, issuer_id=str(i)) for i, a in enumerate(('equity', 'debt')))
    result = metrics(positions, as_of=DAY)
    assert result['total_value_paise'] == 1
    assert sum(result['asset_class_paise'].values()) == 1
    assert sum(result['issuer_paise'].values()) == 1


@pytest.mark.parametrize('change', [dict(price_paise=None), dict(price_date='2026-11-08', price_expires='2026-11-09'),
    dict(price_date='2026-11-06', price_expires='2026-11-07'), dict(price_source=None), dict(price_version=None)])
def test_missing_stale_unverified_quotes_never_become_zero(db_engine, change):
    with Session(db_engine) as db:
        seed(db)
        store.write(db, 1, 'holdings', book(observations=[observation(**change)]))
        result = store.valuation(db, 1, DAY)
        assert result['total_value_paise'] is None
        assert result['status'] == 'unavailable'
        assert result['absolute_gain_paise'] is None


@pytest.mark.parametrize('change', [dict(units='NaN'), dict(units='garbage'), dict(units='Infinity'), dict(units='-1'),
    dict(units='0.000000001'), dict(price_paise=True), dict(price_paise=1.1),
    dict(price_paise=10**14), dict(currency='USD'), dict(closed=True)])
def test_invalid_observations_refuse(change):
    with pytest.raises(ValidationError):
        book(observations=[observation(**change)])


def test_csv_preview_requires_confirmation_and_exact_header():
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=store.CSV_COLUMNS)
    writer.writeheader()
    row = observation()
    writer.writerow({k: row.get(k, '') for k in store.CSV_COLUMNS})
    payload = CSVPreview(csv_text=output.getvalue(), as_of=DAY)
    result = store.csv_preview(payload)
    assert result['persisted'] is False and result['status'] == 'requires_owner_confirmation'
    assert result['preview']['source'] == 'csv'
    assert 'confirmed' not in result['preview']
    for bad in ('garbage\na', '"unterminated', output.getvalue()+output.getvalue().splitlines()[-1]+'\n'):
        with pytest.raises(HTTPException) as err:
            store.csv_preview(CSVPreview(csv_text=bad, as_of=DAY))
        assert err.value.status_code == 422


def test_asset_class_rebalance_golden_no_unknown_tax_claim():
    result = rebalance((Holding(asset='equity', value_paise=80000), Holding(asset='cash', value_paise=20000)),
        10000, {'cash': 2000, 'debt': 3000, 'equity': 5000})
    assert result['target_paise'] == {'cash': 22000, 'debt': 33000, 'equity': 55000}
    assert result['contribution_first']['additions_paise'] == {'cash': 2000, 'debt': 8000, 'equity': 0}
    assert result['sale_alternative']['delta_paise'] == {'cash': 2000, 'debt': 33000, 'equity': -25000}
    assert result['sale_alternative']['sales_paise'] == 25000
    assert result['tax_cost_paise'] is None and result['net_improvement'] is None
    assert sum(result['contribution_first']['result_paise'].values()) == 110000


def test_owned_allocation_fencing_replay_stale_and_gate(db_engine, monkeypatch):
    with Session(db_engine) as db:
        save_inputs(db)
        with pytest.raises(HTTPException) as err:
            allocation.create_owned_scenario(db, 1, scenario())
        assert err.value.status_code == 404
        monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
        request = scenario()
        result = allocation.create_owned_scenario(db, 1, request)
        assert result['status'] == 'hypothetical' and not result['stale']
        assert result['allocation']['status'] == 'feasible'
        assert not result['public_eligible'] and not result['named_products_eligible']
        assert result['rebalance']['status'] == 'hypothetical'
        assert allocation.create_owned_scenario(db, 1, request)['id'] == result['id']
        assert db.query(AllocationPlan).count() == 1
        for changes in ({'expected_holdings_revision': 9}, {'expected_suitability_revision': 9},
                        {'expected_profile_revision': 9}, {'expected_planning_vector': {'missing': 1}}):
            with pytest.raises(HTTPException) as err:
                allocation.create_owned_scenario(db, 1, scenario(**changes))
            assert err.value.status_code == 409
        with pytest.raises(HTTPException) as err:
            allocation.create_owned_scenario(db, 1, scenario(idempotency_key=request.idempotency_key, eligible_liquid_paise=1))
        assert err.value.status_code == 409
        store.write(db, 1, 'holdings', book(1, observations=[observation(price_paise=30000, price_version=2)]))
        old = allocation.read_owned_plan(db, 1, result['id'])
        assert old['stale'] and 'holdings_changed' in old['stale_reasons']
        assert old['inputs']['holdings']['observations'][0]['price_paise'] == 40000
        for identity in (result['id'], 'missing'):
            with pytest.raises(HTTPException) as err:
                allocation.read_owned_plan(db, 2, identity)
            assert (err.value.status_code, err.value.detail) == (404, 'Allocation plan not found')


def test_registry_export_purge_is_scoped_and_idempotent(db_engine):
    from backend.core.owned_stores import _registry, validate_coverage
    validate_coverage()
    with Session(db_engine) as db:
        save_inputs(db)
        store.write(db, 2, 'holdings', book())
        assert len(_registry['portfolio'].export(db, 1)['portfolio_revisions']) == 2
        for _ in range(2):
            _registry['portfolio'].purge(db, 1)
            db.commit()
        assert db.query(PortfolioRevision).filter_by(user_id=1).count() == 0
        assert db.query(PortfolioRevision).filter_by(user_id=2).count() == 1


def test_migration_roundtrip_model_sync_and_populated_refusal(tmp_path):
    url = f"sqlite:///{(tmp_path/'migration.db').as_posix()}"
    cfg = _alembic_cfg(url)
    command.upgrade(cfg, '0110')
    command.upgrade(cfg, '0120')
    engine = create_engine(url)
    assert {c['name'] for c in inspect(engine).get_columns('portfolio_revisions')} == set(PortfolioRevision.__table__.columns.keys())
    command.downgrade(cfg, '0110')
    assert 'portfolio_revisions' not in inspect(engine).get_table_names()
    command.upgrade(cfg, '0120')
    with Session(engine) as db:
        seed(db)
        store.write(db, 1, 'holdings', book())
    with pytest.raises(RuntimeError, match='evidence exists'):
        command.downgrade(cfg, '0110')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT COUNT(*) FROM portfolio_revisions')).scalar_one() == 1
    engine.dispose()


def test_returns_independent_dated_examples_and_abstention():
    # Exactly 365 days, -100 rupees to 110: 10% annualized.
    flows = ((date(2025, 1, 1), -10000), (date(2026, 1, 1), 11000))
    assert Decimal(xirr(flows, corporate_actions_supported=True)['annual_rate']) == Decimal('.1')
    assert xirr(flows, corporate_actions_supported=False)['status'] == 'unavailable'
    assert xirr(((DAY, -100), (DAY+timedelta(days=1), 0)), corporate_actions_supported=True)['status'] == 'unavailable'
    assert xirr(((date(2024,1,1), -100), (date(2025,1,1), 200), (date(2026,1,1), -100)), corporate_actions_supported=True)['status'] == 'unavailable'
    # 10% then 10% after external end-flow adjustment -> 21%, exact fraction 21/100.
    assert time_weighted(((10000, 12000, 1000), (12000, 13200, 0)), evidence_complete=True)['return_fraction'] == '21/100'
    assert time_weighted(((0, 100, 0),), evidence_complete=True)['status'] == 'unavailable'


PACK = Path(__file__).resolve().parents[1] / 'knowledge_base/tax/sample-v1.json'


def sample_case(**changes):
    return SampleCase(**{**dict(period='SAMPLE-2026', regime='sample', resident=True, employer_count=1,
        salary_paise=260000, withholding_paise=10000, evidence_complete=True, input_revision=1), **changes})


def sample_pack():
    return load_pack(PACK, expected_sha256=sha256(PACK.read_bytes()).hexdigest())


@pytest.mark.parametrize('salary,tax', [(0,0),(110000,0),(110001,0),(210000,10100),(210005,10101),(260000,20200)])
def test_sample_tax_goldens(salary, tax):
    # Deduct invented 10k; first invented 100k zero, next 100k at 10%, rest 20%; 1% supplement.
    result = calculate(sample_case(salary_paise=salary), sample_pack(), as_of=DAY)
    assert result['tax_paise'] == tax
    assert result['synthetic_only'] and result['status'] == 'synthetic_sample'
    assert not result['filing_enabled'] and not result['production_approved']


@pytest.mark.parametrize('changes,status', [(dict(period='2026-27'),'unsupported'), (dict(regime='new'),'unsupported'),
    (dict(other_income=('capital_gain',)),'unsupported'), (dict(employer_count=2),'unsupported'),
    (dict(conflicts=('identity',)),'needs_review'), (dict(conflicts=('income','withholding')),'needs_review'),
    (dict(evidence_complete=False),'needs_review'), (dict(salary_paise=2000000),'unsupported')])
def test_sample_tax_scope_and_conflicts(changes,status):
    result = calculate(sample_case(**changes), sample_pack(), as_of=DAY)
    assert result['status'] == status and result['tax_paise'] is None


def test_sample_pack_integrity_expiry_refresh_and_missing_withholding(tmp_path):
    pack = sample_pack()
    with pytest.raises(ValueError, match='hash'):
        load_pack(PACK, expected_sha256='0'*64)
    for change in ({'production_approved': True}, {'synthetic_only': False}, {'period': '2026-27'},
                   {'slabs': list(reversed(json.loads(PACK.read_text())['slabs']))}):
        raw = {**json.loads(PACK.read_text()), **change}
        with pytest.raises(ValidationError):
            SamplePack.model_validate_json(json.dumps(raw))
    case = sample_case(withholding_paise=None)
    result = calculate(case, pack, as_of=DAY)
    assert result['balance_payable_paise'] is None and result['refund_paise'] is None
    assert not stale(result, case, pack, as_of=DAY)
    revised = SamplePack.model_validate_json(pack.model_dump_json().replace('sample.salary.v1', 'sample.salary.v2'))
    assert stale(result, case, revised, as_of=DAY)
    assert stale(result, sample_case(input_revision=2), pack, as_of=DAY)
    assert calculate(case, pack, as_of=date(2027,1,1))['status'] == 'needs_review'


def test_api_owned_history_hypothetical_deficit_and_gate(client, monkeypatch):
    from tests.api.test_tenancy import signup, PROFILE
    a, b = signup(client), signup(client)
    profile = {**PROFILE, 'monthly_income': 45000, 'monthly_expenses': 55000,
               'existing_savings': 30000, 'existing_investments': 80000, 'existing_debts': 0}
    assert client.post('/profile', headers=a, json=profile).status_code == 200
    # No holdings inferred from declared investments, bank flows, analysis or a model.
    assert client.get('/portfolio/holdings', headers=a).status_code == 404
    result = client.post('/portfolio/holdings', headers=a, json=book().model_dump(mode='json'))
    assert result.status_code == 200, result.text
    first = result.json()
    missing = client.get('/portfolio/holdings?revision=999', headers=b)
    foreign = client.get('/portfolio/holdings?revision=1', headers=b)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()['message'] == missing.json()['message']
    result = client.post('/portfolio/scenarios', headers=a, json={
        'expected_revision': 1, 'as_of': DAY.isoformat(), 'shock_bps': -2000, 'contribution_paise': 999999})
    assert result.status_code == 200, result.text
    assert result.json()['status'] == 'hypothetical'
    assert result.json()['shock']['scenario_value_paise'] == 80000
    assert result.json()['verified_affordable_contribution_paise'] == 0
    assert result.json()['chosen_contribution_paise'] == 999999
    assert client.get('/portfolio/holdings', headers=a).json() == first
    suit = SuitabilityWrite(expected_revision=0, idempotency_key=uuid4().hex, reason='Confirmed', data=answers())
    assert client.post('/portfolio/suitability', headers=a, json=suit.model_dump(mode='json')).status_code == 200
    assert client.post('/allocation-scenarios', headers=a, json=scenario().model_dump(mode='json')).status_code == 404
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    result = client.post('/allocation-scenarios', headers=a, json=scenario().model_dump(mode='json'))
    assert result.status_code == 200, result.text
    plan = result.json()
    assert plan['allocation']['status'] == 'infeasible'
    assert plan['rebalance']['status'] == 'unavailable'
    assert client.get('/allocation-plans/'+plan['id'], headers=b).status_code == 404
    assert client.get('/allocation-plans/missing', headers=b).json()['message'] == client.get('/allocation-plans/'+plan['id'], headers=b).json()['message']
    monkeypatch.setenv('NAMED_PRODUCT_RECOMMENDATIONS', 'true')
    assert client.post('/allocation-proposals', headers=a, json={'public_eligible': True}).json()['status'] == 'gated'
    monkeypatch.setenv('APP_ENV', 'production')
    assert client.post('/allocation-scenarios', headers=a, json=scenario().model_dump(mode='json')).status_code == 404


def test_api_invalid_confirmation_future_and_aggregate_bounds(client):
    from tests.api.test_tenancy import signup
    owner = signup(client)
    for change in ({'confirmed': False}, {'confirmed': 1}, {'confirmed': 'true'},
                   {'observations': [observation(units='garbage')]},
                   {'as_of': '2027-01-01', 'observations': [observation(observation_date='2027-01-01')]}):
        raw = book().model_dump(mode='json')
        raw['data'].update(change)
        assert client.post('/portfolio/holdings', headers=owner, json=raw).status_code == 422
    raw = book(observations=[observation(units='1000000000000', price_paise=10**13)]).model_dump(mode='json')
    assert client.post('/portfolio/holdings', headers=owner, json=raw).status_code == 422
    assert client.get('/portfolio/holdings', headers=owner).status_code == 404


def test_real_concurrent_holdings_CAS_and_allocation_replay(db_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    with Session(db_engine) as db:
        save_inputs(db)
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    request = scenario()
    barrier = Barrier(2)
    def allocate_once(_):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return allocation.create_owned_scenario(db, 1, request)['id']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(allocate_once, range(2)))
    assert result[0] == result[1] and isinstance(result[0], str)
    barrier = Barrier(2)
    def correct(_):
        with Session(db_engine) as db:
            barrier.wait(timeout=10)
            try:
                return store.write(db, 1, 'holdings', book(1))['revision']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(correct, range(2))) == [2, 409]
    with Session(db_engine) as db:
        assert db.query(AllocationPlan).count() == 1
        assert allocation.read_owned_plan(db, 1, result[0])['stale']


def test_all_material_vectors_and_expiry_invalidate(db_engine, monkeypatch):
    from backend.models.models import FinancialProfile, PlanningRevision
    with Session(db_engine) as db:
        save_inputs(db)
        monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
        original = allocation.create_owned_scenario(db, 1, scenario())
        # Suitability changes are owned immutable answers, never trusted request revisions.
        store.write(db, 1, 'suitability', SuitabilityWrite(expected_revision=1, idempotency_key=uuid4().hex,
            reason='Changed horizon', data=answers(revision=2, horizon_months=36)))
        assert 'suitability_changed' in allocation.read_owned_plan(db, 1, original['id'])['stale_reasons']
        db.query(FinancialProfile).filter_by(user_id=1).update({'revision': 2})
        db.add(PlanningRevision(id=uuid4().hex, user_id=1, kind='goal', resource_id='goal', revision=1,
            operation_key=uuid4().hex, request={}, data={}))
        db.commit()
        old = allocation.read_owned_plan(db, 1, original['id'])
        assert {'planning_changed', 'profile_changed'} <= set(old['stale_reasons'])
        monkeypatch.setattr(store, 'today', lambda: date(2027,1,1))
        old = allocation.read_owned_plan(db, 1, original['id'])
        assert {'valuation_date_changed','assumptions_changed_or_expired'} <= set(old['stale_reasons'])
        val = store.valuation(db, 1)
        assert val['stale'] and val['total_value_paise'] is None


def test_declared_incomplete_inventory_blocks_rebalance(db_engine, monkeypatch):
    with Session(db_engine) as db:
        save_inputs(db)
        store.write(db, 1, 'holdings', book(1, inventory_complete=False))
        monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
        result = allocation.create_owned_scenario(db, 1, scenario(expected_holdings_revision=2))
        assert result['comparison']['current_value_paise'] is None
        assert result['rebalance']['status'] == 'unavailable'


def test_held_out_rebalance_family():
    cases = json.loads((Path(__file__).resolve().parents[1]/'evals/allocation/stage-e-held-out-v1.json').read_text())
    for case in cases:
        holdings = tuple(Holding(asset=a, value_paise=n) for a,n in case['holdings'].items())
        first = rebalance(holdings, case['contribution'], case['target_bps'])
        assert first == rebalance(holdings, case['contribution'], case['target_bps'])
        assert first['target_paise'] == case['expected_target']
        assert first['contribution_first']['additions_paise'] == case['expected_additions']
        assert first['sale_alternative']['sales_paise'] == case['expected_sales']


def test_shared_FIN14_capacity_and_goals_are_not_reimplemented(db_engine, monkeypatch):
    from tests.test_stage_c_statements import setup
    from tests.test_stage_d import positive_report, future, write, report as make_report
    from backend.models.models import FinancialProfile
    from backend.schemas import planning as p
    from backend.services import planning_service as planning
    with Session(db_engine) as db:
        owner, account = setup(db)
        db.add(FinancialProfile(user_id=owner.id, revision=1, monthly_income_paise=6500000,
            monthly_expenses_paise=5500000, existing_savings_paise=33000000,
            existing_investments_paise=0, existing_debts_paise=0, monthly_credit_spend_paise=0))
        db.commit()
        store.write(db, owner.id, 'holdings', book())
        store.write(db, owner.id, 'suitability', SuitabilityWrite(expected_revision=0, idempotency_key=uuid4().hex,
            reason='Confirmed', data=answers()))
        planning.write(db, owner.id, 'obligation', write(p.ObligationWrite,
            {'label': 'Principal payment', 'amount_paise': 400000, 'due_date': date.today()}))
        report = positive_report(db, owner, account)
        monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
        vector = planning.vector(db, owner.id)
        # Historical surplus or a profile cap cannot bypass existing obligations.
        blocked = allocation.create_owned_scenario(db, owner.id, scenario(expected_planning_vector=vector))
        assert blocked['allocation']['status'] == 'insufficient_data'
        cap = p.GoalPlan(**future(db, owner, report['id']), as_of=DAY)
        result = allocation.create_owned_scenario(db, owner.id, scenario(expected_planning_vector=vector, planning_capacity=cap))
        # 6,500,000 - 5,500,000 - 400,000 - 300,000 = 300,000 paise.
        assert result['inputs']['planning_capacity']['capacity']['available_paise'] == 300000
        assert result['allocation']['budget_paise'] == 300000
        assert not result['stale']
        # Reserve all remaining capacity for an already confirmed goal, leaving none for allocation.
        planning.write(db, owner.id, 'goal', write(p.GoalWrite, {'label':'Goal', 'target_paise':3600000,
            'target_date': date.today().replace(year=date.today().year+1), 'funding_account_id': account.id}))
        report = make_report(db, owner, account)
        cap = p.GoalPlan(**future(db, owner, report['id']), as_of=DAY)
        result = allocation.create_owned_scenario(db, owner.id, scenario(expected_planning_vector=planning.vector(db, owner.id), planning_capacity=cap))
        assert result['inputs']['planning_capacity']['unallocated_capacity_paise'] == 0
        assert result['allocation']['status'] == 'infeasible'


def test_private_export_delete_restore_and_metadata_only_telemetry(db_engine, tmp_path, monkeypatch):
    from backend.services.auth_service import AuthService
    from backend.services.privacy.lifecycle import export_owned, delete_owned, SuppressionJournal
    from backend.core.telemetry import events, ALLOWED_META_KEYS
    from backend.models.models import User
    with Session(db_engine) as db:
        credentials = AuthService(db).signup('owner-e@example.test', 'Synthetic', 'Safe-fictional-pass-987')
        owner = db.get(User, credentials['user_id'])
        store.write(db, owner.id, 'holdings', book())
        store.write(db, owner.id, 'suitability', SuitabilityWrite(expected_revision=0, idempotency_key=uuid4().hex,
            reason='Confirmed', data=answers()))
        db.add(AllocationPlan(id=uuid4().hex, user_id=owner.id, profile_revision=1, suitability_revision=1,
            input_snapshot={'private_fixture': 'synthetic-A'}, result={'status': 'hypothetical'}))
        db.commit()
        exported = export_owned(db, owner, 'Safe-fictional-pass-987')
        assert len(exported['stores']['portfolio']['portfolio_revisions']) == 2
        assert len(exported['stores']['allocation']['allocation_plans']) == 1
        assert 'hashed_password' not in json.dumps(exported, default=str)
        spans = [event for event in events if event['node'] == 'portfolio_revision']
        assert spans and all(set(event) <= set(ALLOWED_META_KEYS) for event in spans)
        assert 'synthetic-A' not in json.dumps(spans)
        journal = SuppressionJournal(tmp_path/'separate-journal.db')
        assert delete_owned(db, owner, 'Safe-fictional-pass-987', journal)['status'] == 'live_complete'
        assert db.query(PortfolioRevision).count() == 0
        assert db.query(AllocationPlan).count() == 0
        assert journal.contains(owner.id)
        # Simulated old backup rows remain owned by a suppressed account after restore replay.
        db.add(PortfolioRevision(id=uuid4().hex, user_id=owner.id, kind='holdings', revision=1,
            operation_key=uuid4().hex, request={}, data=book().data.model_dump(mode='json')))
        owner.is_active = True
        db.commit()
        journal.replay(db)
        with pytest.raises(HTTPException) as err:
            store.write(db, owner.id, 'holdings', book(1))
        assert err.value.status_code == 409


def test_missing_current_inputs_or_assumptions_preserve_history(db_engine, monkeypatch):
    from backend.models.models import FinancialProfile
    from backend.finance import allocation_sources
    with Session(db_engine) as db:
        save_inputs(db)
        monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
        result = allocation.create_owned_scenario(db, 1, scenario())
        with monkeypatch.context() as patch:
            from dataclasses import replace
            import engines.portfolio as portfolio_engine
            patch.setattr(portfolio_engine, 'RULES', replace(portfolio_engine.RULES, version='synthetic-next-version'))
            assert 'portfolio_rules_changed' in allocation.read_owned_plan(db, 1, result['id'])['stale_reasons']
        with monkeypatch.context() as patch:
            patch.setattr(allocation_sources, 'synthetic_fixture', lambda *args: (_ for _ in ()).throw(ValueError('invalid pack')))
            old = allocation.read_owned_plan(db, 1, result['id'])
            assert old['stale_reasons'] == ['assumptions_unavailable']
            assert old['inputs'] == result['inputs']
            with pytest.raises(HTTPException) as err:
                allocation.create_owned_scenario(db, 1, scenario())
            assert err.value.status_code == 503
        db.query(FinancialProfile).filter_by(user_id=1).update({'monthly_income_paise': None})
        db.commit()
        old = allocation.read_owned_plan(db, 1, result['id'])
        assert old['stale_reasons'] == ['current_inputs_unavailable']
        assert old['inputs'] == result['inputs']


def test_review_fixes_dated_total_survives_expiry_and_scenario_uses_checked_revision():
    from datetime import date
    from types import SimpleNamespace
    from unittest.mock import patch
    from backend.services import portfolio_service as p
    from backend.schemas.portfolio import ShockRequest

    def book(price):
        return dict(confirmed=True, source='manual', as_of='2026-11-07', inventory_complete=True, observations=[dict(
            account_ref='a', instrument_id='i', units='1', observation_date='2026-11-07', price_paise=price,
            price_date='2026-11-07', price_source='owner', price_version=1, price_expires='2026-11-08')])

    later = p.valuation_data(book(10000), date(2026, 11, 9))
    assert later['dated_total_value_paise'] == 10000 and later['total_value_paise'] is None

    def get(db, owner, kind, revision=None):
        return SimpleNamespace(revision=revision or 1, data=book(10000 if (revision or 1) == 1 else 20000))
    with patch.object(p, 'get', side_effect=get), patch.object(p, 'today', return_value=date(2026, 11, 7)), \
            patch('backend.services.finance_snapshot_service.current_snapshot', return_value=None):
        out = p.scenario(None, 1, ShockRequest(expected_revision=1, as_of=date(2026, 11, 7), shock_bps=0))
    assert out['holdings_revision'] == out['observed']['holdings_revision'] == 1
