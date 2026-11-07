"""003 T306 offline acceptance: two owners, dated sources and observed-only totals."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from backend.services import portfolio_service
from backend.services.output_guard import guard_allocation
from engines.portfolio import Position, metrics
from tests.api.test_tenancy import PROFILE, signup
from tests.test_stage_e import DAY, book, observation, scenario
from tests.allocation.test_allocation import answers


@pytest.fixture(autouse=True)
def fixed_day(monkeypatch):
    monkeypatch.setattr(portfolio_service, 'today', lambda: DAY)


def test_owned_four_class_scenario_review_and_projection_separation(client, monkeypatch):
    owner, other = signup(client), signup(client)
    profile = {**PROFILE, 'existing_savings': 300000, 'existing_investments': 80000, 'existing_debts': 0}
    assert client.post('/profile', headers=owner, json=profile).status_code == 200
    holdings_request = book(observations=[observation(asset_class='gold')]).model_dump(mode='json')
    first = client.post('/portfolio/holdings', headers=owner, json=holdings_request)
    assert first.status_code == 200, first.text
    # Replay is identical and never duplicates an observation.
    assert client.post('/portfolio/holdings', headers=owner, json=holdings_request).json() == first.json()
    raw = dict(expected_revision=0, idempotency_key=uuid4().hex, reason='Synthetic reviewed answers',
               data=answers().model_dump(mode='json'))
    suitability = client.post('/portfolio/suitability', headers=owner, json=raw)
    assert suitability.status_code == 200, suitability.text
    assert suitability.json()['assessment']['status'] == 'complete'
    assert not suitability.json()['assessment']['public_eligible']
    assert client.post('/portfolio/suitability', headers=owner, json=raw).json() == suitability.json()
    before = client.get('/portfolio/valuation', headers=owner).json()
    assert before['total_value_paise'] == 100000 and before['asset_class_paise'] == {'gold': 100000}
    for endpoint in ('holdings', 'suitability', 'valuation'):
        foreign = client.get('/portfolio/'+endpoint+'?revision=1', headers=other)
        missing = client.get('/portfolio/'+endpoint+'?revision=999', headers=other)
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json()['message'] == missing.json()['message']
    shock = client.post('/portfolio/scenarios', headers=owner, json=dict(expected_revision=1,
        as_of=DAY.isoformat(), shock_bps=10000, contribution_paise=999999)).json()
    assert shock['status'] == 'hypothetical' and not shock['persisted']
    assert shock['scenario_value_with_contribution_paise'] == 1199999
    request = scenario().model_dump(mode='json')
    assert client.post('/allocation-scenarios', headers=owner, json=request).status_code == 404
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    request.update(excluded_assets=['equity', 'gold'], maximum_liquidity_days=0)
    response = client.post('/allocation-scenarios', headers=owner, json=request)
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan['inputs']['assumptions']['universe_version'] == 'inr-classes.synthetic.v2'
    assert plan['allocation']['status'] == 'feasible'
    amounts = {h['asset']: h['value_paise'] for h in plan['allocation']['amounts']}
    assert amounts == dict(cash=450000, debt=0, equity=0, gold=0)
    assert plan['comparison']['current_value_paise'] == 100000
    assert plan['rebalance']['current_paise']['gold'] == 100000
    assert plan['rebalance']['tax_cost_paise'] is plan['rebalance']['net_improvement'] is None
    assert not plan['stale'] and not plan['public_eligible'] and not plan['named_products_eligible']
    assert client.post('/allocation-scenarios', headers=owner, json=request).json()['id'] == plan['id']
    foreign = client.get('/allocation-plans/'+plan['id'], headers=other)
    missing = client.get('/allocation-plans/missing', headers=other)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json()['message'] == missing.json()['message']
    # Health and hypothetical calculations cannot rewrite observed holdings/quotes.
    assert client.post('/analysis', headers=owner, json={'analysis_type': 'health'}).status_code == 200
    assert client.get('/portfolio/valuation', headers=owner).json() == before
    assert client.get('/portfolio/holdings', headers=owner).json() == first.json()
    correction = book(1, observations=[observation(asset_class='gold', price_paise=80000, price_version=2)])
    assert client.post('/portfolio/holdings', headers=owner, json=correction.model_dump(mode='json')).status_code == 200
    old = client.get('/allocation-plans/'+plan['id'], headers=owner).json()
    assert old['stale'] and 'holdings_changed' in old['stale_reasons']
    assert old['comparison']['current_value_paise'] == 100000
    assert client.get('/portfolio/valuation', headers=owner).json()['total_value_paise'] == 200000
    monkeypatch.setenv('NAMED_PRODUCT_RECOMMENDATIONS', 'true')
    assert client.post('/allocation-proposals', headers=owner, json={'override': True}).json()['status'] == 'gated'
    safe = guard_allocation(plan, {'public_eligible': True, 'trade': 'BUY Named Fund', 'allocation': {'budget_paise': 99999999}})
    assert safe['allocation'] == plan['allocation'] and 'trade' not in safe
    assert not safe['public_eligible'] and not safe['named_products_eligible']
    monkeypatch.setenv('APP_ENV', 'production')
    assert client.post('/allocation-scenarios', headers=owner, json=request).status_code == 404


def position(identity, **changes):
    return Position(**{**dict(observation_id=identity, instrument_id=identity, units=Decimal('1'),
        price_paise=2500, price_date=DAY, expires=date(2026, 11, 8), source_id='synthetic',
        source_version=1, issuer_id='issuer-one', asset_class='equity'), **changes})


@pytest.mark.parametrize('changes', [dict(price_paise=None), dict(price_date=None),
    dict(source_id=None), dict(source_version=None), dict(expires=None), dict(expires=DAY),
    dict(currency='USD'), dict(price_date=date(2026, 11, 8))])
def test_price_source_coverage_and_concentration_never_imply_complete(changes):
    result = metrics((position('known'), position('missing', **changes)), as_of=DAY)
    assert result['status'] == 'partial' and result['priced_positions'] == 1
    assert result['known_subtotal_paise'] == 2500 and result['total_value_paise'] is None
    assert result['missing_price_observations'] == ['missing']
    assert result['issuer_hhi'] is None and not result['low_risk_claim']
    assert result['concentration_scope'] == 'priced subset only'
    assert result['absolute_gain_paise'] is None


def test_issuer_aggregation_unknown_exposure_and_independent_hhi():
    # Issuer one: 2,500+2,500 =5,000; issuer two:15,000. HHI=1/16+9/16=5/8.
    positions = (position('a'), position('b', asset_class='debt'),
                 position('c', issuer_id='issuer-two', asset_class='gold', price_paise=15000))
    result = metrics(positions, as_of=DAY)
    assert result['issuer_paise'] == {'issuer-one': 5000, 'issuer-two': 15000}
    assert result['issuer_hhi'] == '5/8' and result['largest_issuer_share'] == '3/4'
    assert result['asset_class_paise'] == dict(equity=2500, debt=2500, gold=15000)
    unknown = metrics((*positions, position('unknown', issuer_id=None, asset_class=None, price_paise=5000)), as_of=DAY)
    assert unknown['unknown_class_paise'] == unknown['unknown_issuer_paise'] == 5000
    assert unknown['issuer_hhi'] is None and unknown['largest_issuer_share'] == '3/5'
    assert not unknown['low_risk_claim']
