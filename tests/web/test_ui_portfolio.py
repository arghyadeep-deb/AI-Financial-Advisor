"""Owned synthetic portfolio observations through the real API."""
from datetime import timedelta
import pytest
from playwright.sync_api import expect
from tests.web.test_ui import live_url, tracker, signup  # noqa: F401


def seed_holdings(page, live_url, token, missing=True):
    from backend.services.portfolio_service import today
    day = today()
    quoted = {'account_ref': 'SYNTH_PF', 'instrument_id': 'SyntheticA', 'issuer_id': 'SyntheticIssuer',
              'asset_class': 'equity', 'units': '2', 'observation_date': day.isoformat(),
              'price_paise': 12345, 'price_date': day.isoformat(), 'price_source': 'synthetic_fixture',
              'price_version': 1, 'price_expires': (day + timedelta(days=1)).isoformat()}
    observations = [quoted]
    if missing:
        observations.append({'account_ref': 'SYNTH_PF', 'instrument_id': 'SyntheticMissing', 'units': '1', 'observation_date': day.isoformat()})
    response = page.request.post(live_url + '/portfolio/holdings', headers={'Authorization': 'Bearer ' + token}, data={
        'expected_revision': 0, 'idempotency_key': 'portfolio-ui-fixture', 'reason': 'Synthetic browser fixture',
        'data': {'confirmed': True, 'source': 'manual', 'as_of': day.isoformat(), 'observations': observations}})
    assert response.status == 200


def test_partial_valuation_sources_and_concentration(page, live_url, tracker):
    signup(page, live_url)
    seed_holdings(page, live_url, tracker['token'])
    response = page.request.get(live_url + '/portfolio/valuation', headers={'Authorization': 'Bearer ' + tracker['token']}).json()
    page.get_by_role('link', name='Portfolio', exact=True).click()
    area = page.locator('section.card').filter(has=page.get_by_role('heading', name='Observed holdings', exact=True))
    expect(area).to_contain_text('Valuation status: partial')
    expect(area).to_contain_text('Total value: unknown')
    expect(area).to_contain_text('known subtotal (priced subset): ₹246.90')
    expect(area).to_contain_text(response['concentration_method'])
    expect(area).to_contain_text('Concentration scope: priced subset only. No low-risk claim.')
    expect(area).to_contain_text('largest issuer share: 1')
    page.get_by_text('SyntheticMissing • SYNTH_PF', exact=True).click()
    expect(area.get_by_text('Unit price: unknown', exact=False)).to_be_visible()
    expect(area.get_by_text('Quote status: unavailable', exact=False)).to_be_visible()
    page.get_by_text('SyntheticA • SYNTH_PF', exact=True).click()
    expect(area.get_by_text('Unit price: ₹123.45', exact=False)).to_contain_text('synthetic_fixture')


@pytest.mark.parametrize('status', [404, 503])
def test_portfolio_unavailable_notice(page, live_url, status):
    signup(page, live_url)
    page.route('**/portfolio/valuation', lambda route: route.fulfill(status=status, json={'detail': 'Unavailable'}))
    page.get_by_role('link', name='Portfolio', exact=True).click()
    expect(page.get_by_text('This feature is not available yet, or the resource is missing or not shared with you.', exact=True)).to_be_visible()


def test_unavailable_valuation_never_becomes_zero(page, live_url, tracker):
    signup(page, live_url)
    from backend.services.portfolio_service import today
    day = today().isoformat()
    response = page.request.post(live_url + '/portfolio/holdings', headers={'Authorization': 'Bearer ' + tracker['token']}, data={
        'expected_revision': 0, 'idempotency_key': 'unpriced-fixture', 'reason': 'Synthetic unpriced fixture',
        'data': {'confirmed': True, 'source': 'manual', 'as_of': day, 'observations': [
            {'account_ref': 'SYNTH', 'instrument_id': 'Unpriced', 'units': '1', 'observation_date': day}]}})
    assert response.status == 200
    page.get_by_role('link', name='Portfolio', exact=True).click()
    expect(page.get_by_text('Valuation status: unavailable', exact=False).first).to_be_visible()
    expect(page.get_by_text('Total value: unknown', exact=False)).to_be_visible()
