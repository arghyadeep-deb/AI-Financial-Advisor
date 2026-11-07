from sqlalchemy.orm import Session
from playwright.sync_api import expect
from tests.web.test_ui import live_url, tracker, signup, synthetic  # noqa: F401


def test_preferences_quiet_hours_opt_out_and_session_dismiss(page, live_url, tracker, db_engine):
    email = signup(page, live_url)
    from backend.models.models import User
    from backend.services.notification_service import deliver
    with Session(db_engine) as db:
        user = db.query(User).filter_by(email=email).one()
        deliver(db, user.id, 'synthetic-notice', 'reminder')
        db.commit()
    page.get_by_role('link', name='Reminders', exact=True).click()
    expect(page.get_by_text('You have a reminder to review.', exact=True)).to_be_visible()
    page.get_by_role('button', name='Dismiss You have a reminder to review. for this visit', exact=True).click()
    expect(page.get_by_text('No notices to show.', exact=True)).to_be_visible()
    page.get_by_role('button', name='Refresh notices').click()
    expect(page.get_by_text('No notices to show.', exact=True)).to_be_visible()
    page.get_by_label('Planning reminders', exact=True).uncheck()
    page.get_by_label('Quiet hours start', exact=False).fill('22')
    page.get_by_label('Quiet hours end', exact=False).fill('6')
    page.get_by_role('button', name='Save reminder preferences').click()
    expect(page.get_by_text('Reminder preferences saved. Email stays off.', exact=True)).to_be_visible()
    pref = page.request.get(live_url + '/preferences', headers={'Authorization': 'Bearer ' + tracker['token']}).json()
    assert pref == {'enabled': True, 'email_enabled': False, 'categories': ['report_ready'], 'quiet_start': 22, 'quiet_end': 6}
    page.get_by_label('Enable in-app notices').uncheck()
    with page.expect_response(lambda r: r.url.endswith('/preferences') and r.request.method == 'PUT'):
        page.get_by_role('button', name='Save reminder preferences').click()
    expect(page.get_by_text('Reminder preferences saved. Email stays off.', exact=True)).to_be_visible()
    assert not page.request.get(live_url + '/preferences', headers={'Authorization': 'Bearer ' + tracker['token']}).json()['enabled']


def test_notifications_invalid_quiet_hours_network_and_conflict_preserve_input(page, live_url):
    signup(page, live_url)
    page.get_by_role('link', name='Reminders', exact=True).click()
    page.get_by_label('Quiet hours start', exact=False).fill('22')
    page.get_by_role('button', name='Save reminder preferences').click()
    expect(page.get_by_role('alert')).to_contain_text('Both quiet-hour boundaries')
    page.get_by_label('Quiet hours end', exact=False).fill('6')
    page.route('**/preferences', lambda route: route.fulfill(status=409, json={'detail': 'Changed'}) if route.request.method == 'PUT' else route.continue_())
    page.get_by_role('button', name='Save reminder preferences').click()
    expect(page.get_by_role('alert')).to_contain_text('your input is preserved')
    expect(page.get_by_label('Quiet hours start', exact=False)).to_have_value('22')
    page.unroute('**/preferences')
    page.route('**/preferences', lambda route: route.abort())
    page.get_by_role('button', name='Save reminder preferences').click()
    expect(page.get_by_role('alert')).to_contain_text('Cannot reach the server')


def test_notifications_unavailable_and_ended_session(page, live_url, tracker):
    signup(page, live_url)
    page.route('**/preferences', lambda route: route.fulfill(status=503, json={'detail': 'Disabled'}))
    page.get_by_role('link', name='Reminders', exact=True).click()
    expect(page.get_by_text('Reminders are not available yet.', exact=True)).to_be_visible()
    page.unroute('**/preferences')
    page.request.post(live_url + '/auth/logout', headers={'Authorization': 'Bearer ' + tracker['token']})
    page.get_by_role('link', name='Plan', exact=True).click()
    expect(page.get_by_role('heading', name='Welcome back')).to_be_visible()
