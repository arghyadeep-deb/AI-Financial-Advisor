"""Offline synthetic Stage H acceptance, no providers or real tax data."""
import pytest
import json
from pathlib import Path
from pydantic import ValidationError
from backend.schemas.tax import TaxInputs


def inputs(**changes):
    return {**dict(financial_year='2024-25', assessment_year='2025-26', individual=True,
        resident=True, employer_count=1, identity_ref='fictional-person', sources=[dict(
        source_id='salary-A', layout='synthetic-salary-v1', identity_ref='fictional-person',
        financial_year='2024-25', salary_paise=210000, withholding_paise=10000)]), **changes}


def test_contract_exact_money_and_closed_document_scope():
    assert TaxInputs.model_validate(inputs()).sources[0].salary_paise == 210000
    for amount in [True, -1, 1.5, float('nan'), 10**14]:
        data = inputs()
        data['sources'][0]['salary_paise'] = amount
        with pytest.raises(ValidationError):
            TaxInputs.model_validate(data)
    data = inputs()
    data['sources'][0]['layout'] = 'Form16'
    with pytest.raises(ValidationError):
        TaxInputs.model_validate(data)


def test_scope_has_two_dated_hashed_sample_packs():
    from engines.tax.comparison import packs
    pair = packs()
    assert set(pair) == {'old', 'new'}
    assert all(p.synthetic_only and not p.production_approved for p in pair.values())
    assert pair['old'].version != pair['new'].version


def test_migration_storage_immutable_privacy_and_recovery(db_engine):
    from alembic import command
    from sqlalchemy import inspect, text
    from sqlalchemy.orm import Session
    from backend.core.migrations_runner import _alembic_cfg
    from backend.core.owned_stores import validate_coverage, _registry
    from backend.models.models import TaxRevision
    from tests.allocation.test_allocation import seed
    validate_coverage()
    assert {c['name'] for c in inspect(db_engine).get_columns('tax_revisions')} == set(TaxRevision.__table__.columns.keys())
    cfg = _alembic_cfg(str(db_engine.url))
    command.downgrade(cfg, '0141')
    command.upgrade(cfg, '0150')

    with Session(db_engine) as db:
        seed(db)
        db.add(TaxRevision(id='one', user_id=1, case_id='case', kind='case', revision=1,
            operation_key='operation', request={}, data={}))
        db.commit()
        with pytest.raises(Exception, match='immutable tax revision'):
            db.execute(text("UPDATE tax_revisions SET revision=2"))
        db.rollback()
        assert len(_registry['tax'].export(db, 1)['tax_revisions']) == 1
        assert _registry['tax'].export(db, 2)['tax_revisions'] == []
        with pytest.raises(RuntimeError, match='evidence exists'):
            command.downgrade(cfg, '0141')
        _registry['tax'].purge(db, 2)
        assert db.query(TaxRevision).count() == 1
        _registry['tax'].purge(db, 1)
        _registry['tax'].purge(db, 1)
        db.commit()
    command.downgrade(cfg, '0141')
    command.upgrade(cfg, '0150')


def operation(revision=0, **changes):
    from uuid import uuid4
    return {**dict(expected_revision=revision, idempotency_key=uuid4().hex, reason='Synthetic owner review'), **changes}


def test_owned_review_replay_conflicts_and_originals(client, monkeypatch):
    from backend.core.config import config
    from tests.api.test_tenancy import signup
    a, b = signup(client), signup(client)
    request = operation(data=inputs())
    assert client.post('/tax/cases', headers=a, json=request).status_code == 404
    monkeypatch.setattr(config, 'TAX_SANDBOX_ENABLED', True)
    request['data']['sources'].append({**request['data']['sources'][0], 'source_id': 'salary-B', 'salary_paise': 310000})
    saved = client.post('/tax/cases', headers=a, json=request).json()
    cid = saved['case_id']
    assert saved['data']['preview']['conflicts'] == ['income']
    assert client.post('/tax/cases', headers=a, json=request).json() == saved
    for target in [cid, 'missing']:
        response = client.get(f'/tax/cases/{target}', headers=b)
        assert response.status_code == 404
        assert response.json()['message'] == 'Tax resource not found.'
    r = operation(1, confirmed=True, resolutions=[dict(field='income', source_id='salary-B', explanation='Corrected employer evidence')])
    reviewed = client.post(f'/tax/cases/{cid}/reviews', headers=a, json=r).json()
    assert reviewed['data']['status'] == 'reconciled'
    assert reviewed['data']['fields']['salary_paise'] == 310000
    assert client.post(f'/tax/cases/{cid}/reviews', headers=a, json=r).json() == reviewed
    assert client.get('/tax/reviews/' + reviewed['id'], headers=b).status_code == 404
    assert client.get(f'/tax/cases/{cid}', headers=a).json()['data']['inputs'] == request['data'] | {'other_income': [], 'deductions_claimed': False}
    request['reason'] = 'Different request'
    assert client.post('/tax/cases', headers=a, json=request).status_code == 409
    monkeypatch.setattr(config, 'APP_ENV', 'production')
    assert client.post('/tax/cases', headers=a, json=operation(data=inputs())).status_code == 404


def compared(data=None, **kwargs):
    from datetime import date
    from backend.finance.tax import reconcile
    from engines.tax.comparison import compare
    data = TaxInputs.model_validate(data or inputs())
    review = {**reconcile(data), 'case_revision': 1, 'confirmed': True}
    return compare(data, review, revision=1, as_of=kwargs.pop('as_of', date(2026, 11, 7)), **kwargs)


@pytest.mark.parametrize('salary,old,new', [
    (c['salary_paise'], c['old_tax_paise'], c['new_tax_paise']) for c in json.loads(
        (Path(__file__).parents[1] / 'fixtures/tax/stage-h-goldens.json').read_text())['cases']])
def test_independent_sample_regime_boundaries(salary, old, new):
    # Old: deduct 5000; next 100000 at 15%, remainder 20%; supplement 1%.
    # New: deduct 10000; next 100000 at 10%, remainder 20%; supplement 1%.
    data = inputs()
    data['sources'][0]['salary_paise'] = salary
    result = compared(data)
    assert result['status'] == 'sample_draft'
    assert result['regimes']['old']['tax_paise'] == old
    assert result['regimes']['new']['tax_paise'] == new
    assert result['difference_old_minus_new_paise'] == old - new
    assert not result['filing_enabled'] and not result['production_approved']


@pytest.mark.parametrize('change', [dict(financial_year='2025-26'), dict(assessment_year='2026-27'),
    dict(resident=False), dict(individual=False), dict(employer_count=2),
    dict(other_income=['business']), dict(other_income=['foreign']), dict(other_income=['capital_gains']),
    dict(deductions_claimed=True)])
def test_scope_stops_before_draft(change):
    result = compared(inputs(**change))
    assert result['status'] == 'unsupported' and result['regimes'] is None


def test_expiry_scope_and_incomplete_withholding():
    from datetime import date
    assert compared(as_of=date(2027, 1, 1))['status'] == 'needs_review'
    assert compared(as_of=date(2025, 12, 31))['status'] == 'needs_review'
    data = inputs()
    data['sources'][0]['salary_paise'] = 1010001
    assert compared(data)['status'] == 'unsupported'  # new taxable exceeds final bound
    data['sources'][0]['withholding_paise'] = None
    assert compared(data)['status'] == 'needs_review'


def ready(client, monkeypatch, data=None):
    from backend.core.config import config
    from backend.services import tax_service
    from tests.api.test_tenancy import signup
    from datetime import date
    monkeypatch.setattr(config, 'TAX_SANDBOX_ENABLED', True)
    monkeypatch.setattr(tax_service, 'today', lambda: date(2026, 11, 7))
    headers = signup(client)
    saved = client.post('/tax/cases', headers=headers, json=operation(data=data or inputs())).json()
    cid = saved['case_id']
    review = client.post(f'/tax/cases/{cid}/reviews', headers=headers,
        json=operation(1, confirmed=True)).json()
    return headers, cid, review


def test_draft_export_consistency_stale_and_private_evidence(client, monkeypatch):
    import json
    from hashlib import sha256
    from datetime import date
    from backend.services import tax_service
    from backend.core.config import config
    from tests.api.test_tenancy import signup
    a, cid, review = ready(client, monkeypatch)
    b = signup(client)
    req = operation(1)
    path = f'/tax/cases/{cid}/drafts'
    response = client.post(path, headers=a, json=req)
    assert response.status_code == 200, response.text
    draft = response.json()
    assert not draft['stale'] and draft['data']['status'] == 'sample_draft'
    assert client.post(path, headers=a, json=req).json() == draft
    did = draft['id']
    exported = client.get(f'/tax/drafts/{did}/export', headers=a)
    payload = exported.json()
    assert payload['data'] == draft['data']
    snapshot = json.dumps(payload['data'], sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    assert sha256(snapshot.encode()).hexdigest() == payload['snapshot_sha256']
    assert 'DRAFT' in payload['label'] and not payload['official_acknowledgment']
    assert exported.headers['cache-control'] == 'no-store'
    assert payload['data']['evidence']['income']['source_id'] == 'salary-A'
    assert payload['data']['regimes']['old']['balance_payable_paise'] == 6160
    assert payload['data']['regimes']['new']['balance_payable_paise'] == 100
    for target in [did, 'missing']:
        for suffix in ['', '/export']:
            r = client.get(f'/tax/drafts/{target}{suffix}', headers=b)
            assert r.status_code == 404 and r.json()['message'] == 'Tax resource not found.'
    # A corrected case is a new immutable revision, never a mutation of the draft.
    changed = inputs()
    changed['sources'][0]['salary_paise'] = 310000
    correction = client.post(f'/tax/cases/{cid}/revisions', headers=a, json=operation(1, data=changed))
    assert correction.status_code == 200
    stale = client.get(f'/tax/drafts/{did}', headers=a).json()
    assert stale['data'] == draft['data'] and stale['stale_reasons'] == ['case_revision_changed']
    assert client.post(path, headers=a, json=operation(2)).json()['status'] == 'needs_review'
    client.post(f'/tax/cases/{cid}/reviews', headers=a, json=operation(2, confirmed=True))
    assert 'review_revision_changed' in client.get(f'/tax/drafts/{did}', headers=a).json()['stale_reasons']
    second = client.post(path, headers=a, json=operation(2)).json()
    assert second['revision'] == 2 and not second['stale']
    # Previously exported evidence remains exact even after expiry/disablement.
    monkeypatch.setattr(tax_service, 'today', lambda: date(2027, 1, 1))
    monkeypatch.setattr(config, 'TAX_SANDBOX_ENABLED', False)
    expired = client.get(f'/tax/drafts/{did}/export', headers=a).json()
    assert expired['data'] == draft['data']
    assert expired['snapshot_sha256'] == payload['snapshot_sha256']
    assert 'rule_pack_not_current' in expired['stale_reasons']


@pytest.mark.parametrize('field,value,reason', [('identity_ref', 'fictional-other', 'identity'),
    ('financial_year', '2025-26', 'period'), ('salary_paise', 310000, 'income'),
    ('withholding_paise', 20000, 'withholding')])
def test_conflicts_pause_until_explicit_evidence_review(field, value, reason):
    from backend.finance.tax import reconcile
    from backend.schemas.tax import FieldResolution
    data = inputs()
    data['sources'].append({**data['sources'][0], 'source_id': 'salary-B', field: value})
    parsed = TaxInputs.model_validate(data)
    assert reason in reconcile(parsed)['conflicts']
    chosen = FieldResolution(field=reason, source_id='salary-A', explanation='Retain matching original field')
    assert reconcile(parsed, [chosen])['status'] == 'reconciled'
    # Original contradictory source remains available for review.
    assert parsed.sources[1].model_dump()[field] == value


def test_resolution_cannot_mix_other_person_or_period_income():
    from backend.finance.tax import reconcile
    from backend.schemas.tax import FieldResolution
    data = inputs()
    data['sources'].append({**data['sources'][0], 'source_id': 'salary-B',
        'identity_ref': 'fictional-other', 'salary_paise': 99999, 'financial_year': '2025-26'})
    parsed = TaxInputs.model_validate(data)
    rs = [FieldResolution(field=f, source_id='salary-A' if f != 'income' else 'salary-B',
                         explanation='Attempt field mix') for f in ['identity', 'period', 'income']]
    result = reconcile(parsed, rs)
    assert result['status'] == 'needs_review'
    assert {'identity', 'period'} <= set(result['conflicts'])


def test_pack_changes_unavailable_and_quota_refusals(client, monkeypatch):
    from backend.services import tax_service
    from backend.core.config import config
    from engines.tax import comparison
    a, cid, _ = ready(client, monkeypatch)
    path = f'/tax/cases/{cid}/drafts'
    draft = client.post(path, headers=a, json=operation(1)).json()
    original = comparison.packs
    with monkeypatch.context() as m:
        def corrected():
            return {k: p.model_copy(update={'version': p.version + '.correction'}) for k, p in original().items()}
        m.setattr(comparison, 'packs', corrected)
        assert client.get('/tax/drafts/' + draft['id'], headers=a).json()['stale_reasons'] == ['rule_pack_changed']
    with monkeypatch.context() as m:
        m.setattr(comparison, 'packs', lambda: (_ for _ in ()).throw(ValueError('private-error-sentinel')))
        assert client.get('/tax/drafts/' + draft['id'], headers=a).json()['stale_reasons'] == ['rule_pack_unavailable']
        blocked = client.post(path, headers=a, json=operation(1)).json()
        assert blocked == {'status': 'needs_review', 'reasons': ['sample_pack_unavailable'], 'persisted': False}
    monkeypatch.setattr(config, 'EXPORT_DAILY_LIMIT', 0)
    assert client.get('/tax/drafts/' + draft['id'] + '/export', headers=a).status_code == 429
    monkeypatch.setattr(config, 'ANALYSIS_DAILY_LIMIT', 0)
    assert client.post('/tax/cases', headers=a, json=operation(data=inputs())).status_code == 429
    # A quota refusal never prevents historical evidence reads.
    assert client.get('/tax/drafts/' + draft['id'], headers=a).status_code == 200


def test_real_two_session_cas_and_replay(db_engine, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.orm import Session
    from fastapi import HTTPException
    from tests.allocation.test_allocation import seed
    from backend.core.config import config
    from backend.schemas.tax import CaseWrite
    from backend.services import tax_service as tax
    monkeypatch.setattr(config, 'TAX_SANDBOX_ENABLED', True)
    with Session(db_engine) as db:
        seed(db)
        saved = tax.write_case(db, 1, CaseWrite(**operation(data=inputs())))
    cid = saved['case_id']
    requests = [CaseWrite(**operation(1, data=inputs())) for _ in range(2)]
    def run(req):
        with Session(db_engine) as db:
            try:
                return tax.write_case(db, 1, req, cid)
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, requests))
    assert sum(isinstance(r, dict) for r in results) == 1 and 409 in results
    replay = CaseWrite(**operation(2, data=inputs()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [replay, replay]))
    assert results[0]['id'] == results[1]['id']


def test_tax_privacy_delete_restore_and_metadata(db_engine, tmp_path, monkeypatch):
    import json
    from sqlalchemy.orm import Session
    from backend.services.auth_service import AuthService
    from backend.services.privacy.lifecycle import export_owned, delete_owned, SuppressionJournal
    from backend.core.telemetry import events, ALLOWED_META_KEYS
    from backend.core.config import config
    from backend.models.models import User, TaxRevision
    from backend.schemas.tax import CaseWrite, ReviewWrite, DraftWrite
    from backend.services import tax_service as tax
    from datetime import date
    monkeypatch.setattr(config, 'TAX_SANDBOX_ENABLED', True)
    monkeypatch.setattr(tax, 'today', lambda: date(2026, 11, 7))
    events.clear()
    password = 'Safe-fictional-pass-987'
    with Session(db_engine) as db:
        credentials = AuthService(db).signup('tax-h@synthetic.test', 'Fictional', password)
        owner = db.get(User, credentials['user_id'])
        saved = tax.write_case(db, owner.id, CaseWrite(**operation(data=inputs())))
        tax.review(db, owner.id, saved['case_id'], ReviewWrite(**operation(1, confirmed=True)))
        tax.draft(db, owner.id, saved['case_id'], DraftWrite(**operation(1)))
        exported = export_owned(db, owner, password)
        assert len(exported['stores']['tax']['tax_revisions']) == 3
        spans = [e for e in events if e['node'].startswith('tax_')]
        assert spans and all(set(e) <= set(ALLOWED_META_KEYS) for e in spans)
        assert 'fictional-person' not in json.dumps(spans)
        assert 'salary_paise' not in json.dumps(spans)
        journal = SuppressionJournal(tmp_path / 'tax-journal.db')
        assert delete_owned(db, owner, password, journal)['status'] == 'live_complete'
        assert db.query(TaxRevision).count() == 0
        db.add(TaxRevision(id='restored', user_id=owner.id, case_id='old', kind='case', revision=1,
            operation_key='restored-operation', request={}, data={}))
        owner.is_active = True
        db.commit()
        journal.replay(db)
        assert not db.get(User, owner.id).is_active
        with pytest.raises(Exception) as exc:
            tax.write_case(db, owner.id, CaseWrite(**operation(data=inputs())))
        assert exc.value.status_code == 409
