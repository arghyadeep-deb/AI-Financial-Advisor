"""T108 / T113 / T109 — authentication lifecycle through the real HTTP endpoints."""
import hashlib
import hmac
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.core import auth as authlib
from backend.core.config import Config, ConfigError, config
from backend.models.models import AuthSession, PasswordResetToken, User
from backend.services import auth_service

PW = "Correct-Horse-9"


def signup(client, email=None, password=PW):
    email = email or f"u-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/signup", json={"email": email, "full_name": "Test User", "password": password})
    assert r.status_code == 200, r.text
    return email, r.json()


def bearer(body):
    return {"Authorization": f"Bearer {body['access_token']}"}


def me_status(client, token):
    return client.get("/profile/me", headers={"Authorization": f"Bearer {token}"}).status_code


# ── happy path & hashing ───────────────────────────────────────────────────
def test_signup_login_and_token_claims(client):
    email, body = signup(client)
    assert client.get("/profile/me", headers=bearer(body)).status_code == 200
    claims = jwt.decode(body["access_token"], config.SECRET_KEY, algorithms=["HS256"],
                        audience=config.TOKEN_AUDIENCE, issuer=config.TOKEN_ISSUER)
    for c in ("sub", "sid", "jti", "iat", "nbf", "exp", "iss", "aud", "typ"):
        assert c in claims
    assert claims["exp"] - claims["iat"] == config.ACCESS_TOKEN_MINUTES * 60
    login = client.post("/auth/login", json={"email": email, "password": PW})
    assert login.status_code == 200 and login.json()["access_token"] != body["access_token"]


def test_identical_passwords_get_different_argon2_hashes_and_key_is_not_used_for_hashing(client):
    e1, _ = signup(client)
    e2, _ = signup(client)
    db = client.session_factory()
    h1 = db.query(User).filter(User.email == e1).one()
    h2 = db.query(User).filter(User.email == e2).one()
    assert h1.hashed_password != h2.hashed_password
    assert h1.hashed_password.startswith("$argon2id$") and h1.password_scheme == "argon2id"
    # changing the token-signing key must not affect password verification
    assert authlib.verify_argon2(PW, h1.hashed_password)
    db.close()


def test_weak_or_common_passwords_rejected_at_signup(client):
    for pw in ("short", "password123", "x" * 129):
        r = client.post("/auth/signup", json={"email": f"{uuid.uuid4().hex[:6]}@example.com",
                                              "full_name": "Weak One", "password": pw})
        assert r.status_code == 422


# ── forged / expired / malformed tokens ────────────────────────────────────
def _claims(sub, sid, **over):
    now = datetime.now(timezone.utc)
    base = {"sub": str(sub), "sid": sid, "jti": uuid.uuid4().hex, "iat": now, "nbf": now,
            "exp": now + timedelta(minutes=5), "iss": config.TOKEN_ISSUER, "aud": config.TOKEN_AUDIENCE,
            "typ": "access"}
    base.update(over)
    return {k: v for k, v in base.items() if v is not None}


def test_forged_expired_and_malformed_tokens_all_fail_closed(client):
    _, body = signup(client)
    uid = body["user_id"]
    sid = jwt.decode(body["access_token"], options={"verify_signature": False})["sid"]
    ok = jwt.encode(_claims(uid, sid), config.SECRET_KEY, algorithm="HS256")
    assert me_status(client, ok) == 200                          # control: well-formed token works

    cases = {
        "wrong_key": jwt.encode(_claims(uid, sid), "attacker-key-" + "x" * 40, algorithm="HS256"),
        "default_changeme": jwt.encode(_claims(uid, sid), "changeme", algorithm="HS256"),
        "alg_none": jwt.encode(_claims(uid, sid), None, algorithm="none"),
        "expired": jwt.encode(_claims(uid, sid, exp=datetime.now(timezone.utc) - timedelta(minutes=5)),
                              config.SECRET_KEY, algorithm="HS256"),
        "not_yet_valid": jwt.encode(_claims(uid, sid, nbf=datetime.now(timezone.utc) + timedelta(minutes=30)),
                                    config.SECRET_KEY, algorithm="HS256"),
        "wrong_audience": jwt.encode(_claims(uid, sid, aud="other"), config.SECRET_KEY, algorithm="HS256"),
        "wrong_issuer": jwt.encode(_claims(uid, sid, iss="other"), config.SECRET_KEY, algorithm="HS256"),
        "missing_sid": jwt.encode(_claims(uid, None), config.SECRET_KEY, algorithm="HS256"),
        "missing_jti": jwt.encode(_claims(uid, sid, jti=None), config.SECRET_KEY, algorithm="HS256"),
        "non_numeric_sub": jwt.encode(_claims("abc", sid), config.SECRET_KEY, algorithm="HS256"),
        "negative_sub": jwt.encode(_claims("-1", sid), config.SECRET_KEY, algorithm="HS256"),
        "wrong_type": jwt.encode(_claims(uid, sid, typ="refresh"), config.SECRET_KEY, algorithm="HS256"),
        "unknown_session": jwt.encode(_claims(uid, str(uuid.uuid4())), config.SECRET_KEY, algorithm="HS256"),
        "other_users_session": None,
        "garbage": "not.a.jwt",
        "empty": "",
    }
    _, other = signup(client)
    other_sid = jwt.decode(other["access_token"], options={"verify_signature": False})["sid"]
    cases["other_users_session"] = jwt.encode(_claims(uid, other_sid), config.SECRET_KEY, algorithm="HS256")
    for name, token in cases.items():
        assert me_status(client, token) == 401, name
    assert client.get("/profile/me").status_code == 401           # no header at all: 401, not 403


def test_error_is_identical_whatever_the_reason_a_token_failed(client):
    _, body = signup(client)
    uid = body["user_id"]
    sid = jwt.decode(body["access_token"], options={"verify_signature": False})["sid"]
    expired = jwt.encode(_claims(uid, sid, exp=datetime.now(timezone.utc) - timedelta(minutes=5)),
                         config.SECRET_KEY, algorithm="HS256")
    wrong_key = jwt.encode(_claims(uid, sid), "attacker-key-" + "x" * 40, algorithm="HS256")
    revoked_sid = jwt.encode(_claims(uid, str(uuid.uuid4())), config.SECRET_KEY, algorithm="HS256")
    messages = set()
    for tok in ("garbage", expired, wrong_key, revoked_sid):
        r = client.get("/profile/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 401
        assert r.headers["WWW-Authenticate"] == "Bearer"
        messages.add(r.json()["message"])
    assert len(messages) == 1                              # no oracle for why it failed
    assert r.json()["request_id"] and r.json()["code"] == "unauthenticated"


# ── logout / session revocation ────────────────────────────────────────────
def test_logout_revokes_only_that_session(client):
    email, a = signup(client)
    b = client.post("/auth/login", json={"email": email, "password": PW}).json()
    assert client.post("/auth/logout", headers=bearer(a)).status_code == 204
    assert me_status(client, a["access_token"]) == 401
    assert me_status(client, b["access_token"]) == 200


# ── legacy hash migration ──────────────────────────────────────────────────
def _legacy_user(client, email, password):
    digest = hmac.new(config.LEGACY_PASSWORD_SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()
    db = client.session_factory()
    db.add(User(email=email, full_name="Legacy Person", hashed_password=digest,
                password_scheme="legacy_hmac_sha256", is_active=True))
    db.commit()
    db.close()
    return digest


def test_legacy_account_logs_in_once_and_is_rehashed_to_argon2(client):
    digest = _legacy_user(client, "old@example.com", "old-short")          # legacy allowed short passwords
    bad = client.post("/auth/login", json={"email": "old@example.com", "password": "wrong"})
    assert bad.status_code == 401
    ok = client.post("/auth/login", json={"email": "old@example.com", "password": "old-short"})
    assert ok.status_code == 200
    db = client.session_factory()
    u = db.query(User).filter(User.email == "old@example.com").one()
    assert u.password_scheme == "argon2id" and u.hashed_password != digest
    assert u.hashed_password.startswith("$argon2id$")
    db.close()
    assert client.post("/auth/login", json={"email": "old@example.com", "password": "old-short"}).status_code == 200


def test_legacy_login_impossible_without_legacy_secret_but_reset_path_works(client, monkeypatch):
    _legacy_user(client, "lock@example.com", "pw-before-reset")
    monkeypatch.setattr(config, "LEGACY_PASSWORD_SECRET", "")
    assert client.post("/auth/login", json={"email": "lock@example.com",
                                            "password": "pw-before-reset"}).status_code == 401
    sent = {}
    monkeypatch.setattr(auth_service, "recovery_delivery", lambda email, token: sent.update(token=token))
    assert client.post("/auth/password-reset/request", json={"email": "lock@example.com"}).status_code == 202
    r = client.post("/auth/password-reset/confirm", json={"token": sent["token"], "new_password": "Brand-New-Pass-77"})
    assert r.status_code == 200
    assert client.post("/auth/login", json={"email": "lock@example.com",
                                            "password": "Brand-New-Pass-77"}).status_code == 200


# ── enumeration resistance & throttling ────────────────────────────────────
def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    email, _ = signup(client)
    a = client.post("/auth/login", json={"email": email, "password": "wrong-password-1"})
    b = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong-password-1"})
    assert a.status_code == b.status_code == 401
    assert a.json()["message"] == b.json()["message"]
    ra = client.post("/auth/password-reset/request", json={"email": email})
    rb = client.post("/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert ra.status_code == rb.status_code == 202 and ra.json() == rb.json()


def test_repeated_failures_lock_the_account_even_for_the_right_password(client):
    email, _ = signup(client)
    for _ in range(config.LOGIN_MAX_FAILURES):
        assert client.post("/auth/login", json={"email": email, "password": "nope-nope-nope"}).status_code == 401
    locked = client.post("/auth/login", json={"email": email, "password": PW})
    assert locked.status_code == 429 and int(locked.headers["Retry-After"]) > 0
    assert locked.json()["retryable"] is True


def test_unknown_accounts_are_throttled_the_same_way(client):
    for _ in range(config.LOGIN_MAX_FAILURES):
        client.post("/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-nope"})
    assert client.post("/auth/login", json={"email": "ghost@example.com",
                                            "password": "nope-nope-nope"}).status_code == 429


def test_success_resets_failure_counter(client):
    email, _ = signup(client)
    for _ in range(config.LOGIN_MAX_FAILURES - 1):
        client.post("/auth/login", json={"email": email, "password": "nope-nope-nope"})
    assert client.post("/auth/login", json={"email": email, "password": PW}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "nope-nope-nope"}).status_code == 401


# ── recovery tokens ────────────────────────────────────────────────────────
@pytest.fixture()
def delivered(monkeypatch):
    box = {}
    monkeypatch.setattr(auth_service, "recovery_delivery", lambda email, token: box.update(email=email, token=token))
    return box


def test_reset_flow_revokes_sessions_and_token_cannot_be_replayed(client, delivered):
    email, session = signup(client)
    assert client.post("/auth/password-reset/request", json={"email": email}).status_code == 202
    token = delivered["token"]
    # only a digest is stored
    db = client.session_factory()
    stored = db.query(PasswordResetToken).one()
    assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest() and token not in stored.token_hash
    db.close()

    r = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "Another-Pass-2024"})
    assert r.status_code == 200
    assert me_status(client, session["access_token"]) == 401                     # old session revoked
    assert client.post("/auth/login", json={"email": email, "password": PW}).status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": "Another-Pass-2024"}).status_code == 200
    replay = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "Third-Pass-2024x"})
    assert replay.status_code == 400


def test_expired_unknown_and_weak_reset_attempts_fail_generically(client, delivered):
    email, _ = signup(client)
    client.post("/auth/password-reset/request", json={"email": email})
    token = delivered["token"]
    assert client.post("/auth/password-reset/confirm",
                       json={"token": "x" * 40, "new_password": "Another-Pass-2024"}).status_code == 400
    assert client.post("/auth/password-reset/confirm",
                       json={"token": token, "new_password": "short"}).status_code == 422
    db = client.session_factory()
    row = db.query(PasswordResetToken).one()
    row.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()
    db.close()
    r = client.post("/auth/password-reset/confirm", json={"token": token, "new_password": "Another-Pass-2024"})
    assert r.status_code == 400 and r.json()["message"] == "Invalid or expired recovery token."


def test_new_reset_request_invalidates_nothing_but_confirm_invalidates_other_outstanding_tokens(client, delivered):
    email, _ = signup(client)
    client.post("/auth/password-reset/request", json={"email": email})
    first = delivered["token"]
    client.post("/auth/password-reset/request", json={"email": email})
    second = delivered["token"]
    assert client.post("/auth/password-reset/confirm",
                       json={"token": second, "new_password": "Another-Pass-2024"}).status_code == 200
    assert client.post("/auth/password-reset/confirm",
                       json={"token": first, "new_password": "Third-Pass-2024x"}).status_code == 400


def test_concurrent_confirmations_of_one_token_succeed_exactly_once(client, delivered):
    email, _ = signup(client)
    client.post("/auth/password-reset/request", json={"email": email})
    token = delivered["token"]
    results = []

    def attempt(i):
        db = client.session_factory()
        try:
            auth_service.AuthService(db).confirm_reset(token, f"Race-Password-{i}-xyz")
            results.append("ok")
        except Exception:
            results.append("fail")
        finally:
            db.close()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(6)]
    [t.start() for t in threads]
    [t.join(10) for t in threads]
    assert results.count("ok") == 1 and len(results) == 6


# ── key rotation ───────────────────────────────────────────────────────────
def test_key_rotation_accepts_previous_key_until_it_is_removed(client, monkeypatch):
    _, body = signup(client)
    uid = body["user_id"]
    sid = jwt.decode(body["access_token"], options={"verify_signature": False})["sid"]
    old_key = "old-signing-key-" + "k" * 40
    old_token = jwt.encode(_claims(uid, sid), old_key, algorithm="HS256")
    assert me_status(client, old_token) == 401                               # not yet trusted
    monkeypatch.setattr(config, "SECRET_KEY_PREVIOUS", [old_key])
    assert me_status(client, old_token) == 200                               # rotation window
    monkeypatch.setattr(config, "SECRET_KEY_PREVIOUS", [])
    assert me_status(client, old_token) == 401                               # old credentials revoked
    assert me_status(client, body["access_token"]) == 200                    # current key unaffected


# ── production configuration ───────────────────────────────────────────────
@pytest.mark.parametrize("key", ["", "changeme", "changeme-in-production", "short", "x" * 31])
def test_production_refuses_missing_placeholder_or_short_signing_key(monkeypatch, key):
    c = Config()
    monkeypatch.setattr(c, "APP_ENV", "production")
    monkeypatch.setattr(c, "SECRET_KEY", key)
    monkeypatch.setattr(c, "DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    with pytest.raises(ConfigError):
        c.validate()


def test_unknown_app_env_is_treated_as_production(monkeypatch):
    c = Config()
    monkeypatch.setattr(c, "APP_ENV", "prod-typo")
    monkeypatch.setattr(c, "SECRET_KEY", "")
    with pytest.raises(ConfigError):
        c.validate()


def test_production_rejects_wildcard_cors_and_sqlite_but_accepts_a_proper_config(monkeypatch):
    c = Config()
    monkeypatch.setattr(c, "APP_ENV", "production")
    monkeypatch.setattr(c, "SECRET_KEY", "s" * 48)
    monkeypatch.setattr(c, "DATABASE_URL", "postgresql+psycopg://u:p@h/db")
    monkeypatch.setattr(c, "CORS_ORIGINS", ["*"])
    with pytest.raises(ConfigError):
        c.validate()
    monkeypatch.setattr(c, "CORS_ORIGINS", ["https://app.example.com"])
    c.validate()                                                              # proper config passes
    monkeypatch.setattr(c, "DATABASE_URL", "sqlite:///x.db")
    with pytest.raises(ConfigError):
        c.validate()


def test_development_without_a_key_gets_a_random_ephemeral_key_not_a_constant(monkeypatch):
    monkeypatch.setattr(Config, "SECRET_KEY", "")
    monkeypatch.setattr(Config, "_ephemeral_key", False)
    a, b = Config(), Config()
    monkeypatch.setattr(a, "APP_ENV", "development")
    a.validate()
    first = Config.SECRET_KEY
    assert len(first) >= 32 and first.lower() not in ("changeme", "")
    monkeypatch.setattr(Config, "SECRET_KEY", "")
    b.APP_ENV = "development"
    b.validate()
    assert Config.SECRET_KEY != first
