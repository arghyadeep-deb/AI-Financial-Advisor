"""T109 — tenant boundary across EVERY protected route, plus two-user object-level checks."""
import re
import uuid

import pytest

from backend.main import app

PUBLIC = {
    ("GET", "/"), ("GET", "/health"),
    ("POST", "/auth/signup"), ("POST", "/auth/login"),
    ("POST", "/auth/mfa/verify"),  # short-lived single-use challenge; DB throttle and MFA proof, tested in Lane K
    ("POST", "/auth/password-reset/request"), ("POST", "/auth/password-reset/confirm"),
    ("POST", "/privacy/deletion-receipt"),  # post-deletion bearer capability: indexed digest, constant-time compare,
    # per-source + global DB admission BEFORE lookup (Lane K concurrency/cap tests); no account/session access
}
DOC_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
PW = "Correct-Horse-9"
PROFILE = {"age": 30, "employment_type": "salaried", "monthly_income": 100000, "monthly_expenses": 40000,
           "risk_tolerance": "moderate", "investment_horizon": "long"}


def routes():
    out = []
    for r in app.routes:
        if not hasattr(r, "methods") or r.path in DOC_PATHS:
            continue
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            out.append((m, r.path))
    return out


def signup(client):
    email = f"t-{uuid.uuid4().hex[:8]}@example.com"
    body = client.post("/auth/signup", json={"email": email, "full_name": "Tenant T", "password": PW}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_route_inventory_is_not_empty():
    assert len(routes()) >= 15


@pytest.mark.parametrize("method,path", routes())
def test_every_non_public_route_requires_authentication(client, method, path):
    if (method, path) in PUBLIC:
        pytest.skip("explicitly public")
    concrete = re.sub(r"\{[^}]+\}", "1", path)
    resp = client.request(method, concrete, json={} if method in ("POST", "PUT", "PATCH") else None)
    assert resp.status_code == 401, f"{method} {path} returned {resp.status_code} without credentials"


def test_public_allowlist_is_exact():
    unprotected = {(m, p) for (m, p) in routes() if (m, p) in PUBLIC}
    assert unprotected == PUBLIC


def test_users_only_see_their_own_threads_history_and_analysis(client):
    a, b = signup(client), signup(client)
    assert client.post("/profile", json=PROFILE, headers=a).status_code == 200
    assert client.post("/profile", json=dict(PROFILE, monthly_income=250000), headers=b).status_code == 200
    thread = client.post("/threads", json={"title": "A private thread"}, headers=a).json()
    tid = thread["id"]

    # B cannot read, detail, delete or chat into A's thread; same answer as a thread that does not exist
    missing = client.get("/chat/history/999999", headers=b)
    for resp in (client.get(f"/chat/history/{tid}", headers=b),
                 client.get(f"/threads/{tid}", headers=b),
                 client.get(f"/threads/{tid}/history", headers=b),
                 client.delete(f"/threads/{tid}", headers=b)):
        assert resp.status_code == 404, resp.request.url
        assert resp.json()["message"] == missing.json()["message"]
    chat = client.post("/chat", json={"message": "hello there", "thread_id": tid,
                                      "client_message_id": uuid.uuid4().hex}, headers=b)
    assert chat.status_code == 404
    assert client.get(f"/threads/{tid}", headers=a).status_code == 200      # owner unaffected

    assert [t["id"] for t in client.get("/threads", headers=b).json()] == []

    # analysis / profile / state are per user
    client.post("/analysis", json={"analysis_type": "health"}, headers=a)
    assert client.get("/analysis/last", headers=b).json()["found"] is False
    assert client.get("/analysis/state", headers=b).json()["health_score"] is None
    assert client.get("/profile", headers=a).json()["monthly_income"] == 100000
    assert client.get("/profile", headers=b).json()["monthly_income"] == 250000


def test_user_id_in_request_bodies_cannot_redirect_writes(client):
    a, b = signup(client), signup(client)
    me_b = client.get("/profile/me", headers=b).json()
    resp = client.post("/profile", json=dict(PROFILE, user_id=me_b["id"], id=1), headers=a)
    assert resp.status_code == 200
    assert client.get("/profile", headers=b).status_code == 404             # B still has no profile
    assert client.get("/profile", headers=a).json()["user_id"] != me_b["id"]
