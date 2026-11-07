import pytest
from sqlalchemy.orm import Session
from playwright.sync_api import expect
from tests.web.test_ui import live_url, tracker, signup, synthetic  # noqa: F401


@pytest.fixture
def households_enabled(monkeypatch):
    from backend.core.config import config
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', True)


def section(page, title):
    return page.locator('section.card').filter(has=page.get_by_role('heading', name=title, exact=True))


def initialize(page):
    page.get_by_role('link', name='Household preview', exact=True).click()
    page.get_by_role('button', name='Start synthetic personal inventory').click()
    expect(page.get_by_role('heading', name='Personal net worth — your observations only')).to_be_visible()


def add_observation(page, reference='synthetic_cash', share='33.333333333333333333'):
    page.get_by_text('Add asset or liability', exact=True).click()
    form = section(page, 'Add observation')
    form.get_by_label('Account / holding reference', exact=True).fill(reference)
    form.get_by_label('Whole observed value (paise)').fill('10001')
    form.get_by_label('Exact ownership percentage').fill(share)
    form.get_by_label('Valuation date').fill('2026-11-01')
    form.get_by_label('Reason for inventory change').fill('Synthetic observation')
    form.get_by_role('button', name='Add observation', exact=True).click()
    expect(page.get_by_text('Personal inventory revision 2', exact=True)).to_be_visible()


def test_networth_exact_share_provenance_edit_and_conflict(page, live_url, tracker, households_enabled):
    signup(page, live_url)
    initialize(page)
    add_observation(page)
    # Leave another form's draft open while editing this observation.
    draft = section(page, 'Add observation')
    draft.get_by_label('Account / holding reference', exact=True).fill('Keep_unsaved_observation')
    personal = section(page, 'Personal net worth — your observations only')
    expect(personal).to_contain_text('2026-11-01 • source: user_declared')
    expect(personal).to_contain_text('owned value: ₹33.34')
    expect(personal).to_contain_text('unallocated value: ₹66.67')
    expect(personal).to_contain_text('Planning allocation unavailable')
    page.get_by_text('Edit synthetic_cash', exact=True).click()
    form = section(page, 'Save observation synthetic_cash')
    expect(form.get_by_label('Exact ownership percentage')).to_have_value('33.333333333333333333')
    form.get_by_label('Whole observed value (paise)').fill('20001')
    form.get_by_label('Reason for inventory change').fill('Synthetic correction')
    form.get_by_role('button', name='Save observation synthetic_cash').click()
    expect(page.get_by_text('Personal inventory revision 3', exact=True)).to_be_visible()
    expect(draft.get_by_label('Account / holding reference', exact=True)).to_have_value('Keep_unsaved_observation')
    page.get_by_text('Edit synthetic_cash', exact=True).click()
    headers = {'Authorization': 'Bearer ' + tracker['token']}
    row = page.request.get(live_url + '/networth', headers=headers).json()
    assert page.request.post(live_url + '/networth', headers=headers, data={'data': row['data'], 'expected_revision': 3,
        'reason': 'Concurrent update', 'idempotency_key': 'concurrent-networth'}).status == 200
    form = section(page, 'Save observation synthetic_cash')
    form.get_by_label('Whole observed value (paise)').fill('77777')
    form.get_by_label('Reason for inventory change').fill('Keep draft')
    form.get_by_role('button', name='Save observation synthetic_cash').click()
    expect(form.get_by_role('alert')).to_contain_text('your input is preserved')
    expect(form.get_by_label('Whole observed value (paise)')).to_have_value('77777')


def test_household_invite_accept_account_grants_and_revoke(page, context, live_url, tracker, db_engine, households_enabled):
    signup(page, live_url)
    other = context.new_page()
    email = signup(other, live_url)
    from backend.models.models import User
    with Session(db_engine) as db:
        other_id = db.query(User).filter_by(email=email).one().id
    initialize(page)
    add_observation(page, share='50')
    create = section(page, 'Create household')
    create.get_by_label('Household label').fill('Synthetic family')
    create.get_by_role('button', name='Create household').click()
    expect(create.get_by_role('alert')).to_be_visible()  # explicit adult confirmation required
    create.get_by_label('I declare that I am at least 18 years old (UNVERIFIED)', exact=True).check()
    create.get_by_role('button', name='Create household').click()
    expect(page.get_by_text('Created Synthetic family', exact=False)).to_be_visible()
    house_id = page.get_by_label('Household ID', exact=True).input_value()
    invite = section(page, 'Create invitation')
    invite.get_by_label('Invitee user ID').fill(str(other_id))
    invite.get_by_label('I declare that I am at least 18 years old (UNVERIFIED)', exact=True).check()
    with page.expect_response(lambda r: '/invites' in r.url and r.request.method == 'POST') as response:
        invite.get_by_role('button', name='Create invitation').click()
    invitation = response.value.json()
    initialize(other)
    accept = section(other, 'Accept invitation')
    accept.get_by_label('Invitation ID', exact=True).fill(invitation['id'])
    accept.get_by_label('Invitation token', exact=True).fill(invitation['token'])
    accept.get_by_label('I declare that I am at least 18 years old (UNVERIFIED)', exact=True).check()
    accept.get_by_role('button', name='Accept invitation').click()
    expect(other.get_by_text('Membership accepted.', exact=False)).to_be_visible()
    other.get_by_role('button', name='Refresh shared snapshot').click()
    shared = section(other, 'Household consolidated — personal plus explicitly shared observations')
    expect(shared).to_contain_text('Unavailable: no declared observations.')
    assert shared.get_by_text('synthetic_cash', exact=False).count() == 0
    grant = section(page, 'Save account permissions')
    grant.get_by_label('Recipient user ID').fill(str(other_id))
    grant.get_by_label('Account / holding reference to share').fill('synthetic_cash')
    grant.get_by_label('Allow summaries', exact=True).check()
    grant.get_by_label('Grant enabled (uncheck to revoke)', exact=True).check()
    grant.get_by_role('button', name='Save account permissions').click()
    expect(page.get_by_text('Account synthetic_cash • grant revision 1', exact=False)).to_be_visible()
    other.get_by_role('button', name='Refresh shared snapshot').click()
    expect(shared).to_contain_text('synthetic_cash')
    expect(shared).to_contain_text('owned value: ₹50.01')
    # Summaries permission does not grant exports/documents/transactions.
    headers = {'Authorization': 'Bearer ' + tracker['token']}
    assert page.request.get(live_url + '/households/' + house_id + '/snapshot', headers=headers).status == 200
    grant.get_by_label('Grant enabled (uncheck to revoke)', exact=True).uncheck()
    grant.get_by_role('button', name='Save account permissions').click()
    expect(page.get_by_text('Account synthetic_cash • grant revision 2', exact=False)).to_be_visible()
    other.get_by_role('button', name='Refresh shared snapshot').click()
    expect(shared).to_contain_text('Unavailable: no declared observations.')
    other.close()


def test_household_disabled_notice(page, live_url, monkeypatch):
    from backend.core.config import config
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', False)
    signup(page, live_url)
    page.get_by_role('link', name='Household preview', exact=True).click()
    expect(page.get_by_text('Household is not available yet, or no personal inventory has been created.', exact=True)).to_be_visible()
    page.get_by_role('button', name='Start synthetic personal inventory').click()
    expect(page.get_by_text('Household is not available yet.', exact=True)).to_be_visible()
    assert page.get_by_role('button', name='Create household', exact=True).count() == 0
