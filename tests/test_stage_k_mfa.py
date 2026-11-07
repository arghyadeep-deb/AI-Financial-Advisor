"""RFC vectors + synthetic HTTP lifecycle, replay, throttle and registry purge."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlparse, parse_qs
import pytest
from sqlalchemy.orm import Session, sessionmaker
from fastapi import HTTPException
from backend.core import auth
from backend.core.config import config
from backend.core.totp import totp, matching_step
from backend.models.models import MfaCredential, MfaChallenge, MfaRecoveryCode, AuthSession, User, utcnow
from backend.services import mfa_service as mfa
from tests.test_stage_k_mail import mail_config

PW = 'Fictional-pass-987'
NOW = 1800000000


@pytest.fixture(autouse=True)
def mfa_config(monkeypatch):
    monkeypatch.setattr(config, 'MFA_REQUIRED', False)
    monkeypatch.setattr(mfa.time, 'time', lambda: NOW)


def signup(client, email='mfa@example.com'):
    r = client.post('/auth/signup', json={'email': email, 'full_name': 'Fictional', 'password': PW})
    assert r.status_code == 200, r.text
    return r.json()


def headers(session):
    return {'Authorization': 'Bearer ' + session['access_token']}


def setup(client, session):
    r = client.post('/auth/mfa/enroll/start', headers=headers(session), json={'password': PW})
    assert r.status_code == 200, r.text
    assert r.headers['Cache-Control'] == 'no-store'
    assert set(r.json()) == {'otpauth_uri', 'expires_in'}
    secret = parse_qs(urlparse(r.json()['otpauth_uri']).query)['secret'][0]
    return secret


def enrolled(client, email='mfa@example.com'):
    session = signup(client, email)
    secret = setup(client, session)
    r = client.post('/auth/mfa/enroll/confirm', headers=headers(session), json={'code': totp(secret, NOW)})
    assert r.status_code == 200, r.text
    return session, secret, r.json()


def challenge(client, email='mfa@example.com'):
    r = client.post('/auth/login', json={'email': email, 'password': PW})
    assert r.status_code == 200, r.text
    assert set(r.json()) == {'mfa_required', 'challenge', 'expires_in'}
    return r.json()['challenge']


def verify(client, token, code):
    return client.post('/auth/mfa/verify', json={'challenge': token, 'code': code})


# Independent expected values: RFC 6238 Appendix B (all algorithms, all times).
@pytest.mark.parametrize('timestamp,expected', [
    (59, ('94287082', '46119246', '90693936')),
    (1111111109, ('07081804', '68084774', '25091201')),
    (1111111111, ('14050471', '67062674', '99943326')),
    (1234567890, ('89005924', '91819424', '93441116')),
    (2000000000, ('69279037', '90698825', '38618901')),
    (20000000000, ('65353130', '77737706', '47863826')),
])
def test_rfc6238_vectors(timestamp, expected):
    seeds = [b'12345678901234567890', b'12345678901234567890123456789012',
        b'1234567890123456789012345678901234567890123456789012345678901234']
    for index, algorithm in enumerate(('sha1', 'sha256', 'sha512')):
        secret = base64.b32encode(seeds[index]).decode().rstrip('=')
        assert totp(secret, timestamp, digits=8, algorithm=algorithm) == expected[index]


def test_step_window_and_constant_format():
    secret = base64.b32encode(b'12345678901234567890').decode()
    for delta in (-1, 0, 1):
        assert matching_step(secret, totp(secret, NOW + delta * 30), NOW) == NOW // 30 + delta
    for code in ('12345', '1234567', '１２３４５６', '', 'garbage'):
        assert matching_step(secret, code, NOW) is None
    assert matching_step(secret, totp(secret, NOW - 60), NOW) is None
    assert matching_step(secret, totp(secret, NOW), NOW, NOW // 30) is None


def test_enrollment_login_secret_replay_and_sessions(client):
    old, secret, completed = enrolled(client)
    assert len(set(completed['recovery_codes'])) == 10
    assert client.get('/profile/me', headers=headers(old)).status_code == 401
    assert client.get('/profile/me', headers=headers(completed['session'])).status_code == 200
    assert client.get('/auth/mfa/status', headers=headers(completed['session'])).json() == {'enrolled': True, 'required': False}
    assert client.post('/auth/mfa/enroll/start', headers=headers(completed['session']), json={'password': PW}).status_code == 409
    token = challenge(client)
    assert verify(client, token, totp(secret, NOW)).status_code == 401  # enrollment step already used
    result = verify(client, token, totp(secret, NOW + 30))
    assert result.status_code == 200 and result.headers['Cache-Control'] == 'no-store'
    assert verify(client, token, totp(secret, NOW + 30)).status_code == 401
    assert client.get('/profile/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    with client.session_factory() as db:
        stored = db.get(MfaCredential, old['user_id'])
        assert secret not in stored.encrypted_secret
        assert db.query(MfaChallenge).one().token_hash == auth.digest_token(token)
        assert {r.token_hash for r in db.query(MfaRecoveryCode)} == {auth.digest_token(c) for c in completed['recovery_codes']}


def test_recovery_code_single_use_and_revokes_other_sessions(client):
    _, _, completed = enrolled(client)
    code = completed['recovery_codes'][0]
    result = verify(client, challenge(client), code)
    assert result.status_code == 200
    assert client.get('/profile/me', headers=headers(completed['session'])).status_code == 401
    assert client.get('/profile/me', headers=headers(result.json())).status_code == 200
    assert verify(client, challenge(client), code).status_code == 401
    with client.session_factory() as db:
        assert db.query(MfaRecoveryCode).filter(MfaRecoveryCode.used_at.is_not(None)).count() == 1


def test_challenge_expired_unknown_and_throttled_generic(client):
    _, secret, _ = enrolled(client)
    token = challenge(client)
    with client.session_factory() as db:
        db.get(MfaChallenge, auth.digest_token(token)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    expired = verify(client, token, totp(secret, NOW + 30))
    unknown = verify(client, 'missing', 'wrong')
    assert expired.status_code == unknown.status_code == 401
    assert expired.json()['message'] == unknown.json()['message']
    token = challenge(client)
    for _ in range(config.LOGIN_MAX_FAILURES - 1):
        assert verify(client, token, 'wrong').status_code == 401
    blocked = verify(client, token, totp(secret, NOW + 30))
    assert blocked.status_code == 429 and int(blocked.headers['Retry-After']) > 0


def test_disable_and_regenerate_require_reauth_revoke_and_invalidate(client):
    _, secret, completed = enrolled(client)
    token = challenge(client)
    h = headers(completed['session'])
    for route in ('disable', 'recovery-codes/regenerate'):
        assert client.post('/auth/mfa/' + route, headers=h, json={'password': 'wrong'}).status_code == 401
    regenerated = client.post('/auth/mfa/recovery-codes/regenerate', headers=h, json={'password': PW})
    assert regenerated.status_code == 200
    body = regenerated.json()
    assert not set(body['recovery_codes']) & set(completed['recovery_codes'])
    assert verify(client, token, totp(secret, NOW + 30)).status_code == 401
    assert verify(client, challenge(client), completed['recovery_codes'][0]).status_code == 401
    assert client.get('/profile/me', headers=h).status_code == 401
    assert client.post('/auth/mfa/disable', headers=headers(body['session']), json={'password': PW}).status_code == 200
    assert client.get('/profile/me', headers=headers(body['session'])).status_code == 401
    login = client.post('/auth/login', json={'email': 'mfa@example.com', 'password': PW})
    assert login.status_code == 200 and 'access_token' in login.json()
    with client.session_factory() as db:
        assert db.query(MfaCredential).count() == db.query(MfaChallenge).count() == db.query(MfaRecoveryCode).count() == 0


def test_required_policy_restricts_signup_login_and_disable(client, monkeypatch):
    monkeypatch.setattr(config, 'MFA_REQUIRED', True)
    session, secret, completed = enrolled(client)
    assert session['mfa_enrollment_required']
    assert client.get('/profile/me', headers=headers(completed['session'])).status_code == 200
    assert client.post('/auth/mfa/disable', headers=headers(completed['session']), json={'password': PW}).status_code == 409
    other = signup(client, 'other@example.com')
    assert client.get('/profile/me', headers=headers(other)).status_code == 401
    assert client.get('/privacy/consents', headers=headers(other)).status_code == 401
    assert client.get('/auth/mfa/status', headers=headers(other)).status_code == 200


def test_export_omits_secrets_and_deletion_purges_mfa(client, tmp_path, monkeypatch):
    from backend.services.privacy.lifecycle import delete_owned, configured_journal, export_owned
    from backend.core.owned_stores import validate_coverage
    monkeypatch.setattr(config, 'SUPPRESSION_JOURNAL', str(tmp_path / 'journal.db'))
    old, secret, completed = enrolled(client)
    challenge(client)
    with client.session_factory() as db:
        user = db.get(User, old['user_id'])
        validate_coverage()
        exported = str(export_owned(db, user, PW)['stores']['mfa'])
        assert secret not in exported and not any(c in exported for c in completed['recovery_codes'])
        assert 'encrypted_secret' not in exported and 'token_hash' not in exported
        delete_owned(db, user, PW, configured_journal())
        assert db.query(MfaCredential).count() == db.query(MfaChallenge).count() == db.query(MfaRecoveryCode).count() == 0


def test_concurrent_totp_step_only_one_session(client):
    old, secret, completed = enrolled(client)
    tokens = [challenge(client), challenge(client)]
    def attempt(token):
        with client.session_factory() as db:
            try:
                return mfa.verify(db, token, totp(secret, NOW + 30))['user_id']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, tokens))
    assert sorted(results) == sorted([old['user_id'], 401])


def test_mfa_migration_schema_roundtrip(db_engine):
    from alembic import command
    from sqlalchemy import inspect
    from backend.core.migrations_runner import _alembic_cfg
    from backend.models.models import Base
    for name in ('mfa_credentials', 'mfa_challenges', 'mfa_recovery_codes'):
        assert set(Base.metadata.tables[name].columns.keys()) == {c['name'] for c in inspect(db_engine).get_columns(name)}
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0180')
    assert 'mfa_credentials' not in inspect(db_engine).get_table_names()
    command.upgrade(cfg, 'head')
    assert 'mfa_credentials' in inspect(db_engine).get_table_names()


def test_pending_expiry_wrong_owner_and_unknown_code(client):
    session = signup(client)
    secret = setup(client, session)
    other = signup(client, 'other@example.com')
    assert client.post('/auth/mfa/enroll/confirm', headers=headers(other), json={'code': totp(secret, NOW)}).status_code == 401
    with client.session_factory() as db:
        db.get(MfaCredential, session['user_id']).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post('/auth/mfa/enroll/confirm', headers=headers(session), json={'code': totp(secret, NOW)}).status_code == 401


def test_concurrent_recovery_only_one_session(client):
    old, _, completed = enrolled(client)
    tokens = [challenge(client), challenge(client)]
    def attempt(token):
        with client.session_factory() as db:
            try:
                return mfa.verify(db, token, completed['recovery_codes'][0])['user_id']
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, tokens))
    assert sorted(results) == sorted([old['user_id'], 401])


def test_password_reset_preserves_mfa_and_invalidates_challenge(client, monkeypatch):
    from backend.services import auth_service
    _, secret, completed = enrolled(client)
    token = challenge(client)
    sent = {}
    monkeypatch.setattr(auth_service, 'recovery_delivery', lambda email, code: sent.update(token=code))
    assert client.post('/auth/password-reset/request', json={'email': 'mfa@example.com'}).status_code == 202
    assert client.post('/auth/password-reset/confirm', json={'token': sent['token'], 'new_password': 'New-fictional-pass-999'}).status_code == 200
    assert verify(client, token, totp(secret, NOW + 30)).status_code == 401
    result = client.post('/auth/login', json={'email': 'mfa@example.com', 'password': 'New-fictional-pass-999'})
    assert result.status_code == 200 and result.json()['mfa_required']
