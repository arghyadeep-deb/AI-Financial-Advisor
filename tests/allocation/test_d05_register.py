"""D05 synthetic fixtures; no market evidence or real recommendations."""
from datetime import date
import json
import pytest
from pydantic import ValidationError
from backend.finance.allocation_assumptions import AssumptionRegister, load_register
from backend.finance.allocation_sources import synthetic_fixture
from backend.services.allocation_service import propose
from engines.allocation import allocate, evidence_current
from engines.allocation.contracts import AssumptionPack, Constraints
from tests.allocation.test_allocation import DAY, answers, snapshot


def test_register_metadata_and_expiry():
    register = load_register()
    assert register.version and not register.validated(DAY)
    for a in register.assumptions:
        assert a.source.name and a.source.url and a.source.publisher
        assert a.methodology and a.uncertainty and a.version
        assert a.current(DAY) and not a.current(a.expires)
        assert not a.current(date(2026, 1, 1))
        assert a.status == 'unvalidated_prototype'
    data = register.model_dump(mode='json')
    data['assumptions'].append(data['assumptions'][0])
    with pytest.raises(ValidationError, match='duplicate'):
        AssumptionRegister.model_validate_json(json.dumps(data))


def test_unvalidated_recommendation_refused_even_with_synthetic_pack(monkeypatch):
    pack, registry = synthetic_fixture('v2')
    result = allocate(snapshot(), answers(), pack, Constraints(eligible_liquid_paise=10000),
                      registry, owner_id=1, as_of=DAY)
    assert result.status == 'gated' and result.reasons == ('assumptions not validated',)
    assert not result.amounts
    assert 'assumptions not validated' in propose()['reasons']
    monkeypatch.setenv('APP_ENV', 'development')
    with pytest.raises(ValueError, match='test fixtures only'):
        synthetic_fixture('v2')
    assert allocate(snapshot(), answers(), pack, Constraints(eligible_liquid_paise=10000),
                    registry, owner_id=1, as_of=DAY, synthetic_test=True).status == 'gated'


def test_register_per_scalar_integrity_and_individual_expiry():
    pack, registry = synthetic_fixture('v2')
    assert all(a.status == 'synthetic_test' for a in pack.register.assumptions)
    data = pack.model_dump(mode='json')
    data['register']['assumptions'].pop()
    with pytest.raises(ValidationError, match='every parameter'):
        AssumptionPack.model_validate_json(json.dumps(data))
    expired = pack.register.assumptions[0].model_copy(update={'expires': DAY})
    changed = pack.model_copy(update={'register': pack.register.model_copy(update={
        'assumptions': (expired, *pack.register.assumptions[1:])})})
    assert not evidence_current(changed, registry, 1, DAY)


def test_authenticated_read_register(client):
    assert client.get('/allocation-assumptions').status_code == 401
    from tests.api.test_tenancy import signup
    response = client.get('/allocation-assumptions', headers=signup(client))
    assert response.status_code == 200
    assert response.json()['assumptions'] == load_register().model_dump(mode='json')['assumptions']
    assert response.json()['recommendation_status'] == 'assumptions not validated'
    assert response.json()['public_eligible'] is False


def test_configurable_prototype_floor_and_near_term_label():
    pack, registry = synthetic_fixture('v2')
    def run(**kw):
        return allocate(snapshot(), answers(loss_tolerance='low', horizon_months=24), pack,
            Constraints(eligible_liquid_paise=10000, **kw), registry,
            owner_id=1, as_of=DAY, synthetic_test=True)
    assert next(h.value_paise for h in run().amounts if h.asset == 'equity') == 0
    custom = run(near_term_months=12, liquidity_floor_bps=9000)
    assert custom.status == 'feasible' and custom.policy_status == 'unvalidated_prototype'
    assert next(h.value_paise for h in custom.amounts if h.asset == 'cash') >= 9000
    assert next(h.value_paise for h in run(near_term_months=12).amounts if h.asset == 'equity') > 0
    assert custom.policy_configuration == {
        'cash_floor_bps': 9000, 'near_term_months': 12}
    assert all(a.status == 'unvalidated_prototype' for a in custom.policy_assumptions)
    assert not answers(horizon_months=24).blockers(near_term_months=12)
    assert answers(horizon_months=24).assessment()['policy_status'] == 'unvalidated_prototype'



def test_unknown_liquidity_never_meets_deadline():
    pack, registry = synthetic_fixture('v2')
    result = allocate(snapshot(), answers(), pack,
        Constraints(eligible_liquid_paise=10000, maximum_liquidity_days=3650),
        registry, owner_id=1, as_of=DAY, synthetic_test=True)
    assert result.status == 'infeasible' and not result.amounts
    assert set(result.liquidity_days.values()) == {None}
    assert 'Unknown liquidity' in result.liquidity_explanation
    data = pack.model_dump(mode='json')
    data['assets'][0]['liquidity_days'] = 0
    with pytest.raises(ValidationError, match='evidence'):
        AssumptionPack.model_validate_json(json.dumps(data))


def signed_pack(data, source):
    # Synthetic source revision: ensure failures below test expiry, not hash tampering.
    from hashlib import sha256
    from backend.knowledge.registry import Registry
    data.pop('source_hash', None)
    text = json.dumps(data)
    digest = sha256(text.encode()).hexdigest()
    pack = AssumptionPack.model_validate_json(json.dumps({**data, 'source_hash': digest}))
    return pack, Registry((source.model_copy(update={'text': text, 'content_hash': digest}),),
                          frozenset({'example.test'}))


def test_individual_expiry_with_matching_source():
    pack, registry = synthetic_fixture('v2')
    source = registry.retrieve('allocation', owner_id=1, as_of=DAY)[0]
    data = pack.model_dump(mode='json')
    data['register']['assumptions'][0]['expires'] = DAY.isoformat()
    data['register']['assumptions'][0]['as_of'] = '2026-11-06'
    pack, registry = signed_pack(data, source)
    assert not evidence_current(pack, registry, 1, DAY)
    result = allocate(snapshot(), answers(), pack, Constraints(eligible_liquid_paise=10000),
                      registry, owner_id=1, as_of=DAY, synthetic_test=True)
    assert result.status == 'insufficient_data' and not result.amounts


@pytest.mark.parametrize('expired', [False, True])
def test_instrument_evidence_can_meet_deadline_until_expiry(expired):
    pack, registry = synthetic_fixture('v2')
    source = registry.retrieve('allocation', owner_id=1, as_of=DAY)[0]
    data = pack.model_dump(mode='json')
    # Explicit fictional instrument evidence ONLY for this synthetic test.
    cash = data['assets'][0]
    cash['liquidity_days'] = 0
    cash['liquidity_evidence'] = dict(instrument='synthetic-test-cash-account',
        restrictions='synthetic unrestricted test balance', settlement='synthetic same-day settlement',
        source='synthetic_test evidence, no real instrument', as_of='2026-11-06',
        expires=DAY.isoformat() if expired else '2027-01-01')
    entry = dict(data['register']['assumptions'][0], id='cash.liquidity_days', value=0)
    data['register']['assumptions'].append(entry)
    pack, registry = signed_pack(data, source)
    result = allocate(snapshot(), answers(), pack,
        Constraints(eligible_liquid_paise=10000, maximum_liquidity_days=0),
        registry, owner_id=1, as_of=DAY, synthetic_test=True)
    if expired:
        assert result.status == 'infeasible' and result.liquidity_days['cash'] is None
    else:
        assert result.status == 'feasible' and result.liquidity_days['cash'] == 0
        assert {h.asset: h.value_paise for h in result.amounts} == dict(cash=10000, debt=0, equity=0, gold=0)


@pytest.mark.parametrize('values', [dict(liquidity_floor_bps=-1), dict(liquidity_floor_bps=10001),
                                  dict(near_term_months=0), dict(near_term_months=1201),
                                  dict(near_term_months=True)])
def test_invalid_policy_overrides(values):
    from tests.test_stage_e import scenario
    with pytest.raises(ValidationError):
        Constraints(**values)
    with pytest.raises(ValidationError):
        type(scenario()).model_validate({**scenario().model_dump(), **values})


def test_policy_expiry_blocks_synthetic_solver(monkeypatch):
    import engines.allocation as engine
    register = load_register()
    assumptions = tuple(a.model_copy(update={'expires': DAY, 'as_of': date(2026, 11, 6)})
                        for a in register.assumptions)
    monkeypatch.setattr(engine, 'load_register', lambda: register.model_copy(update={'assumptions': assumptions}))
    pack, registry = synthetic_fixture('v2')
    result = allocate(snapshot(), answers(), pack, Constraints(eligible_liquid_paise=10000),
        registry, owner_id=1, as_of=DAY, synthetic_test=True)
    assert result.status == 'insufficient_data' and 'expired' in result.reasons[0]
    assert not result.amounts


def test_policy_revision_stales_owned_plan_without_rewriting(db_engine, monkeypatch):
    from sqlalchemy.orm import Session
    from backend.services import allocation_service as service, portfolio_service as portfolio
    from tests.test_stage_e import save_inputs, scenario
    from backend.models.models import AllocationPlan
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    monkeypatch.setattr(portfolio, 'today', lambda: DAY)
    with Session(db_engine) as db:
        save_inputs(db)
        saved = service.create_owned_scenario(db, 1, scenario())
        original = db.get(AllocationPlan, saved['id']).input_snapshot
        policy = load_register().model_copy(update={'version': 'allocation-policy.test-revision'})
        monkeypatch.setattr(service, 'load_register', lambda: policy)
        read = service.read_owned_plan(db, 1, saved['id'])
        assert read['stale'] and 'prototype_policy_changed_or_expired' in read['stale_reasons']
        assert read['inputs'] == original and read['allocation'] == saved['allocation']
        assert read['recommendation_status'] == 'assumptions not validated'


def test_missing_policy_register_fails_closed(monkeypatch, client):
    import engines.allocation as engine
    import backend.finance.allocation_assumptions as assumptions
    from tests.api.test_tenancy import signup
    headers = signup(client)
    pack, registry = synthetic_fixture('v2')
    constraints = Constraints(eligible_liquid_paise=10000)
    def missing():
        raise FileNotFoundError('synthetic missing register')
    monkeypatch.setattr(engine, 'load_register', missing)
    result = allocate(snapshot(), answers(), pack, constraints,
        registry, owner_id=1, as_of=DAY, synthetic_test=True)
    assert result.status == 'insufficient_data' and not result.amounts
    monkeypatch.setattr(assumptions, 'load_register', missing)
    response = client.get('/allocation-assumptions', headers=headers)
    assert response.status_code == 503
    assert 'assumptions not validated' in response.json()['message']
