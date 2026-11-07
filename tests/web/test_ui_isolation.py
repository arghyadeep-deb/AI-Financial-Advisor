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
