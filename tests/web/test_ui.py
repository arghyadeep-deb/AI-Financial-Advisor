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
    page.get_by_role("link", name="Advisor chat").click()
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
