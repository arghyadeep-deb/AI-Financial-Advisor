"""T1401: the statements screen says plainly what is supported and what is not (scanned, photo, PDF, password-protected)."""
import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

from tests.web.test_ui import add_account, live_url, signup, synthetic, tracker, write_csv  # noqa: E402,F401


def test_unsupported_kinds_are_named_before_and_after_a_try(page, live_url, tracker, db_engine, synthetic):
    from sqlalchemy.orm import Session
    from backend.workers import statements as worker
    signup(page, live_url)
    add_account(page, live_url)
    expect(page.get_by_text("Accepted: CSV or plain-text files.")).to_be_visible()
    expect(page.get_by_text("password-protected")).to_be_visible()
    expect(page.get_by_text("nothing is read by OCR")).to_be_visible()
    # a PDF is queued and then the parser refuses it; the user is told in plain words and nothing reaches their records
    page.set_input_files("#up_file", write_csv(synthetic, "stmt.pdf", "%PDF-1.7 not a real statement"))
    page.get_by_role("button", name="Upload", exact=True).click()
    expect(page.get_by_text("Waiting to be read")).to_be_visible()
    with Session(db_engine) as db:
        worker.run_once(db)
    page.get_by_role("button", name="Refresh status").click()
    expect(page.get_by_text("PDF statements are not supported yet")).to_be_visible()
    expect(page.get_by_role("button", name="Confirm import")).to_have_count(0)
    # a photo is refused in the CSV mapper before anything is sent
    page.set_input_files("#mp_file", write_csv(synthetic, "photo.jpg", "x"))
    expect(page.get_by_text("Scanned files, photos and PDFs are not supported yet")).to_be_visible()
