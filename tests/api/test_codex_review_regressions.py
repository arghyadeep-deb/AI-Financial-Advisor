"""Regressions for defects found by the Codex review of Stage A (each failed before its fix)."""
import uuid
from decimal import Decimal

import pytest

import backend.services.chat_service as cs
from backend.models.models import Message, Thread
from backend.services.profile_service import ProfileService

PW = "Correct-Horse-9"
BASE = {"age": 30, "employment_type": "salaried", "monthly_income": 150000, "monthly_expenses": 40000,
        "existing_savings": 300000, "existing_investments": 0, "existing_debts": 0,
        "risk_tolerance": "moderate", "investment_horizon": "long"}


def user(client):
    b = client.post("/auth/signup", json={"email": f"r-{uuid.uuid4().hex[:8]}@example.com",
                                          "full_name": "Review User", "password": PW}).json()
    return {"Authorization": f"Bearer {b['access_token']}"}, b["user_id"]


def test_first_message_retry_without_thread_id_reuses_the_thread_and_does_not_call_model_twice(client, monkeypatch):
    calls = []
    monkeypatch.setattr(cs, "call_llm", lambda **kw: calls.append(1) or "ok")
    h, uid = user(client)
    client.post("/profile", json=BASE, headers=h)
    cid = uuid.uuid4().hex
    a = client.post("/chat", json={"message": "hello", "client_message_id": cid}, headers=h).json()
    b = client.post("/chat", json={"message": "hello", "client_message_id": cid}, headers=h).json()   # thread id never arrived
    assert a["thread_id"] == b["thread_id"] and b["replayed"] is True and len(calls) == 1
    db = client.session_factory()
    assert db.query(Thread).filter_by(user_id=uid).count() == 1
    assert db.query(Message).filter_by(role="user").count() == 1
    db.close()


def test_another_users_message_id_is_not_treated_as_a_retry(client, monkeypatch):
    monkeypatch.setattr(cs, "call_llm", lambda **kw: "ok")
    h1, _ = user(client)
    h2, _ = user(client)
    cid = uuid.uuid4().hex
    t1 = client.post("/chat", json={"message": "hi", "client_message_id": cid}, headers=h1).json()["thread_id"]
    t2 = client.post("/chat", json={"message": "hi", "client_message_id": cid}, headers=h2).json()
    assert t2["thread_id"] != t1 and t2["replayed"] is False


def test_standalone_summary_keeps_computed_health_and_investment_figures(client):
    h, _ = user(client)
    client.post("/profile", json=BASE, headers=h)
    out = client.post("/analysis", json={"analysis_type": "summary"}, headers=h).json()
    s = out["results"]["summary"]
    assert s["health_score"] not in (None, 0) and s["grade"] != "N/A"
    assert s["key_numbers"]["recommended_sip"] > 0
    assert out["results"]["investment"]["total_monthly_investment"] == s["key_numbers"]["recommended_sip"]


def test_late_superseded_run_does_not_displace_current_revision_results(client, monkeypatch):
    h, uid = user(client)
    client.post("/profile", json=BASE, headers=h)
    from agents.graph_executor import GraphExecutor
    real = GraphExecutor.execute_single
    state = {"first": True}

    def racing(self, name, profile):
        out = real(self, name, profile)
        if state["first"]:                       # edit the profile while the first run is in flight
            state["first"] = False
            db = client.session_factory()
            try:
                d = {k: (Decimal(str(v)) if isinstance(v, (int, float)) and k != "age" else v) for k, v in BASE.items()}
                d.update(monthly_income=Decimal("160000"), monthly_credit_spend=Decimal("0"),
                         monthly_debt_payment=None, credit_score=None)
                ProfileService(db).save(uid, d)
            finally:
                db.close()
        return out

    monkeypatch.setattr(GraphExecutor, "execute_single", racing)
    late = client.post("/analysis", json={"analysis_type": "health"}, headers=h).json()
    assert late["status"] == "superseded"
    current = client.post("/analysis", json={"analysis_type": "health"}, headers=h).json()
    last = client.get("/analysis/last", headers=h).json()
    assert last["section_status"]["_meta"]["health"]["analysis_id"] == current["analysis_id"]
    assert last["stale"] is False


def test_streaming_failover_reaches_the_second_provider_family(monkeypatch):
    import utils.llm_brain as lb
    calls = []

    class BadGroq:
        def __init__(self, **kw): pass
        def stream(self, m):
            calls.append("groq")
            raise RuntimeError("down")
            yield

    class GoodGemini:
        def __init__(self, **kw): pass
        def stream(self, m):
            calls.append("gemini")
            class C: content = "from gemini"
            yield C()

    monkeypatch.setattr(lb, "ChatGroq", BadGroq)
    monkeypatch.setattr(lb, "ChatGoogleGenerativeAI", GoodGemini)
    monkeypatch.setattr(lb, "GROQ_KEYS", ["k1", "k2"])
    monkeypatch.setattr(lb, "GROQ_MODELS", ["m1", "m2"])
    monkeypatch.setattr(lb, "GOOGLE_KEYS", ["g1"])
    monkeypatch.setattr(lb, "DISABLED_GROQ_MODELS", set())
    out = "".join(lb.stream_llm(system_prompt="s", user_message="u", max_tokens=10, agent_name="t"))
    assert out == "from gemini" and calls.count("groq") == lb._cfg.LLM_MAX_ATTEMPTS and calls[-1] == "gemini"


# ── Codex review round 2 ──────────────────────────────────────────────────
def test_simulation_never_invests_more_than_the_canonical_contribution(client):
    h, _ = user(client)
    client.post("/profile", json={**BASE, "monthly_income": 100000, "monthly_expenses": 40000,
                                  "existing_debts": 300000, "monthly_debt_payment": 60000}, headers=h)
    out = client.post("/analysis", json={"analysis_type": "full"}, headers=h).json()
    assert out["snapshot"]["available_contribution_paise"] == 0
    sim = out["results"]["simulation"]
    assert sim["optimized_trajectory"]["monthly_investment"] == 0
    assert sim["current_trajectory"]["monthly_investment"] == 0


def test_unknown_migrated_debt_or_savings_blocks_affordability_instead_of_becoming_zero(client):
    from backend.models.models import FinancialProfile
    h, uid = user(client)
    client.post("/profile", json=BASE, headers=h)
    db = client.session_factory()
    row = db.query(FinancialProfile).filter_by(user_id=uid).one()
    row.existing_debts_paise = None
    db.commit()
    db.close()
    assert client.get("/profile", headers=h).json()["needs_reentry"] == ["existing_debts"]
    r = client.post("/analysis", json={"analysis_type": "investment"}, headers=h)
    assert r.status_code == 422 and "existing_debts" in r.json()["fields"] if "fields" in r.json() else r.status_code == 422
    ok = client.post("/analysis", json={"analysis_type": "investment", "scenario": {"existing_debts": 0}}, headers=h)
    assert ok.status_code == 200                    # a what-if can supply the missing value


def test_state_write_is_conditional_on_the_current_revision(client):
    from backend.models.models import FinancialState
    from backend.services.analysis_service import AnalysisService
    from engines.cashflow import build_snapshot
    h, uid = user(client)
    client.post("/profile", json=BASE, headers=h)
    client.post("/analysis", json={"analysis_type": "health"}, headers=h)
    client.post("/profile", json={**BASE, "monthly_income": 160000}, headers=h)      # now revision 2
    client.post("/analysis", json={"analysis_type": "health"}, headers=h)
    db = client.session_factory()
    svc = AnalysisService(db)
    snap = build_snapshot(dict(income_paise=1, expenses_paise=1), owner_id=uid, profile_revision=1)
    svc._update_state(uid, 11.0, snap, revision=1)            # a straggler from revision 1 arrives late
    st = db.query(FinancialState).filter_by(user_id=uid).one()
    assert st.health_score != 11.0 and st.health_score_revision == 2
    db.close()


def test_concurrent_first_message_creates_one_thread_and_one_turn(client, monkeypatch):
    """Simulates the lost race: two threads were created, the second insert hits the unique index."""
    from backend.models.models import Message, Thread
    from backend.services.chat_service import ChatService
    monkeypatch.setattr(cs, "call_llm", lambda **kw: "ok")
    h, uid = user(client)
    cid = uuid.uuid4().hex
    db = client.session_factory()
    svc = ChatService(db)
    t1 = svc.get_or_create_thread(uid, None, "hello", "U", "u@example.com")
    t2 = svc.get_or_create_thread(uid, None, "hello", "U", "u@example.com")          # both passed the lookup
    assert t1 != t2
    r1 = svc.chat(uid, "U", "hello", t1, cid)
    r2 = svc.chat(uid, "U", "hello", t2, cid)                                         # loses the race
    assert r2["thread_id"] == t1 and r2["replayed"] is True
    assert db.query(Message).filter_by(role="user").count() == 1
    assert db.query(Thread).filter_by(user_id=uid).count() == 1                       # stray thread removed
    db.close()


def test_malformed_model_json_is_reported_degraded_not_complete(client, monkeypatch):
    import agents.health_agent as ha
    monkeypatch.setattr(ha, "call_llm", lambda **kw: "this is not json")
    h, _ = user(client)
    client.post("/profile", json=BASE, headers=h)
    out = client.post("/analysis", json={"analysis_type": "health"}, headers=h).json()
    assert out["section_status"]["health"]["status"] == "degraded"
    assert out["status"] == "degraded" and out["success"] is False


def test_explicit_unknown_credit_override_beats_the_saved_score(client):
    h, _ = user(client)
    client.post("/profile", json={**BASE, "credit_score": 780}, headers=h)
    known = client.post("/analysis", json={"analysis_type": "health"}, headers=h).json()
    assert known["results"]["health"]["components"]["credit_score"]["value"] == "780"
    unk = client.post("/analysis", json={"analysis_type": "health", "scenario": {"credit_score": None}},
                      headers=h).json()
    assert unk["is_scenario"] is True
    assert unk["results"]["health"]["components"]["credit_score"]["value"] == "unknown"
    assert client.get("/profile", headers=h).json()["credit_score"] == 780          # saved profile untouched


def test_duplicate_of_an_in_flight_turn_waits_for_the_reply_instead_of_calling_the_model(client, monkeypatch):
    import threading
    import time
    from backend.services.chat_service import ChatService
    calls = []
    monkeypatch.setattr(cs, "call_llm", lambda **kw: calls.append(1) or "ok")
    monkeypatch.setattr(cs, "IN_FLIGHT_SECONDS", 5.0)
    h, uid = user(client)
    cid = uuid.uuid4().hex
    db = client.session_factory()
    svc = ChatService(db)
    tid = svc.get_or_create_thread(uid, None, "hello", "U", "u@example.com")
    first = svc.begin_turn(uid, "U", tid, "hello", cid)            # original request: user row stored, reply pending
    assert first.replay is None

    def finish_later():
        time.sleep(0.6)
        s2 = client.session_factory()
        ChatService(s2).finish_turn(tid, "the answer", "ok", cid)
        s2.close()
    threading.Thread(target=finish_later).start()

    dup = ChatService(client.session_factory()).begin_turn(uid, "U", tid, "hello", cid)
    assert dup.replay == "the answer"                                # waited, replayed, no second model call
    assert calls == []
    db.close()
