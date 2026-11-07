"""T106 — chat idempotency, outage fallback, stream contract, contradiction guard (providers mocked)."""
import json
import uuid

import pytest

import backend.services.chat_service as cs
from backend.models.models import Message
from utils.llm_brain import ProviderUnavailable, StreamInterrupted

PW = "Correct-Horse-9"
DEFICIT = {"age": 30, "employment_type": "salaried", "monthly_income": 45000, "monthly_expenses": 55000,
           "risk_tolerance": "moderate", "investment_horizon": "long"}


@pytest.fixture
def me(client):
    body = client.post("/auth/signup", json={"email": f"c-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "Chat User", "password": PW}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.post("/profile", json=DEFICIT, headers=h).status_code == 200
    return h


def count(client, role=None):
    db = client.session_factory()
    try:
        q = db.query(Message)
        return (q.filter_by(role=role) if role else q).count()
    finally:
        db.close()


def sse(resp):
    return [json.loads(l[6:]) for l in resp.text.splitlines() if l.startswith("data: ")]


def test_retry_with_same_client_message_id_is_idempotent(client, me, monkeypatch):
    calls = []
    monkeypatch.setattr(cs, "call_llm", lambda **kw: calls.append(1) or "Your expenses exceed income; trim spending first.")
    cid = uuid.uuid4().hex
    first = client.post("/chat", json={"message": "How am I doing?", "client_message_id": cid}, headers=me).json()
    again = client.post("/chat", json={"message": "How am I doing?", "thread_id": first["thread_id"],
                                       "client_message_id": cid}, headers=me).json()
    assert first["replayed"] is False and again["replayed"] is True and again["reply"] == first["reply"]
    assert len(calls) == 1                                   # the model is not called twice
    assert count(client, "user") == 1 and count(client, "assistant") == 1


def test_same_id_with_different_text_is_a_conflict(client, me, monkeypatch):
    monkeypatch.setattr(cs, "call_llm", lambda **kw: "ok")
    cid = uuid.uuid4().hex
    t = client.post("/chat", json={"message": "first", "client_message_id": cid}, headers=me).json()["thread_id"]
    r = client.post("/chat", json={"message": "different", "thread_id": t, "client_message_id": cid}, headers=me)
    assert r.status_code == 409 and r.json()["code"] == "idempotency_conflict"
    assert count(client, "user") == 1


def test_outage_returns_deterministic_reply_from_verified_numbers_and_is_flagged(client, me, monkeypatch):
    def boom(**kw):
        raise ProviderUnavailable("down")
    monkeypatch.setattr(cs, "call_llm", boom)
    out = client.post("/chat", json={"message": "Can I start a SIP?", "client_message_id": uuid.uuid4().hex},
                      headers=me).json()
    assert out["status"] == "degraded"
    text = out["reply"]
    assert "Rs 10,000" in text and "exceed your income" in text and "nothing to invest" in text
    assert "27,500" not in text


def test_reply_claiming_surplus_during_deficit_is_replaced(client, me, monkeypatch):
    monkeypatch.setattr(cs, "call_llm", lambda **kw: "You have a monthly surplus of Rs 10,000, start a SIP now!")
    out = client.post("/chat", json={"message": "invest?", "client_message_id": uuid.uuid4().hex}, headers=me).json()
    assert out["status"] == "degraded" and "monthly surplus" not in out["reply"].lower()


def test_stream_contract_and_idempotent_replay(client, me, monkeypatch):
    monkeypatch.setattr(cs, "stream_llm", lambda **kw: iter(["Spend ", "less ", "first."]))
    cid = uuid.uuid4().hex
    r = client.post("/chat/stream", json={"message": "help", "client_message_id": cid}, headers=me)
    ev = sse(r)
    assert [e["chunk"] for e in ev if "chunk" in e] == ["Spend ", "less ", "first."]
    done = ev[-1]
    assert done["done"] is True and done["full_reply"] == "Spend less first." and done["replayed"] is False
    again = sse(client.post("/chat/stream", json={"message": "help", "thread_id": done["thread_id"],
                                                  "client_message_id": cid}, headers=me))
    assert again[-1]["replayed"] is True and again[-1]["full_reply"] == "Spend less first."
    assert count(client, "assistant") == 1


def test_stream_outage_gives_degraded_fallback(client, me, monkeypatch):
    def dead(**kw):
        raise ProviderUnavailable("down")
        yield  # pragma: no cover
    monkeypatch.setattr(cs, "stream_llm", dead)
    ev = sse(client.post("/chat/stream", json={"message": "help", "client_message_id": uuid.uuid4().hex}, headers=me))
    assert ev[-1]["done"] and ev[-1]["status"] == "degraded" and "10,000" in ev[-1]["full_reply"]


def test_interrupted_stream_stores_no_assistant_message_and_retry_completes(client, me, monkeypatch):
    def broken(**kw):
        yield "partial "
        raise StreamInterrupted("cut")
    monkeypatch.setattr(cs, "stream_llm", broken)
    cid = uuid.uuid4().hex
    ev = sse(client.post("/chat/stream", json={"message": "help", "client_message_id": cid}, headers=me))
    assert ev[-1]["retryable"] is True and "error" in ev[-1]
    assert count(client, "assistant") == 0 and count(client, "user") == 1
    thread = ev[-1]["thread_id"]
    monkeypatch.setattr(cs, "stream_llm", lambda **kw: iter(["Complete answer."]))
    ev2 = sse(client.post("/chat/stream", json={"message": "help", "thread_id": thread, "client_message_id": cid},
                          headers=me))
    assert ev2[-1]["done"] and ev2[-1]["full_reply"] == "Complete answer."
    assert count(client, "user") == 1 and count(client, "assistant") == 1


def test_chat_without_profile_asks_for_one_instead_of_inventing_numbers(client, monkeypatch):
    body = client.post("/auth/signup", json={"email": f"n-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "No Profile", "password": PW}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    seen = {}
    monkeypatch.setattr(cs, "call_llm", lambda **kw: seen.update(kw) or "Please complete your profile.")
    out = client.post("/chat", json={"message": "hi", "client_message_id": uuid.uuid4().hex}, headers=h)
    assert out.status_code == 200 and "missing or incomplete" in seen["system_prompt"]
