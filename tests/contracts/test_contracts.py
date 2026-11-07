"""T114/T115 — one set of numbers across API, chat, summary and legacy state; precedence never double-counts."""
import uuid

import pytest

import backend.services.chat_service as cs
from engines.precedence import Candidate, resolve

PW = "Correct-Horse-9"
PROFILE = {"age": 30, "employment_type": "salaried", "monthly_income": 90000, "monthly_expenses": 50000,
           "existing_savings": 300000, "existing_investments": 200000, "existing_debts": 100000,
           "monthly_debt_payment": 5000, "credit_score": 760,
           "risk_tolerance": "moderate", "investment_horizon": "long"}


def test_every_surface_reports_the_same_contribution(client, monkeypatch):
    body = client.post("/auth/signup", json={"email": f"k-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "Contract User", "password": PW}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.post("/profile", json=PROFILE, headers=h).status_code == 200
    out = client.post("/analysis", json={"analysis_type": "full"}, headers=h).json()
    snap = out["snapshot"]
    rupees = snap["available_contribution_paise"] // 100
    assert rupees > 0
    r = out["results"]
    # analysis sections
    assert r["investment"]["total_monthly_investment"] <= rupees
    assert r["summary"]["key_numbers"]["monthly_surplus"] == snap["surplus_paise"] // 100 == 40000
    assert r["health"]["monthly_surplus"] == 40000
    # persisted "last" and legacy state agree with the live run
    last = client.get("/analysis/last", headers=h).json()
    assert last["snapshot"]["available_contribution_paise"] == snap["available_contribution_paise"]
    # chat context is built from the same snapshot
    seen = {}
    monkeypatch.setattr(cs, "call_llm", lambda **kw: seen.update(kw) or "ok")
    client.post("/chat", json={"message": "plan?", "client_message_id": uuid.uuid4().hex}, headers=h)
    from backend.core.money import format_inr
    assert format_inr(snap["available_contribution_paise"]) in seen["system_prompt"]
    assert format_inr(snap["surplus_paise"]) in seen["system_prompt"]


def test_declared_portfolio_is_never_replaced_by_a_projection(client):
    body = client.post("/auth/signup", json={"email": f"p-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "Port User", "password": PW}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    client.post("/profile", json=PROFILE, headers=h)
    client.post("/analysis", json={"analysis_type": "full"}, headers=h)
    assert client.get("/analysis/state", headers=h).json()["portfolio_value"] == 200000


# ── precedence ─────────────────────────────────────────────────────────────
def test_higher_authority_wins_and_values_are_not_summed():
    r = resolve([Candidate("user_declared", 5_000_000), Candidate("ledger", 5_000_000)])
    assert r.value_paise == 5_000_000 and r.source == "ledger" and not r.conflict and r.is_fact


def test_disagreement_is_flagged_not_averaged():
    r = resolve([Candidate("user_declared", 5_000_000), Candidate("ledger", 4_200_000)])
    assert r.value_paise == 4_200_000 and r.source == "ledger" and r.conflict


def test_projection_and_estimates_are_never_facts():
    r = resolve([Candidate("projected", 9_999_900)])
    assert r.is_fact is False
    r2 = resolve([Candidate("user_declared", 100), Candidate("projected", 9_999_900)])
    assert r2.value_paise == 100 and r2.is_fact and not r2.conflict     # projections never create conflicts


def test_missing_and_unknown_sources():
    assert resolve([]).value_paise is None and resolve([Candidate("ledger", None)]).source is None
    with pytest.raises(ValueError):
        resolve([Candidate("rumour", 1)])
