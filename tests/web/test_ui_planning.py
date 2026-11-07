import pytest
from playwright.sync_api import expect
from tests.web.test_ui import live_url, tracker, signup, synthetic  # noqa: F401


def create_obligation(page, live_url):
    signup(page, live_url)
    page.get_by_role('link', name='Plan', exact=True).click()
    page.get_by_text('Add obligation', exact=True).click()
    page.fill('#obligations-newlabel', 'Synthetic rent')
    page.fill('#obligations-newamount_paise', '12345')
    page.fill('#obligations-newdue_date', '2026-11-20')
    page.fill('#obligations-newreason', 'Synthetic declaration')
    page.get_by_role('button', name='Create obligation', exact=True).click()
    expect(page.get_by_text('Synthetic rent — revision 1', exact=True)).to_be_visible()


def test_create_edit_and_real_revision_conflict(page, live_url, tracker):
    create_obligation(page, live_url)
    page.get_by_text('Synthetic rent — revision 1', exact=True).click()
    detail = page.locator('details').filter(has=page.get_by_text('Synthetic rent — revision 1', exact=True)).first
    expect(detail.get_by_text('amount paise: ₹123.45', exact=True)).to_be_visible()
    detail.get_by_label('Label', exact=True).fill('Changed rent')
    detail.get_by_label('Reason for change').fill('Corrected declaration')
    detail.get_by_role('button', name='Save changes').click()
    page.get_by_text('Changed rent — revision 2', exact=True).click()
    headers = {'Authorization': 'Bearer ' + tracker['token']}
    row = page.request.get(live_url + '/obligations', headers=headers).json()[0]
    response = page.request.put(live_url + '/obligations/' + row['id'], headers=headers,
        data={'data': row['data'], 'expected_revision': 2, 'reason': 'Concurrent edit', 'idempotency_key': 'concurrent-obligation'})
    assert response.status == 200
    detail = page.locator('details').filter(has=page.get_by_text('Changed rent — revision 2', exact=True)).first
    detail.get_by_label('Label', exact=True).fill('Keep my draft')
    detail.get_by_label('Reason for change').fill('Draft edit')
    detail.get_by_role('button', name='Save changes').click()
    expect(detail.get_by_role('alert')).to_contain_text('your input is preserved')
    expect(detail.get_by_label('Label', exact=True)).to_have_value('Keep my draft')


def test_disabled_planning(page, live_url):
    signup(page, live_url)
    page.route('**/budgets', lambda route: route.fulfill(status=503, json={'detail': 'Disabled'}))
    page.get_by_role('link', name='Plan', exact=True).click()
    expect(page.get_by_text('Planning is not available yet.', exact=True)).to_be_visible()
    assert page.get_by_role('button', name='Create obligation').count() == 0


def test_planning_isolation(page, live_url, tracker):
    create_obligation(page, live_url)
    page.get_by_role('button', name='Log out', exact=True).click()
    expect(page.get_by_role('heading', name='Welcome back')).to_be_visible()
    signup(page, live_url)
    page.get_by_role('link', name='Plan', exact=True).click()
    expect(page.get_by_text('No obligations yet.', exact=True)).to_be_visible()
    assert page.get_by_text('Synthetic rent — revision 1').count() == 0


def test_budget_goal_debt_create_and_edit(page, live_url, tracker, synthetic):
    create_obligation(page, live_url)
    headers = {'Authorization': 'Bearer ' + tracker['token']}
    obligation = page.request.get(live_url + '/obligations', headers=headers).json()[0]
    response = page.request.post(live_url + '/statement-accounts', headers=headers,
        data={'label': 'Synthetic funding', 'token': 'SYNTH_GOAL', 'account_type': 'synthetic_debit'})
    assert response.status == 201
    account = response.json()
    cases = [
        ('budgets', 'budget', {'month': '2026-11', 'amount0': '10001'}, '2026-11', 'month', '2026-12', '2026-12'),
        ('goals', 'goal', {'label': 'Synthetic goal', 'target_paise': '99999', 'target_date': '2027-11-01',
                         'funding_account_id': account['id']}, 'Synthetic goal', 'label', 'Edited goal', 'Edited goal'),
        ('debts', 'debt', {'label': 'Synthetic debt', 'obligation_id': obligation['id'], 'principal_paise': '999999',
                         'minimum_payment_paise': '12345', 'evidence_date': '2026-11-01'},
                         'Synthetic debt', 'label', 'Edited debt', 'Edited debt'),
    ]
    for kind, singular, values, title, edit_key, edit_value, edited_title in cases:
        page.get_by_text('Add ' + singular, exact=True).click()
        for key, value in values.items():
            page.locator('#' + kind + '-new' + key).fill(value)
        page.locator('#' + kind + '-newreason').fill('Synthetic creation')
        page.get_by_role('button', name='Create ' + singular, exact=True).click()
        page.get_by_text(title + ' — revision 1', exact=True).click()
        detail = page.locator('details').filter(has=page.get_by_text(title + ' — revision 1', exact=True)).first
        if kind == 'budgets':
            expect(detail.get_by_text('groceries: ₹100.01', exact=True)).to_be_visible()
        if kind == 'debts':
            expect(detail.get_by_label('Annual rate (basis points; blank means unknown)', exact=True)).to_have_value('')
        detail.locator('[id$="' + edit_key + '"]').fill(edit_value)
        detail.get_by_label('Reason for change').fill('Synthetic correction')
        detail.get_by_role('button', name='Save changes').click()
        expect(page.get_by_text(edited_title + ' — revision 2', exact=True)).to_be_visible()


def test_planning_offline_preserves_draft_and_missing_amount_is_rejected(page, live_url):
    signup(page, live_url)
    page.get_by_role('link', name='Plan', exact=True).click()
    page.get_by_text('Add obligation', exact=True).click()
    page.fill('#obligations-newlabel', 'Keep draft')
    page.fill('#obligations-newdue_date', '2026-11-20')
    page.fill('#obligations-newreason', 'Synthetic declaration')
    page.get_by_role('button', name='Create obligation', exact=True).click()
    expect(page.get_by_role('alert')).to_be_visible()
    page.fill('#obligations-newamount_paise', '12345')
    page.route('**/obligations', lambda route: route.abort() if route.request.method == 'POST' else route.continue_())
    page.get_by_role('button', name='Create obligation', exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Cannot reach the server')
    expect(page.locator('#obligations-newlabel')).to_have_value('Keep draft')


def test_save_preserves_other_drafts_and_lost_response_retry_is_idempotent(page, live_url, tracker):
    signup(page, live_url)
    page.get_by_role('link', name='Plan', exact=True).click()
    page.get_by_text('Add goal', exact=True).click()
    page.fill('#goals-newlabel', 'Keep unsaved goal')
    page.get_by_text('Add obligation', exact=True).click()
    page.fill('#obligations-newlabel', 'Lost response bill')
    page.fill('#obligations-newamount_paise', '10001')
    page.fill('#obligations-newdue_date', '2026-11-20')
    page.fill('#obligations-newreason', 'Synthetic declaration')
    keys = []
    def lose_first_response(route):
        if route.request.method != 'POST':
            route.continue_()
            return
        keys.append(route.request.post_data_json['idempotency_key'])
        if len(keys) == 1:
            response = route.fetch()
            assert response.status == 201
            route.abort()
        else:
            route.continue_()
    page.route('**/obligations', lose_first_response)
    page.get_by_role('button', name='Create obligation', exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text('Cannot reach the server')
    page.get_by_role('button', name='Create obligation', exact=True).click()
    expect(page.get_by_text('Lost response bill — revision 1', exact=True)).to_be_visible()
    expect(page.locator('#goals-newlabel')).to_have_value('Keep unsaved goal')
    assert len(keys) == 2 and keys[0] == keys[1]
    rows = page.request.get(live_url + '/obligations', headers={'Authorization': 'Bearer ' + tracker['token']}).json()
    assert len(rows) == 1

