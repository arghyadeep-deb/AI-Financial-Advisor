"""T104-T106 / US1 — consistent facts, revisions, scenarios, staleness, outages (real endpoints, providers disabled)."""
import json
import uuid

import pytest

from backend.models.models import Analysis, FinancialProfile, FinancialState, ProfileRevision
from backend.services.profile_service import ProfileService

PW = "Correct-Horse-9"
BASE = {"age": 30, "employment_type": "salaried", "monthly_income": 45000, "monthly_expenses": 55000,
        "existing_savings": 0, "existing_investments": 0, "existing_debts": 0,
        "risk_tolerance": "moderate", "investment_horizon": "long", "financial_goals": ["retirement"]}
R = 100


def user(client):
    body = client.post("/auth/signup", json={"email": f"f-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "Fin User", "password": PW}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user_id"]


def save(client, h, **over):
    r = client.post("/profile", json={**BASE, **over}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def run(client, h, kind="full", **extra):
    r = client.post("/analysis", json={"analysis_type": kind, **extra}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def flatten(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from flatten(v)
    elif isinstance(o, list):
        for v in o:
            yield from flatten(v)
    else:
        yield o


# ── profile revisions & exact money ────────────────────────────────────────
def test_profile_save_creates_revisions_only_on_change(client):
    h, uid = user(client)
    p1 = save(client, h)
    assert p1["revision"] == 1 and p1["monthly_income_paise"] == 4_500_000 and p1["monthly_expenses_paise"] == 5_500_000
    assert save(client, h)["revision"] == 1                                   # identical save: no new revision
    p2 = save(client, h, monthly_income=65000)
    assert p2["revision"] == 2 and p2["monthly_income_paise"] == 6_500_000
    db = client.session_factory()
    assert [r.revision for r in db.query(ProfileRevision).filter_by(user_id=uid).order_by(ProfileRevision.revision)] == [1, 2]
    snap2 = db.query(ProfileRevision).filter_by(user_id=uid, revision=2).one().snapshot
    assert snap2["monthly_income_paise"] == 6_500_000 and all(not isinstance(v, float) for v in snap2.values())
    row = db.query(FinancialProfile).filter_by(user_id=uid).one()
    assert row.monthly_income == 65000.0 and row.monthly_income_paise == 6_500_000      # legacy mirror derived from paise
    db.close()


def test_optimistic_concurrency_conflict_returns_409(client):
    h, _ = user(client)
    save(client, h)
    save(client, h, monthly_income=50000)                                     # now revision 2
    r = client.post("/profile", json={**BASE, "monthly_income": 51000, "expected_revision": 1}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "revision_conflict"
    assert client.get("/profile", headers=h).json()["monthly_income"] == 50000
    ok = client.post("/profile", json={**BASE, "monthly_income": 51000, "expected_revision": 2}, headers=h)
    assert ok.status_code == 200 and ok.json()["revision"] == 3


@pytest.mark.parametrize("field,value", [
    ("monthly_income", 0), ("monthly_income", -5), ("monthly_expenses", -1), ("monthly_income", 12.345),
    ("monthly_income", 1e30), ("existing_savings", "abc"), ("existing_debts", 10 ** 15),
    ("credit_score", 299), ("credit_score", 901), ("monthly_debt_payment", -1),
])
def test_invalid_money_and_scores_are_rejected_with_field_errors(client, field, value):
    h, _ = user(client)
    r = client.post("/profile", json={**BASE, field: value}, headers=h)
    assert r.status_code == 422
    assert any(f["field"] == field for f in r.json()["field_errors"])
    assert str(value) not in json.dumps(r.json()["field_errors"]) or isinstance(value, (int, float))


def test_nan_and_infinity_in_raw_json_are_rejected(client):
    h, _ = user(client)
    for token in ("NaN", "Infinity", "-Infinity"):
        raw = json.dumps({**BASE}).replace("45000", token)
        r = client.post("/profile", content=raw, headers={**h, "Content-Type": "application/json"})
        assert r.status_code == 422, token


# ── US1: the deficit story ─────────────────────────────────────────────────
def test_FIN01_deficit_is_the_same_everywhere_and_nothing_is_advised(client):
    h, _ = user(client)
    save(client, h)
    out = run(client, h)
    snap = out["snapshot"]
    assert snap["surplus_paise"] == -10_000 * R and snap["shortfall_paise"] == 10_000 * R
    assert snap["available_contribution_paise"] == 0
    r = out["results"]
    assert r["health"]["monthly_shortfall"] == 10000 and r["health"]["monthly_surplus"] == -10000
    assert r["health"]["raw_metrics"]["monthly_shortfall"] == 10000
    inv = r["investment"]
    assert inv["total_monthly_investment"] == 0 and inv["monthly_sip_plan"] == []
    assert inv["contribution"]["status"] == "none"
    assert r["summary"]["key_numbers"]["monthly_shortfall"] == 10000
    assert r["summary"]["key_numbers"]["recommended_sip"] == 0
    assert r["rebalance"]["status"] == "unavailable" and r["rebalance"]["rebalancing_actions"] == []
    blob = " ".join(str(x) for x in flatten(r)).lower()
    assert "27,500" not in blob and "27500" not in blob and "switch" not in blob
    assert "monthly deficit" in blob


def test_income_edit_makes_old_result_stale_and_fresh_run_uses_new_income(client):
    h, _ = user(client)
    save(client, h)
    first = run(client, h)
    assert first["profile_revision"] == 1 and first["stale"] is False
    save(client, h, monthly_income=65000)
    last = client.get("/analysis/last", headers=h).json()
    assert last["stale"] is True and last["current_revision"] == 2 and last["profile_revision"] == 1
    assert client.get("/analysis/state", headers=h).json()["stale"] is True
    fresh = run(client, h)
    assert fresh["snapshot"]["surplus_paise"] == 10_000 * R and fresh["profile_revision"] == 2
    # zero savings => the whole 10,000 goes to the emergency fund first; nothing is invested
    assert fresh["snapshot"]["reserve_funding_paise"] == 10_000 * R
    assert fresh["results"]["investment"]["total_monthly_investment"] == 0
    last = client.get("/analysis/last", headers=h).json()
    assert last["stale"] is False and last["profile_revision"] == 2


def test_in_flight_analysis_for_an_old_revision_never_becomes_current(client, monkeypatch):
    h, uid = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000, existing_savings=300000)
    run(client, h, "health")
    before_state = client.get("/analysis/state", headers=h).json()
    from agents.graph_executor import GraphExecutor
    real = GraphExecutor.execute_single

    def racing(self, name, profile):
        out = real(self, name, profile)
        db = client.session_factory()                  # another request edits the profile mid-run
        try:
            ProfileService(db).save(uid, {**BASE, "monthly_income": __import__("decimal").Decimal("20000"),
                                          "monthly_expenses": __import__("decimal").Decimal("15000"),
                                          "existing_savings": __import__("decimal").Decimal("0"),
                                          "existing_investments": __import__("decimal").Decimal("0"),
                                          "existing_debts": __import__("decimal").Decimal("0"),
                                          "monthly_credit_spend": __import__("decimal").Decimal("0"),
                                          "monthly_debt_payment": None, "credit_score": None})
        finally:
            db.close()
        return out

    monkeypatch.setattr(GraphExecutor, "execute_single", racing)
    out = run(client, h, "health")
    assert out["status"] == "superseded" and out["stale"] is True and out["success"] is False
    assert client.get("/analysis/state", headers=h).json()["health_score"] == before_state["health_score"]
    last = client.get("/analysis/last", headers=h).json()
    assert last["stale"] is True                       # the only usable result is flagged outdated


# ── scenarios never touch the saved profile ────────────────────────────────
def test_scenario_uses_submitted_values_but_leaves_profile_and_current_results_alone(client):
    h, uid = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000)
    base = run(client, h, "health")
    scen = run(client, h, "health", scenario={"monthly_income": 120000})
    assert scen["is_scenario"] is True and scen["snapshot"]["income_paise"] == 12_000_000
    assert scen["results"]["health"]["monthly_surplus"] == 80000
    assert base["results"]["health"]["monthly_surplus"] == 60000
    prof = client.get("/profile", headers=h).json()
    assert prof["monthly_income"] == 100000 and prof["revision"] == 1
    last = client.get("/analysis/last", headers=h).json()
    assert last["analysis_id"] == base["analysis_id"]          # scenario run is not "the current analysis"
    db = client.session_factory()
    assert db.query(ProfileRevision).filter_by(user_id=uid).count() == 1
    assert db.query(Analysis).filter_by(user_id=uid, is_scenario=True).count() == 1
    db.close()


def test_scenario_rejects_unknown_fields_and_bad_values(client):
    h, _ = user(client)
    save(client, h)
    assert client.post("/analysis", json={"analysis_type": "health", "scenario": {"user_id": 2}}, headers=h).status_code == 422
    assert client.post("/analysis", json={"analysis_type": "health", "scenario": {"monthly_income": -1}}, headers=h).status_code == 422


# ── unknown stays unknown / distinct debt inputs / observed vs projected ───
def test_unknown_credit_score_is_excluded_not_defaulted(client):
    h, _ = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000)
    out = run(client, h, "health")
    health = out["results"]["health"]
    assert health["components"]["credit_score"]["value"] == "unknown"
    assert health["components"]["credit_score"]["score"] is None
    assert health["score_basis"] == {"points": health["score_basis"]["points"], "available_points": 90,
                                     "excluded": ["credit_score"], "partial": True}
    assert "credit_score" in out["snapshot"]["missing_inputs"]
    assert not any("credit score" in (w.get("title", "")).lower() for w in health.get("detailed_warnings", []))
    save(client, h, monthly_income=100000, monthly_expenses=40000, credit_score=780)
    known = run(client, h, "health")["results"]["health"]
    assert known["score_basis"]["available_points"] == 100 and known["components"]["credit_score"]["value"] == "780"


def test_debt_balance_and_payment_are_distinct_inputs(client):
    h, _ = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000, existing_savings=240000, existing_debts=500000)
    out = run(client, h, "investment")
    assert out["snapshot"]["contribution_status"] == "unavailable"
    assert out["results"]["investment"]["total_monthly_investment"] == 0
    assert "monthly_debt_payment" in out["snapshot"]["missing_inputs"]
    save(client, h, monthly_income=100000, monthly_expenses=40000, existing_savings=240000,
         existing_debts=500000, monthly_debt_payment=10000)
    ok = run(client, h, "investment")
    assert ok["snapshot"]["available_contribution_paise"] == 45_000 * R
    inv = ok["results"]["investment"]
    assert 0 < inv["total_monthly_investment"] <= 45_000
    assert sum(p["monthly_amount"] for p in inv["monthly_sip_plan"]) == inv["total_monthly_investment"]


def test_health_only_run_preserves_other_sections_and_projection_is_not_observed(client):
    h, _ = user(client)
    save(client, h, monthly_income=150000, monthly_expenses=40000, existing_savings=300000,
         existing_investments=500000)
    full = run(client, h)
    assert full["results"]["investment"]["projected_corpus_10yr"] > 0
    state = client.get("/analysis/state", headers=h).json()
    assert state["portfolio_value"] == 500000                      # the declared amount, never the projection
    health_run = run(client, h, "health")
    last = client.get("/analysis/last", headers=h).json()
    assert {"health", "investment", "summary"} <= set(last["results"])
    assert last["section_status"]["_meta"]["investment"]["analysis_id"] == full["analysis_id"]
    assert last["section_status"]["_meta"]["health"]["analysis_id"] == health_run["analysis_id"]
    assert client.get("/analysis/state", headers=h).json()["portfolio_value"] == 500000
    assert full["results"]["investment"]["projection_label"].startswith("Illustrative projection")


def test_latest_per_section_prefers_newer_quick_over_older_full(client):
    h, _ = user(client)
    save(client, h, monthly_income=150000, monthly_expenses=40000, existing_savings=300000)
    full = run(client, h)
    quick = run(client, h, "quick")
    last = client.get("/analysis/last", headers=h).json()
    assert last["analysis_id"] == quick["analysis_id"]
    assert last["section_status"]["_meta"]["health"]["analysis_id"] == quick["analysis_id"]
    assert last["section_status"]["_meta"]["summary"]["analysis_id"] == full["analysis_id"]


def test_legacy_rows_with_unverified_money_must_be_reentered(client):
    h, uid = user(client)
    save(client, h)
    db = client.session_factory()
    row = db.query(FinancialProfile).filter_by(user_id=uid).one()
    row.monthly_income_paise = None
    db.commit()
    db.close()
    prof = client.get("/profile", headers=h).json()
    assert prof["needs_reentry"] == ["monthly_income"] and prof["monthly_income"] is None
    r = client.post("/analysis", json={"analysis_type": "health"}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "profile_incomplete"


# ── model failure modes ────────────────────────────────────────────────────
def test_total_provider_outage_keeps_verified_facts_and_is_not_plain_success(client):
    h, _ = user(client)
    save(client, h)
    out = run(client, h)
    assert out["status"] == "degraded" and out["success"] is False
    assert out["snapshot"]["shortfall_paise"] == 1_000_000
    for name in ("health", "investment", "credit", "optimizer", "simulation", "summary"):
        assert out["section_status"][name]["status"] == "degraded"
        assert out["section_status"][name]["source"] in ("deterministic_fallback", "deterministic")
    assert out["results"]["summary"]["narrative_source"] == "deterministic_fallback"
    assert "10,000" in out["results"]["summary"]["executive_summary"]


def test_model_cannot_publish_a_surplus_during_a_deficit(client, monkeypatch):
    import agents.summary_agent as sa
    fabricated = {"executive_summary": "Great news! You have a healthy monthly surplus of Rs 10,000 to invest.",
                  "top_priorities": [{"priority": 1, "action": "Start a SIP of Rs 27,500 today",
                                      "timeline": "now", "impact": "high"}],
                  "quick_wins": [], "personalized_message": "Keep going",
                  "key_numbers": {"monthly_surplus": 10000, "recommended_sip": 27500}}
    monkeypatch.setattr(sa, "call_llm", lambda **kw: json.dumps(fabricated))
    h, _ = user(client)
    save(client, h)
    out = run(client, h)
    s = out["results"]["summary"]
    assert s["narrative_source"] == "deterministic_after_rejection"
    assert s["narrative_rejected"] == "claims_surplus_during_deficit"
    assert s["key_numbers"]["monthly_surplus"] == -10000 and s["key_numbers"]["recommended_sip"] == 0
    assert "27,500" not in json.dumps(s) and "healthy monthly surplus" not in json.dumps(s)
    assert out["section_status"]["summary"]["narrative"]["narrative_rejected"] == "claims_surplus_during_deficit"


def test_model_amount_not_traceable_to_deterministic_outputs_is_rejected(client, monkeypatch):
    import agents.summary_agent as sa
    h, _ = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000, existing_savings=240000)
    bad = {"executive_summary": "You will have Rs 98,76,543 by next year.", "top_priorities": [], "quick_wins": [],
           "personalized_message": "ok", "key_numbers": {}}
    monkeypatch.setattr(sa, "call_llm", lambda **kw: json.dumps(bad))
    s = run(client, h)["results"]["summary"]
    assert s["narrative_rejected"] == "unsupported_amount" and "98,76,543" not in json.dumps(s)


def test_model_cannot_override_sip_plan_or_tax_claims_for_a_deficit(client, monkeypatch):
    import agents.investment_agent as ia
    bogus = {"monthly_sip_plan": [{"instrument": "HDFC Flexi Cap Fund", "category": "Equity",
                                   "monthly_amount": 27500, "rationale": "grow fast"}],
             "total_monthly_investment": 27500, "key_advice": "Invest Rs 27,500 now",
             "tax_saving_plan": {"total_tax_saved_annually": 99999},
             "stock_recommendations": [{"company": "TCS", "symbol": "TCS", "allocation_percent": 50}],
             "lumpsum_suggestions": [{"instrument": "Nifty 50 Index Fund", "amount": 500000}]}
    monkeypatch.setattr(ia, "call_llm", lambda **kw: json.dumps(bogus))
    h, _ = user(client)
    save(client, h)
    inv = run(client, h, "investment")["results"]["investment"]
    assert inv["monthly_sip_plan"] == [] and inv["total_monthly_investment"] == 0
    assert inv["tax_saving_plan"]["total_tax_saved_annually"] is None
    assert inv["stock_recommendations"] == [] and inv["lumpsum_suggestions"] == []
    assert inv["named_products"]["status"] == "gated"


def test_named_products_are_generic_unless_explicitly_enabled(client):
    h, _ = user(client)
    save(client, h, monthly_income=200000, monthly_expenses=40000, existing_savings=240000)
    inv = run(client, h, "investment")["results"]["investment"]
    assert inv["monthly_sip_plan"], "an affordable profile still gets a plan"
    text = json.dumps(inv)
    for brand in ("Mirae", "UTI", "Parag Parikh", "HDFC", "ICICI"):
        assert brand not in text
    assert inv["stock_recommendations"] == []
    assert sum(p["monthly_amount"] for p in inv["monthly_sip_plan"]) <= inv["contribution"]["available_monthly"]


def test_failed_agent_section_is_reported_failed_not_silently_successful(client, monkeypatch):
    import agents.credit_agent as ca
    monkeypatch.setattr(ca, "run_credit_agent", lambda p: (_ for _ in ()).throw(RuntimeError("boom with secret-marker-123")))
    h, _ = user(client)
    save(client, h, monthly_income=100000, monthly_expenses=40000)
    out = run(client, h, "quick")
    assert out["status"] == "partial" and out["section_status"]["credit"]["status"] == "failed"
    assert "secret-marker-123" not in json.dumps(out["section_status"])        # statuses carry codes, not exception text
