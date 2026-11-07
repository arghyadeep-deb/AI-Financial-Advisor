"""T1303 entitlements, T1304 support tools, T1305 privacy-safe analytics. All data fictional."""
import json
from datetime import timedelta
from pathlib import Path
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from backend.core.config import config
from backend.models.models import SupportAccessLog, SupportGrant, utcnow
from backend.observability import analytics
from backend.services import entitlements, support
from tests.test_stage_c_platform import auth

FIXTURE = Path(__file__).parent / 'fixtures' / 'statements' / 'supported.csv'


@pytest.fixture(autouse=True)
def synthetic_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'SYNTHETIC_STATEMENTS_ENABLED', True)
    monkeypatch.setattr(config, 'PRIVATE_STORAGE_ROOT', str(tmp_path / 'private'))
    monkeypatch.setattr(config, 'STORAGE_ACTIVE_KEY', 'v1')
    monkeypatch.setattr(config, 'STORAGE_KEYS_JSON', json.dumps({'v1': Fernet.generate_key().decode()}))


def uploaded(client, headers):
    acct = client.post('/statement-accounts', headers=headers, json={'label': 'A', 'token': 'SYNTH_A'}).json()
    r = client.post(f"/statement-accounts/{acct['id']}/uploads", headers={**headers, 'Content-Type': 'text/csv'},
                    content=FIXTURE.read_bytes())
    assert r.status_code == 202, r.text
    return r.json()['document_id']


# ---- entitlements -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize('plan', ['free_pilot', 'free', 'suspended', 'nonsense', '', None])
def test_every_plan_keeps_privacy_export_and_deletion(plan):
    caps = entitlements.capabilities(plan)
    assert entitlements.ALWAYS <= caps
    assert entitlements.entitled('privacy_export', plan) and entitlements.entitled('account_deletion', plan)


def test_downgrade_removes_paid_capability_but_never_privacy():
    assert entitlements.entitled('tax_sandbox', 'free_pilot') and not entitlements.entitled('tax_sandbox', 'free')
    assert not entitlements.entitled('statements', 'suspended') and entitlements.entitled('privacy_export', 'suspended')
    assert not entitlements.entitled('anything_unknown', 'free_pilot')


def test_client_cannot_unlock_by_flag_header_or_query(client):
    a = auth(client, 'ent@example.com')
    base = client.get('/billing/entitlement', headers=a).json()
    assert base['plan'] == 'free_pilot' and base['paid_billing'] == 'deferred' and 'privacy_export' in base['capabilities']
    for headers, params in (({'X-Plan': 'paid'}, {}), ({}, {'plan': 'paid'}), ({'X-Entitlements': 'all'}, {'entitled': 'true'})):
        assert client.get('/billing/entitlement', headers={**a, **headers}, params=params).json() == base


def test_unsupported_billing_mode_fails_closed(monkeypatch):
    monkeypatch.setattr(config, 'BILLING_MODE', 'something_else')
    assert entitlements.current_plan() == 'suspended'
    assert entitlements.entitled('privacy_export') and not entitlements.entitled('statements')


# ---- analytics ----------------------------------------------------------------------------------------------------
def test_analytics_accepts_only_allow_listed_events_and_properties():
    analytics.captured.clear()
    assert analytics.capture('statement_uploaded', {'surface': 'web', 'size_bucket': analytics.bucket(42)})
    assert analytics.captured[-1] == {'event': 'statement_uploaded', 'props': {'surface': 'web', 'size_bucket': '11-100'}}


@pytest.mark.parametrize('name,props', [
    ('statement_uploaded', {'amount_paise': 500000}), ('profile_saved', {'monthly_income': '90000'}),
    ('profile_saved', {'surface': 'web', 'email': 'a@example.com'}), ('profile_saved', {'outcome': 'ok; DROP'}),
    ('report_viewed', {'description': 'Salary from Fictional Ltd'}), ('document_text', {}), ('signup_completed', {'user_id': 7}),
    ('export_requested', {'step': 12345}), ('export_requested', {'size_bucket': 1234567}),
])
def test_analytics_drops_financial_or_identifying_payloads_whole(name, props):
    analytics.captured.clear()
    assert analytics.capture(name, props) is False and not analytics.captured


def test_captured_buffer_never_holds_money_or_identity_after_mixed_input():
    analytics.captured.clear()
    mixed = [('profile_saved', {'surface': 'web', 'outcome': 'ok'}), ('profile_saved', {'monthly_income': 1}),
             ('credit_entry_added', {'score': 750}), ('report_viewed', {'surface': 'web'})]
    kept = sum(analytics.capture(n, p) for n, p in mixed)
    assert kept == 2
    text = json.dumps(list(analytics.captured))
    for forbidden in ('income', 'score', 'paise', '750', 'email', 'user'):
        assert forbidden not in text


# ---- support: request lookup, grants, audit -----------------------------------------------------------------------
def test_request_lookup_returns_metadata_only_and_is_audited(client, db_engine):
    a = auth(client, 'sup1@example.com')
    r = client.get('/profile?secret=abc123', headers={**a, 'X-Request-ID': 'req-abc-001'})
    assert r.headers['X-Request-ID'] == 'req-abc-001'
    with Session(db_engine) as db:
        found = support.lookup_request(db, 'support-1', 'req-abc-001', 'user reported an error')
        assert found['method'] == 'GET' and found['route'] == '/profile' and found['status'] == r.status_code
        assert set(found) == {'request_id', 'method', 'route', 'status', 'duration_ms'}
        assert 'abc123' not in json.dumps(found)
        assert support.lookup_request(db, 'support-1', 'no-such-id', 'checking') is None
        outcomes = [(x.action, x.target, x.outcome) for x in db.query(SupportAccessLog).order_by(SupportAccessLog.created_at)]
        assert outcomes == [('request_lookup', 'req-abc-001', 'found'), ('request_lookup', 'no-such-id', 'not_found')]
        with pytest.raises(ValueError):                                      # no anonymous or reasonless access
            support.lookup_request(db, '', 'req-abc-001', 'x')
        with pytest.raises(ValueError):
            support.lookup_request(db, 'support-1', 'req-abc-001', '')


def test_raw_document_needs_owner_grant_and_every_attempt_is_visible_to_owner(client, db_engine):
    a, b = auth(client, 'own@example.com'), auth(client, 'other@example.com')
    doc = uploaded(client, a)
    assert client.post('/support/grants', headers=b, json={'document_id': doc, 'hours': 2}).status_code == 404
    assert client.post('/support/grants', headers=a, json={'document_id': doc, 'hours': 100}).status_code == 422
    grant = client.post('/support/grants', headers=a, json={'document_id': doc, 'hours': 2})
    assert grant.status_code == 201
    gid = grant.json()['id']
    with Session(db_engine) as db:
        with pytest.raises(PermissionError):
            support.read_document(db, 'support-1', 'unknown-grant', 'no grant')
        content = support.read_document(db, 'support-1', gid, 'ticket 123')
        assert content == FIXTURE.read_bytes()
    log = client.get('/support/access-log', headers=a).json()
    assert [(x['action'], x['outcome']) for x in log] == [('document_read', 'allowed')]
    assert client.get('/support/access-log', headers=b).json() == []        # another user sees nothing of this


def test_expired_and_revoked_grants_refuse_and_are_logged(client, db_engine):
    a = auth(client, 'exp@example.com')
    doc = uploaded(client, a)
    g1 = client.post('/support/grants', headers=a, json={'document_id': doc, 'hours': 1}).json()['id']
    g2 = client.post('/support/grants', headers=a, json={'document_id': doc, 'hours': 1}).json()['id']
    assert client.post(f'/support/grants/{g2}/revoke', headers=a).json()['revoked']
    with Session(db_engine) as db:
        db.get(SupportGrant, g1).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        for gid in (g1, g2):
            with pytest.raises(PermissionError):
                support.read_document(db, 'support-1', gid, 'late')
    log = client.get('/support/access-log', headers=a).json()
    assert {x['outcome'] for x in log} == {'refused_expired_or_revoked'} and len(log) == 2


def test_other_user_cannot_revoke_grant(client):
    a, b = auth(client, 'r1@example.com'), auth(client, 'r2@example.com')
    gid = client.post('/support/grants', headers=a, json={'document_id': uploaded(client, a), 'hours': 1}).json()['id']
    assert client.post(f'/support/grants/{gid}/revoke', headers=b).status_code == 404


def test_support_routes_require_authentication(client):
    assert client.get('/support/access-log').status_code == 401
    assert client.post('/support/grants', json={'document_id': 'x', 'hours': 1}).status_code == 401
