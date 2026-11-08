"""T208: another signed-in user cannot see or touch someone else's statement account, in the real UI."""
import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

from tests.web.test_ui import add_account, live_url, signup, synthetic, tracker  # noqa: E402,F401

CALL = """async ([path, token, body]) => {
  const r = await fetch(path, {method: body ? 'POST' : 'GET',
    headers: {Authorization: 'Bearer ' + token, 'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
  return {status: r.status, text: await r.text()};
}"""


def test_other_user_cannot_see_or_use_my_statement_account(page, browser, live_url, tracker, synthetic):
    signup(page, live_url)
    add_account(page, live_url)
    token_a = tracker["token"]
    mine = page.evaluate(CALL, ["/statement-accounts", token_a, None])
    assert mine["status"] == 200
    import json
    account_id = json.loads(mine["text"])[0]["id"]

    other = browser.new_page()
    try:
        seen = {}
        other.on("request", lambda r: seen.__setitem__("token", (r.headers.get("authorization") or "")[7:] or seen.get("token")))
        signup(other, live_url)
        other.goto(f"{live_url}/app/#/statements")
        expect(other.get_by_role("heading", name="Statements")).to_be_visible()
        expect(other.get_by_text("Sample account")).to_have_count(0)        # their list does not include mine
        body = {"csv_text": "date,desc,amount\n01/01/2025,x,1.00", "mapping": {
            "delimiter": ",", "has_header": True, "date_column": 0, "date_format": "%d/%m/%Y",
            "description_column": 1, "reference_column": None, "amount_mode": "signed", "amount_column": 2}}
        denied = other.evaluate(CALL, [f"/statement-accounts/{account_id}/mapped-preview", seen["token"], body])
        assert denied["status"] == 404 and "Sample account" not in denied["text"]   # not 403: existence is not revealed
    finally:
        other.close()
    assert not tracker["errors"], tracker["errors"]


def test_review_conflict_keeps_the_users_decisions_and_lets_them_retry(page, live_url, tracker, db_engine, synthetic):
    """T1003: if the import changed on the server while the user was deciding, nothing they chose is thrown away."""
    from pathlib import Path
    from sqlalchemy.orm import Session
    from backend.models.models import StatementImport
    from backend.workers import statements as worker

    def upload_and_read(name):
        page.set_input_files("#up_file", str(Path("tests/fixtures/statements").resolve() / name))
        page.get_by_role("button", name="Upload", exact=True).click()
        expect(page.get_by_text("Waiting to be read")).to_be_visible()
        with Session(db_engine) as db:
            worker.run_once(db)
        page.get_by_role("button", name="Refresh status").click()

    signup(page, live_url)
    add_account(page, live_url)
    upload_and_read("supported.csv")
    page.get_by_role("button", name="Confirm import").click()
    expect(page.get_by_text("Imported", exact=True)).to_be_visible()
    upload_and_read("overlap.csv")
    choice = page.locator("select[aria-label^='Decision for row']").filter(
        has=page.locator("option", has_text="Different from those entries")).first   # a row that overlaps an existing entry
    expect(choice).to_be_visible()
    label = choice.get_attribute("aria-label")
    choice.select_option("distinct")
    with Session(db_engine) as db:                                         # someone else changes the import meanwhile
        job = db.query(StatementImport).order_by(StatementImport.created_at.desc()).first()
        job.revision += 1
        db.commit()
    page.get_by_role("button", name="Confirm import").click()
    expect(page.get_by_text("Revision changed")).to_be_visible()   # told it conflicted, not silently overwritten
    expect(page.get_by_label(label, exact=True)).to_have_value("distinct")   # the choice is still there
    expect(page.get_by_role("button", name="Confirm import")).to_be_enabled()   # and they can try again
    assert not tracker["errors"] or all("409" in e for e in tracker["errors"]), tracker["errors"]


def test_import_status_and_review_survive_reload_and_login_again(page, live_url, tracker, db_engine, synthetic):
    """T208 restart: the browser forgets everything on reload, so the server must still hold the import and its review."""
    from pathlib import Path
    from sqlalchemy.orm import Session
    from backend.workers import statements as worker
    from tests.web.test_ui import PASSWORD

    email = signup(page, live_url)
    add_account(page, live_url)
    page.set_input_files("#up_file", str(Path("tests/fixtures/statements/supported.csv").resolve()))
    page.get_by_role("button", name="Upload", exact=True).click()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    with Session(db_engine) as db:
        worker.run_once(db)                                                  # the worker restarts independently of the browser
    page.reload()                                                            # token lived in memory only, so this logs out
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    page.fill("#email", email)
    page.fill("#password", PASSWORD)
    page.click("button[type=submit]")
    expect(page.get_by_role("heading", name="Welcome back")).to_have_count(0)   # logged in; the app moved on
    page.goto(f"{live_url}/app/#/statements")
    expect(page.get_by_role("heading", name="Statements")).to_be_visible()
    expect(page.get_by_text("Needs your review")).to_be_visible()
    expect(page.get_by_text("Synthetic salary")).to_be_visible()
    expect(page.get_by_text("Balance check")).to_be_visible()
    assert not tracker["errors"] or all("401" in e for e in tracker["errors"]), tracker["errors"]
