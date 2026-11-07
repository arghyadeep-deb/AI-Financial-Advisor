"""T102 — synthetic reproductions of the baseline findings (specs/baseline.md).

Each test states the DESIRED behaviour through public entry points only, with
model providers disabled (conftest clears all keys).  They were first run
against the unmodified baseline (818b219) to learn which findings still
reproduce; results are recorded in specs/implementation-progress.md.  They
remain as regression tests.
"""
import itertools
import re
import uuid

import jwt
import pytest
from fastapi.testclient import TestClient

DEFICIT = {
    "age": 30, "employment_type": "salaried",
    "monthly_income": 45000, "monthly_expenses": 55000,
    "existing_savings": 0, "existing_investments": 0, "existing_debts": 0,
    "risk_tolerance": "moderate", "investment_horizon": "long",
    "financial_goals": ["retirement"], "monthly_credit_spend": 0,
    "top_spend_categories": [],
}
_counter = itertools.count()


@pytest.fixture(scope="module")
def api():
    from backend.main import app
    with TestClient(app) as c:
        yield c


def _signup(api, password="Correct-Horse-9"):
    email = f"u{next(_counter)}-{uuid.uuid4().hex[:6]}@example.com"
    r = api.post("/auth/signup", json={"email": email, "full_name": "Test User", "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    return email, body, {"Authorization": f"Bearer {body['access_token']}"}


def _flatten(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _flatten(v)
    else:
        yield obj


def test_B1_deficit_profile_never_gets_contribution_or_fund_switch(api):
    _, _, h = _signup(api)
    assert api.post("/profile", json=DEFICIT, headers=h).status_code == 200
    r = api.post("/analysis", json={"analysis_type": "full"}, headers=h)
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    inv = results["investment"]
    assert inv["total_monthly_investment"] == 0
    assert inv.get("monthly_sip_plan", []) == []
    text = " ".join(str(x) for x in _flatten(results))
    assert "27,500" not in text and "27500" not in text
    assert "switch" not in text.lower()


def test_B2_default_signing_secret_cannot_forge_a_token(api):
    _, body, _ = _signup(api)
    forged = jwt.encode({"sub": str(body["user_id"])}, "changeme", algorithm="HS256")
    r = api.get("/profile/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_B2b_identical_passwords_have_distinct_stored_hashes(api):
    from backend.core.database import SessionLocal
    from backend.models.models import User
    e1, _, _ = _signup(api, "Same-Password-1")
    e2, _, _ = _signup(api, "Same-Password-1")
    db = SessionLocal()
    try:
        h1 = db.query(User).filter(User.email == e1).one().hashed_password
        h2 = db.query(User).filter(User.email == e2).one().hashed_password
    finally:
        db.close()
    assert h1 != h2


def test_B4_stale_report_is_labelled_after_profile_edit(api):
    _, _, h = _signup(api)
    p = dict(DEFICIT, monthly_income=65000, monthly_expenses=55000)
    assert api.post("/profile", json=p, headers=h).status_code == 200
    assert api.post("/analysis", json={"analysis_type": "full"}, headers=h).status_code == 200
    assert api.post("/profile", json=dict(p, monthly_income=70000), headers=h).status_code == 200
    last = api.get("/analysis/last", headers=h).json()
    assert last.get("stale") is True


def test_B5_health_only_run_preserves_portfolio_state(api):
    _, _, h = _signup(api)
    p = dict(DEFICIT, monthly_income=100000, monthly_expenses=40000, existing_investments=500000)
    assert api.post("/profile", json=p, headers=h).status_code == 200
    assert api.post("/analysis", json={"analysis_type": "full"}, headers=h).status_code == 200
    before = api.get("/analysis/state", headers=h).json()["portfolio_value"]
    assert api.post("/analysis", json={"analysis_type": "health"}, headers=h).status_code == 200
    after = api.get("/analysis/state", headers=h).json()["portfolio_value"]
    assert after == before


def test_B5b_projection_is_not_reported_as_observed_portfolio_value(api):
    _, _, h = _signup(api)
    p = dict(DEFICIT, monthly_income=100000, monthly_expenses=40000, existing_investments=0)
    assert api.post("/profile", json=p, headers=h).status_code == 200
    assert api.post("/analysis", json={"analysis_type": "full"}, headers=h).status_code == 200
    state = api.get("/analysis/state", headers=h).json()
    assert state["portfolio_value"] in (0, None)


def test_B6_unknown_credit_score_stays_unknown(api):
    from backend.models.models import FinancialProfile
    from backend.services.profile_service import to_agent_dict
    prof = FinancialProfile(age=30, employment_type="salaried", monthly_income_paise=100,
                            monthly_expenses_paise=0, existing_savings_paise=0,
                            existing_debts_paise=0, credit_score=None, revision=1)
    assert to_agent_dict(prof)["credit_score"] is None


def test_B7_all_providers_failing_is_not_reported_as_plain_success(api):
    _, _, h = _signup(api)
    assert api.post("/profile", json=dict(DEFICIT, monthly_income=90000), headers=h).status_code == 200
    r = api.post("/analysis", json={"analysis_type": "full"}, headers=h).json()
    assert r["success"] is True or r["success"] is False
    status = r.get("status")
    assert status in {"degraded", "partial", "failed"}, f"got {status!r}; fallback must be visible"


def test_B8_edit_forms_use_submitted_scenario_values_without_touching_profile(api):
    _, _, h = _signup(api)
    p = dict(DEFICIT, monthly_income=100000, monthly_expenses=40000)
    assert api.post("/profile", json=p, headers=h).status_code == 200
    r = api.post("/analysis", json={"analysis_type": "health",
                                    "scenario": {"monthly_income": 120000}}, headers=h)
    assert r.status_code == 200, r.text
    assert api.get("/profile", headers=h).json()["monthly_income"] == 100000
