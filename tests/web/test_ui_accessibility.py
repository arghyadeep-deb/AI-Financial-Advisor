"""T1004: accessibility and responsive smoke across every screen at phone, tablet and desktop widths.

Routes come from one list so a new screen only needs adding here. Run: pytest tests/web/test_ui_accessibility.py -q
"""
import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

from tests.web.test_ui import live_url, signup, synthetic, tracker  # noqa: E402,F401

PUBLIC = ["", "login", "signup", "demo"]
SIGNED_IN = ["dashboard", "health", "portfolio", "stocks", "credit", "reports", "profile", "chat",
             "statements", "monthly", "settings", "planning", "reminders", "household"]
WIDTHS = [(360, 740), (768, 1024), (1440, 900)]

NAMELESS = """() => [...document.querySelectorAll('input, select, textarea')].filter(e => {
  if (e.type === 'hidden' || e.hidden || e.closest('[hidden]')) return false;
  const r = e.getBoundingClientRect(); if (!r.width && !r.height) return false;
  const label = (e.labels && e.labels.length && [...e.labels].some(l => l.textContent.trim()));
  return !(label || e.getAttribute('aria-label') || e.getAttribute('aria-labelledby') || e.title);
}).map(e => e.id || e.name || e.type)"""

HEADING_ORDER = """() => {
  const levels = [...document.querySelectorAll('main h1, main h2, main h3, main h4')].map(h => Number(h.tagName[1]));
  const bad = []; for (let i = 1; i < levels.length; i++) if (levels[i] - levels[i-1] > 1) bad.push([levels[i-1], levels[i]]);
  return { h1: levels.filter(l => l === 1).length, bad, count: levels.length };
}"""

UNLABELLED_IMG = "() => [...document.querySelectorAll('main svg[role=img]')].filter(s => !s.getAttribute('aria-label')).length"
NO_SCROLL = "() => document.documentElement.scrollWidth - window.innerWidth"
WIDE = """() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > window.innerWidth + 1
  && !e.closest('.table-scroll')).slice(0, 6).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right))"""
BUTTONS_NAMELESS = "() => [...document.querySelectorAll('button, a[href]')].filter(b => !b.hidden && (b.getBoundingClientRect().width || b.getBoundingClientRect().height) && !(b.textContent.trim() || b.getAttribute('aria-label') || b.title)).length"


def check_screen(page, label):
    page.wait_for_timeout(400)
    assert page.evaluate(NO_SCROLL) <= 1, f"{label}: horizontal scroll, wide elements: {page.evaluate(WIDE)}"
    assert page.evaluate(NAMELESS) == [], f"{label}: inputs without a name"
    order = page.evaluate(HEADING_ORDER)
    assert order["h1"] == 1, f"{label}: expected exactly one h1, got {order['h1']}"
    assert order["bad"] == [], f"{label}: heading levels skip {order['bad']}"
    assert page.evaluate(UNLABELLED_IMG) == 0, f"{label}: svg role=img without aria-label"
    assert page.evaluate(BUTTONS_NAMELESS) == 0, f"{label}: button or link without a name"


@pytest.mark.parametrize("width,height", WIDTHS)
@pytest.mark.parametrize("route", PUBLIC)
def test_public_screens(page, live_url, tracker, route, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{live_url}/app/#/{route}")
    expect(page.locator("main")).to_be_visible()
    check_screen(page, f"/{route} @{width}")
    assert not tracker["errors"], tracker["errors"]


@pytest.mark.parametrize("width,height", WIDTHS)
def test_signed_in_screens(page, live_url, tracker, synthetic, monkeypatch, width, height):
    from backend.core.config import config
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', True)
    page.set_viewport_size({"width": width, "height": height})
    signup(page, live_url)
    # Capability and missing-inventory share the same 404: initialize a synthetic book explicitly.
    response = page.request.post(live_url + '/networth', headers={'Authorization': 'Bearer ' + tracker['token']},
        data={'expected_revision': 0, 'idempotency_key': 'accessibility-inventory', 'reason': 'Synthetic accessibility fixture',
              'data': {'observations': []}})
    assert response.status == 200
    for route in SIGNED_IN:
        page.goto(f"{live_url}/app/#/{route}")
        expect(page.locator("main h1").first).to_be_visible()
        check_screen(page, f"/{route} @{width}")
    assert not tracker["errors"], tracker["errors"]


@pytest.mark.parametrize("width,height", WIDTHS)
def test_new_screens_expanded_forms_and_long_evidence(page, live_url, tracker, monkeypatch, width, height):
    from backend.core.config import config
    monkeypatch.setattr(config, 'SYNTHETIC_HOUSEHOLDS_ENABLED', True)
    page.set_viewport_size({'width': width, 'height': height})
    signup(page, live_url)
    response = page.request.post(live_url + '/networth', headers={'Authorization': 'Bearer ' + tracker['token']},
        data={'expected_revision': 0, 'idempotency_key': 'expanded-inventory', 'reason': 'Synthetic evidence',
              'data': {'observations': [{'reference': 'synthetic_' + 'a' * 60, 'kind': 'asset', 'value_paise': 10001,
                                        'share_percent': '33.333333333333333333', 'valued_on': '2020-01-01'}]}})
    assert response.status == 200
    for route in ['planning', 'reminders', 'household']:
        page.goto(f'{live_url}/app/#/{route}')
        expect(page.locator('main h1')).to_be_visible()
        page.wait_for_timeout(400)
        for detail in page.locator('main details').all():
            detail.evaluate('(e) => e.open = true')
        check_screen(page, f'expanded /{route} @{width}')
        assert page.locator('main [style], main [onclick], main script').count() == 0
    assert not tracker['errors'], tracker['errors']


def test_skip_link_is_reachable_visible_on_focus_and_moves_focus_to_main(page, live_url):
    page.goto(f"{live_url}/app/#/login")
    page.focus("a.skip")
    box = page.locator("a.skip").bounding_box()
    assert box and box["x"] >= 0 and box["y"] >= 0                       # on screen once focused
    assert page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle") != "none"
    page.keyboard.press("Enter")
    assert page.evaluate("() => document.activeElement.id") == "main"


def test_login_form_works_with_keyboard_only(page, live_url):
    page.goto(f"{live_url}/app/#/login")
    page.focus("#email")
    page.keyboard.type("nobody@example.com")
    page.keyboard.press("Tab")
    page.keyboard.type("Wrong-password-123!")
    page.keyboard.press("Enter")
    expect(page.locator("[role=alert]").first).to_be_visible()


def test_charts_have_text_alternatives(page, live_url, tracker):
    from tests.web.test_ui import save_profile, run_analysis
    signup(page, live_url)
    save_profile(page)
    run_analysis(page)
    page.goto(f"{live_url}/app/#/dashboard")
    expect(page.locator("main svg[role=img]").first).to_be_visible()
    assert page.evaluate(UNLABELLED_IMG) == 0
    assert not tracker["errors"], tracker["errors"]
