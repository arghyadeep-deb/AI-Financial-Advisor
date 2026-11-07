"""Browser tests for the plain HTML/CSS/JS frontend (frontend/static), served by the real FastAPI app on a live
local port against an isolated database, with every model provider disabled (conftest).  Run:
    pytest tests/web -q          (needs: pip install pytest-playwright; playwright install chromium)
"""
import json
import socket
import threading
import time
import uuid

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

PASSWORD = "Uitest-Throwaway-4471!"


@pytest.fixture()
def live_url(db_engine):
    import uvicorn
    from sqlalchemy.orm import sessionmaker

    from backend.core.database import get_db
    from backend.main import app

    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=10)
    app.dependency_overrides.clear()


@pytest.fixture()
def tracker(page):
    """Collects console errors, page errors and the bearer token the page used."""
    seen = {"errors": [], "token": None}
    page.on("console", lambda m: seen["errors"].append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.on("pageerror", lambda e: seen["errors"].append(str(e)))
    page.on("response", lambda r: seen["errors"].append(f"HTTP {r.status} {r.request.method} {r.url}") if r.status >= 400 and "/auth/logout" not in r.url and not (r.status == 404 and r.url.endswith("/profile")) else None)

    def on_req(r):
        auth = r.headers.get("authorization")
        if auth and auth.startswith("Bearer "):
            seen["token"] = auth[7:]
    page.on("request", on_req)
    return seen


def signup(page, live_url):
    email = f"u{uuid.uuid4().hex[:8]}@example.com"
    page.goto(f"{live_url}/app/#/signup")
    page.fill("#full_name", "Test User")
    page.fill("#email", email)
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    expect(page.get_by_role("heading", name="Your profile")).to_be_visible()
    return email


def save_profile(page, income="100000", expenses="40000"):
    page.fill("#monthly_income", income)
    page.fill("#monthly_expenses", expenses)
    page.fill("#existing_savings", "240000")
    page.fill("#existing_investments", "0")
    page.fill("#existing_debts", "0")
    page.fill("#monthly_debt_payment", "0")
    page.fill("#monthly_credit_spend", "10000")
    page.click("button[type=submit]")
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()


def run_analysis(page):
    page.get_by_role("button", name="Run full analysis").click()
    expect(page.get_by_text("Health score", exact=True)).to_be_visible(timeout=60000)


def test_signup_profile_analysis_shows_degraded_banner_and_charts(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    run_analysis(page)
    expect(page.get_by_text("Partly automatic")).to_be_visible()          # providers are off: labelled, not "success"
    expect(page.get_by_text("Suggested allocation")).to_be_visible()
    assert page.locator("svg.chart circle.stk").count() >= 2             # donut drawn with strokes (not filled blobs)
    assert tracker["errors"] == []


def test_deficit_dashboard_shows_no_plan_projection_or_card(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page, income="30000", expenses="40000")
    run_analysis(page)
    expect(page.get_by_text("Nothing to invest each month right now")).to_be_visible()
    assert page.get_by_text("Suggested allocation").count() == 0
    assert page.get_by_text("Wealth projection").count() == 0
    page.get_by_role("link", name="Credit").click()
    expect(page.get_by_text("No card recommendations")).to_be_visible()


def test_unknown_credit_score_stays_unknown_in_what_if(page, live_url, tracker):
    signup(page, live_url)
    page.fill("#credit_score", "780") if not page.locator("#credit_score").is_disabled() else None
    page.uncheck("#credit_unknown")
    page.fill("#credit_score", "780")
    save_profile(page)
    page.get_by_role("link", name="Health").click()
    page.check("#w_unknown")
    page.get_by_role("button", name="Try this what-if").click()
    expect(page.get_by_text("What-if result")).to_be_visible(timeout=60000)
    expect(page.get_by_text("Not provided").first).to_be_visible()


def test_logout_revokes_the_token_on_the_server(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    token = tracker["token"]
    assert token
    ok = page.request.get(f"{live_url}/profile", headers={"Authorization": f"Bearer {token}"})
    assert ok.status == 200
    page.get_by_role("button", name="Log out").click()
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    after = page.request.get(f"{live_url}/profile", headers={"Authorization": f"Bearer {token}"})
    assert after.status == 401
    page.goto(f"{live_url}/app/#/dashboard")                             # token lives in memory only
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    assert page.evaluate("[localStorage.length, sessionStorage.length, document.cookie.length]") == [0, 0, 0]


def test_revoked_session_sends_user_to_login_on_next_request(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    page.request.post(f"{live_url}/auth/logout", headers={"Authorization": f"Bearer {tracker['token']}"})
    page.get_by_role("link", name="Health").click()
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()


def test_profile_conflict_asks_to_reload_not_overwrite(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    page.get_by_role("link", name="Profile").click()
    expect(page.get_by_role("heading", name="Your profile")).to_be_visible()
    page.wait_for_selector("#monthly_income")
    cur = page.request.get(f"{live_url}/profile", headers={"Authorization": f"Bearer {tracker['token']}"}).json()
    body = {k: cur[k] for k in ("age", "employment_type", "risk_tolerance", "investment_horizon")}
    body.update({"monthly_income": "120000", "monthly_expenses": "40000", "expected_revision": cur["revision"]})
    r = page.request.post(f"{live_url}/profile", data=json.dumps(body),
                          headers={"Authorization": f"Bearer {tracker['token']}", "Content-Type": "application/json"})
    assert r.status == 200                                                # another tab saved first
    page.fill("#monthly_income", "90000")
    page.click("button[type=submit]")
    expect(page.get_by_text("changed somewhere else")).to_be_visible()


def test_model_text_is_rendered_as_text_never_markup(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    evil = "<img src=x onerror=window.__pwned=1> <script>window.__pwned=2</script> **bold**"

    def fulfill(route):
        frames = (f"data: {json.dumps({'thread_id': 1, 'chunk': evil})}\n\n"
                  f"data: {json.dumps({'thread_id': 1, 'done': True, 'full_reply': evil, 'status': 'ok'})}\n\n")
        route.fulfill(status=200, content_type="text/event-stream", body=frames)

    page.route("**/chat/stream", fulfill)
    page.get_by_role("link", name="Ask the advisor").click()
    page.fill("#chat_in", "hello")
    page.get_by_role("button", name="Send").click()
    expect(page.locator(".msg.assistant").first).to_contain_text("<img src=x")
    assert page.locator(".messages img, .messages script").count() == 0
    assert page.evaluate("window.__pwned === undefined")


def test_stream_frames_split_across_chunks_are_reassembled(page, live_url, tracker):
    page.goto(f"{live_url}/app/#/")
    result = page.evaluate(
        """async () => {
          const api = await import('/app/js/api.js');
          api.session.set('t');
          const enc = new TextEncoder();
          const pieces = ['data: {"thread_id": 7, "chu', 'nk": "Hel"}\\n', '\\ndata: {"chunk": "lo"}\\n\\nda',
                          'ta: {"done": true, "thread_id": 7, "full_reply": "Hello", "status": "ok"}\\n\\n'];
          const realFetch = window.fetch;
          window.fetch = async () => new Response(new ReadableStream({
            start(c) { pieces.forEach(p => c.enqueue(enc.encode(p))); c.close(); } }), {status: 200});
          const got = [];
          const out = await api.streamChat({message: 'hi', onChunk: (t) => got.push(t)});
          window.fetch = realFetch;
          return {got, out};
        }""")
    assert result["got"] == ["Hel", "lo"]
    assert result["out"]["ok"] is True and result["out"]["reply"] == "Hello" and result["out"]["threadId"] == 7


def test_ui_has_strict_csp_and_docs_keep_working(page, live_url):
    r = page.request.get(f"{live_url}/app/")
    csp = r.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "unsafe-inline" not in csp
    assert "content-security-policy" not in page.request.get(f"{live_url}/docs").headers
    assert page.request.get(f"{live_url}/health").status == 200


def test_pages_have_no_inline_style_or_script_attributes(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    run_analysis(page)
    bad = page.evaluate("document.querySelectorAll('[style], script:not([src]), [onclick]').length")
    assert bad == 0
    assert tracker["errors"] == []


def test_what_if_cannot_silently_keep_a_cleared_debt_payment(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)                                                     # saves a declared payment of 0
    page.get_by_role("link", name="Health").click()
    page.fill("#w_payment", "")
    page.get_by_role("button", name="Try this what-if").click()
    expect(page.get_by_text("cannot clear a saved payment")).to_be_visible()
    assert page.get_by_text("What-if result").count() == 0


def test_chat_thread_buttons_are_disabled_while_a_reply_streams(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    held = {}
    page.route("**/chat/stream", lambda route: held.update(route=route))      # hold the request open
    page.get_by_role("link", name="Ask the advisor").click()
    page.fill("#chat_in", "hello")
    page.get_by_role("button", name="Send").click()
    expect(page.get_by_role("button", name="+ New chat")).to_be_disabled()
    for _ in range(50):
        if "route" in held:
            break
        page.wait_for_timeout(100)
    body = (f"data: {json.dumps({'thread_id': 1, 'chunk': 'ok'})}\n\n"
            f"data: {json.dumps({'thread_id': 1, 'done': True, 'full_reply': 'ok', 'status': 'ok'})}\n\n")
    held["route"].fulfill(status=200, content_type="text/event-stream", body=body)
    expect(page.locator(".msg.assistant").first).to_contain_text("ok", timeout=10000)
    expect(page.get_by_role("button", name="+ New chat")).to_be_enabled()


def test_settings_sessions_password_consent_and_preferences(page, live_url, tracker):
    email = signup(page, live_url)
    page.goto(f"{live_url}/app/#/settings")
    expect(page.get_by_role("heading", name="Settings")).to_be_visible()
    expect(page.get_by_text("(this device)")).to_be_visible()
    # consent choice is recorded
    page.get_by_role("button", name="Allow").first.click()
    expect(page.get_by_text("allowed.")).to_be_visible()
    # notification preferences round-trip
    page.check("#pref_on")
    page.get_by_role("button", name="Save notification settings").click()
    expect(page.get_by_text("Saved.", exact=True)).to_be_visible()
    # password change signs everyone out
    page.fill("#pw_cur", PASSWORD)
    page.fill("#pw_new", "Uitest-Changed-9912!")
    page.get_by_role("button", name="Change password").click()
    expect(page).to_have_url(__import__("re").compile(r"#/(login)?$"))
    page.goto(f"{live_url}/app/#/login")
    page.fill("#email", email)
    page.fill("#password", "Uitest-Changed-9912!")
    page.click("button[type=submit]")
    expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
    assert not tracker["errors"], tracker["errors"]


def test_statement_upload_review_and_confirm(page, live_url, tracker, db_engine, monkeypatch, tmp_path):
    from backend.core.config import config
    from cryptography.fernet import Fernet
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))
    from pathlib import Path
    from sqlalchemy.orm import Session

    from backend.workers import statements as worker

    signup(page, live_url)
    page.goto(f"{live_url}/app/#/statements")
    expect(page.get_by_role("heading", name="Statements")).to_be_visible()
    page.fill("#acct_label", "Sample account")
    page.fill("#acct_token", "SYNTH_A")
    page.get_by_role("button", name="Add account").click()
    page.set_input_files("#up_file", str(Path("tests/fixtures/statements/supported.csv").resolve()))
    page.get_by_role("button", name="Upload", exact=True).click()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    with Session(db_engine) as db:                      # the operator worker; not a public API
        worker.run_once(db)
    page.get_by_role("button", name="Refresh status").click()
    expect(page.get_by_text("Needs your review")).to_be_visible()
    expect(page.get_by_text("Synthetic salary")).to_be_visible()
    expect(page.get_by_role("cell", name="₹45,000.00")).to_be_visible()
    expect(page.get_by_text("Balance check")).to_be_visible()
    page.get_by_role("button", name="Confirm import").click()
    expect(page.get_by_text("Imported", exact=True)).to_be_visible()
    assert not tracker["errors"], tracker["errors"]


def test_statements_page_says_unavailable_when_feature_is_off(page, live_url, tracker):
    signup(page, live_url)
    page.goto(f"{live_url}/app/#/statements")
    expect(page.get_by_text("Statement upload is not available yet")).to_be_visible()
    assert not page.locator("#up_file").count()


def test_theme_toggle_switches_persists_and_changes_colours(page, live_url, tracker):
    page.emulate_media(color_scheme="light")
    page.goto(f"{live_url}/app/#/")
    bg = lambda: page.evaluate("getComputedStyle(document.body).backgroundColor")
    light_bg = bg()
    page.get_by_role("button", name="Switch to dark mode").click()
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
    assert bg() != light_bg
    page.reload()                                              # the choice survives a reload, applied before first paint
    assert page.evaluate("document.documentElement.getAttribute('data-theme')") == "dark"
    page.get_by_role("button", name="Switch to light mode").click()
    assert bg() == light_bg
    assert not tracker["errors"], tracker["errors"]


def _metrics(page):
    return page.evaluate("[...document.querySelectorAll('.metric .value')].map(e => e.textContent)")


def test_numbers_animate_then_settle_on_the_exact_values(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    run_analysis(page)
    page.wait_for_timeout(2500)                                           # animation is about 1.1 s
    settled = _metrics(page)
    assert settled[0] == "87" and settled[3] == "₹60,000", settled        # exact, not an in-between frame
    dash = page.evaluate("[...document.querySelectorAll('.donut-wrap circle')].map(c => c.getAttribute('stroke-dasharray').split(' ')[0])")
    assert len(dash) >= 2 and all(float(x) > 0 for x in dash), dash
    assert not tracker["errors"], tracker["errors"]


def test_reduced_motion_shows_final_numbers_immediately(page, live_url, tracker):
    page.emulate_media(reduced_motion="reduce")
    signup(page, live_url)
    save_profile(page)
    run_analysis(page)
    assert _metrics(page)[0] == "87"                                      # no counting up when the user asks for less motion
    assert not tracker["errors"], tracker["errors"]


# ---- core journeys: monthly report, mapped CSV import, manual credit score --------------------------------------
@pytest.fixture()
def synthetic(monkeypatch, tmp_path):
    from backend.core.config import config
    from cryptography.fernet import Fernet
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))
    return tmp_path


def add_account(page, live_url):
    page.goto(f"{live_url}/app/#/statements")
    expect(page.get_by_role("heading", name="Statements")).to_be_visible()
    page.fill("#acct_label", "Sample account")
    page.fill("#acct_token", "SYNTH_A")
    page.get_by_role("button", name="Add account").click()
    expect(page.locator("#mp_acct")).to_be_visible()


def test_monthly_report_shows_checked_totals_and_does_not_invent_investable_money(page, live_url, tracker, db_engine, synthetic):
    from pathlib import Path
    from sqlalchemy.orm import Session
    from backend.workers import statements as worker
    signup(page, live_url)
    add_account(page, live_url)
    page.set_input_files("#up_file", str(Path("tests/fixtures/statements/supported.csv").resolve()))
    page.get_by_role("button", name="Upload", exact=True).click()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    with Session(db_engine) as db:
        worker.run_once(db)
    page.get_by_role("button", name="Refresh status").click()
    page.get_by_role("button", name="Confirm import").click()
    expect(page.get_by_text("Imported", exact=True)).to_be_visible()
    page.goto(f"{live_url}/app/#/monthly")
    expect(page.get_by_role("heading", name="Monthly report")).to_be_visible()
    page.fill("#mr_month", "2026-01")
    page.get_by_role("button", name="Create report").click()
    expect(page.get_by_text("Report for 2026-01")).to_be_visible()
    expect(page.get_by_text("₹45,000.00").first).to_be_visible()                       # money in
    expect(page.get_by_text("Spending was higher than money in")).to_be_visible()
    expect(page.get_by_text("The gap is ₹10,000.00")).to_be_visible()
    assert not page.get_by_text("You can invest").count()
    expect(page.get_by_role("cell", name="Synthetic salary")).to_be_visible()
    expect(page.get_by_text("Net worth is not shown")).to_be_visible()
    # filters narrow the list, persist across a reload, and a row opens to show where it came from
    page.select_option("#mr_cat", "income")
    expect(page.get_by_role("cell", name="Synthetic expenses")).to_have_count(0)
    page.fill("#mr_find", "salary")
    page.get_by_role("button", name="Details").click()
    expect(page.get_by_text("Where this came from")).to_be_visible()
    expect(page.get_by_text("Statement rows: import")).to_be_visible()
    page.fill("#mr_find", "zzz")
    expect(page.get_by_text("No entries match these filters.")).to_be_visible()
    page.fill("#mr_find", "salary")
    page.goto(f"{live_url}/app/#/profile")                           # leave and come back (a reload would log out)
    expect(page.get_by_role("heading", name="Your profile")).to_be_visible()
    page.goto(f"{live_url}/app/#/monthly")
    expect(page.locator("#mr_cat")).to_have_value("income")
    expect(page.locator("#mr_find")).to_have_value("salary")
    assert not tracker["errors"], tracker["errors"]


def write_csv(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_mapped_csv_preview_problems_block_import_then_confirm_works(page, live_url, tracker, synthetic):
    signup(page, live_url)
    add_account(page, live_url)
    bad = write_csv(synthetic, "bad.csv", "Date,Narration,Amount\n01/10/2025,Rent,abc\n02/10/2025,=HYPERLINK(1),500.00\n")
    page.set_input_files("#mp_file", bad)
    page.get_by_role("button", name="Preview").click()
    expect(page.get_by_text("Fix these before importing")).to_be_visible()
    expect(page.get_by_text("The amount is not a valid number")).to_be_visible()
    assert not page.get_by_role("button", name="Import").count()
    good = write_csv(synthetic, "good.csv", "Date,Narration,Amount\n01/10/2025,Salary,\"1,00,000.50\"\n02/10/2025,=HYPERLINK(1),-2500.25\n")
    page.set_input_files("#mp_file", good)
    page.get_by_role("button", name="Preview").click()
    expect(page.get_by_text("Text starting with = + - or @ was made safe.")).to_be_visible()
    expect(page.get_by_role("cell", name="₹1,00,000.50")).to_be_visible()
    expect(page.get_by_role("cell", name="'=HYPERLINK(1)")).to_be_visible()            # neutralised, shown as plain text
    page.get_by_role("button", name="Import 2 rows for review").click()
    expect(page.get_by_text("Imported. Review the rows")).to_be_visible()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    assert not tracker["errors"], tracker["errors"]


def test_scanned_or_image_file_gets_clear_message_not_an_upload(page, live_url, tracker, synthetic):
    signup(page, live_url)
    add_account(page, live_url)
    page.set_input_files("#mp_file", write_csv(synthetic, "scan.png", "not really an image"))
    expect(page.get_by_text("Scanned files, photos and PDFs are not supported yet")).to_be_visible()
    assert not page.locator("#mp_fmt").count()
    assert not tracker["errors"], tracker["errors"]


def test_manual_credit_score_is_dated_unverified_and_unknown_stays_unknown(page, live_url, tracker):
    signup(page, live_url)
    save_profile(page)
    page.goto(f"{live_url}/app/#/credit")
    expect(page.get_by_text("No credit score on record. We never guess one.")).to_be_visible()
    page.fill("#ms_score", "750")
    page.fill("#ms_label", "My bank app")
    page.get_by_role("button", name="Save entry").click()
    expect(page.get_by_text("Your entry: 750")).to_be_visible()
    expect(page.get_by_text("User-reported and unverified.").first).to_be_visible()
    page.fill("#ms_score", "950")
    page.get_by_role("button", name="Save entry").click()
    expect(page.get_by_text("Enter a score from 300 to 900")).to_be_visible()
    page.check("#ms_unknown")
    page.get_by_role("button", name="Save entry").click()
    expect(page.get_by_text("No credit score on record. We never guess one.")).to_be_visible()
    assert not tracker["errors"], tracker["errors"]


def test_demo_is_labelled_sample_makes_no_requests_and_is_reachable_signed_out(page, live_url, tracker):
    requests = []
    page.on("request", lambda r: requests.append(r.url) if "/app/" not in r.url else None)
    page.goto(f"{live_url}/app/#/")
    page.get_by_role("link", name="See a sample").click()
    expect(page.get_by_role("heading", name="Sample report")).to_be_visible()
    expect(page.get_by_text("Sample data, not yours.")).to_be_visible()
    expect(page.get_by_text("Sample salary")).to_be_visible()
    assert requests == [], requests                                   # cannot mix with a real account: no API calls at all
    assert not tracker["errors"], tracker["errors"]


def test_first_run_checklist_and_privacy_notice_before_upload(page, live_url, tracker, synthetic):
    signup(page, live_url)
    page.goto(f"{live_url}/app/#/dashboard")
    expect(page.get_by_text("Getting started")).to_be_visible()
    expect(page.get_by_role("link", name="Tell us about your money")).to_be_visible()
    expect(page.get_by_role("link", name="Add a bank statement and confirm it")).to_be_visible()
    page.goto(f"{live_url}/app/#/statements")
    expect(page.get_by_text("Before you upload")).to_be_visible()
    expect(page.get_by_text("never sent to an AI model")).to_be_visible()
    expect(page.get_by_text("PDFs, photos and scanned pages")).to_be_visible()
    assert not tracker["errors"], tracker["errors"]


def test_wrong_password_on_sensitive_actions_keeps_the_user_signed_in(page, live_url, tracker):
    signup(page, live_url)
    page.goto(f"{live_url}/app/#/settings")
    page.fill("#pw_cur", "Not-the-right-password-1!")
    page.fill("#pw_new", "Another-Throwaway-5582!")
    page.get_by_role("button", name="Change password").click()
    expect(page.locator("[role=alert]").first).to_be_visible()
    expect(page.get_by_role("heading", name="Settings")).to_be_visible()      # still signed in, not bounced to login
    page.fill("#ex_pw", "Not-the-right-password-1!")
    page.get_by_role("button", name="Prepare my download").click()
    expect(page.get_by_role("heading", name="Settings")).to_be_visible()
    expect(page.locator("#ex_pw")).to_have_value("")                   # the password is never left in the field


def test_export_download_and_account_deletion_with_receipt(page, live_url, tracker, db_engine, monkeypatch, tmp_path):
    import json as _json
    from cryptography.fernet import Fernet
    from backend.core.config import config
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', _json.dumps({'v1': Fernet.generate_key().decode()}))
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(tmp_path / 'journal.db'))
    signup(page, live_url)
    page.goto(f"{live_url}/app/#/settings")
    page.fill("#ex_pw", PASSWORD)
    page.get_by_role("button", name="Prepare my download").click()
    expect(page.get_by_text("Your file is ready until")).to_be_visible()
    with page.expect_download() as info:
        page.get_by_role("button", name="Download my data (JSON)").click()
    data = _json.loads(open(info.value.path(), encoding="utf-8").read())
    assert isinstance(data, dict) and data
    # deletion needs the exact word and the password, then shows a one-time receipt
    page.fill("#del_pw", PASSWORD)
    page.fill("#del_word", "delete")
    page.get_by_role("button", name="Delete my account").click()
    expect(page.get_by_text("Type DELETE exactly to confirm.")).to_be_visible()
    page.fill("#del_word", "DELETE")
    page.get_by_role("button", name="Delete my account").click()
    expect(page.get_by_text("Your account has been closed.")).to_be_visible()
    receipt = page.locator("#del_receipt").input_value()
    assert len(receipt) == 43
    page.get_by_role("button", name="I saved it - sign out").click()
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()


def test_support_access_is_opt_in_per_file_and_revocable(page, live_url, tracker, db_engine, synthetic):
    from pathlib import Path
    signup(page, live_url)
    page.goto(f"{live_url}/app/#/settings")
    expect(page.get_by_text("Support staff have not looked at anything of yours.")).to_be_visible()
    add_account(page, live_url)
    page.set_input_files("#up_file", str(Path("tests/fixtures/statements/supported.csv").resolve()))
    page.get_by_role("button", name="Upload", exact=True).click()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    page.goto(f"{live_url}/app/#/settings")
    page.get_by_role("button", name="Allow support to open this file").click()
    expect(page.get_by_text("Support can open this one file until")).to_be_visible()
    page.get_by_role("button", name="Stop this access now").click()
    expect(page.get_by_text("Access stopped.")).to_be_visible()
    assert not tracker["errors"], tracker["errors"]
