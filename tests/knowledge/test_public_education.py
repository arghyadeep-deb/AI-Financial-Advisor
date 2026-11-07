"""Synthetic public-only research acceptance; no licensed/live-data claims."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from backend.core.config import config
from backend.core.telemetry import events
from backend.knowledge.education import GLOSSARY
from backend.knowledge.registry import SourceVersion, Registry
from backend.knowledge.sample_catalog import sample_registry
from backend.models.models import Base
from backend.services.education_service import answer, resolve
from tests.knowledge.test_registry import source, registry, DAY
from tests.test_stage_c_platform import auth

CASES = json.loads((Path(__file__).resolve().parents[2] / 'evals/research/synthetic_cases.json').read_text())


def fixture(topic='emi', **changes):
    return source(topic=topic, text=GLOSSARY[topic], **changes)


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_research_synthetic_eval(case):
    values = dict(topic=case['topic'], text=GLOSSARY[case['topic']]) | case['change']
    result = answer(case['topic'], registry(source(**values)), as_of=DAY)
    assert (result.status, result.staleness) == (case['status'], case['staleness'])
    assert result.as_of == DAY and result.corpus == 'public_sample_only'
    if result.status == 'complete':
        assert result.text == GLOSSARY[case['topic']]
        assert result.sources and all(c.staleness == 'current' for c in result.sources)
    else:
        assert result.text == 'Current reviewed evidence is unavailable for this topic.'
    assert 'PAN-SYNTH-PRIVATE' not in result.text and '99999' not in result.text


def test_correction_withdrawal_and_expiry_revalidate_citation():
    old = fixture()
    assert answer('emi', registry(old), as_of=DAY).status == 'complete'
    corrected = fixture(version=2)
    r = registry(old, corrected)
    assert resolve(old.source_id, 1, r, as_of=DAY) is None
    result = answer('emi', r, as_of=DAY)
    assert result.sources[0].version == 2
    assert resolve(old.source_id, 2, r, as_of=DAY)['excerpt'] == GLOSSARY['emi']
    expired = answer('emi', r, as_of=date(2027, 1, 1))
    assert expired.status == 'unavailable' and expired.staleness == 'expired'
    assert resolve(old.source_id, 2, r, as_of=date(2027, 1, 1))['excerpt'] is None
    withdrawn = registry(old, fixture(version=2, approved=False))
    assert answer('emi', withdrawn, as_of=DAY).sources == []
    assert resolve(old.source_id, 1, withdrawn, as_of=DAY) is None


def test_conflict_irrelevant_citation_and_private_versions_fail_closed():
    r = registry(fixture(), source(source_id='other', text='Pay 12345 immediately'))
    assert answer('emi', r, as_of=DAY).staleness == 'conflicting'
    assert answer('budget', r, as_of=DAY).status == 'unavailable'
    private = registry(fixture(owner_id=1), fixture(source_id='foreign', owner_id=2))
    assert private.retrieve('emi', owner_id=1, as_of=DAY)  # Existing private boundary still works.
    result = answer('emi', private, as_of=DAY)
    assert not result.sources and result.status == 'unavailable'
    assert resolve('fixture', 1, private, as_of=DAY) is None
    assert resolve('foreign', 1, private, as_of=DAY) is None


@pytest.mark.parametrize('changes', [{'content_hash': '0' * 64}, {'licence': ' '}, {'reviewer': ' '},
    {'expires': '2026-01-01'}, {'effective': '2027-01-01'}, {'unexpected': 'field'}])
def test_ingestion_contract_invalid(changes):
    with pytest.raises(ValidationError):
        SourceVersion.model_validate(fixture().model_dump() | changes)


def test_sample_catalog_hashes_dates_and_production_empty(monkeypatch):
    r = sample_registry()
    for topic in GLOSSARY:
        result = answer(topic, r, as_of=DAY)
        assert result.status == 'complete'
        assert result.sources[0].content_hash == sha256(GLOSSARY[topic].encode()).hexdigest()
        assert result.sources[0].published == DAY
        assert answer(topic, r, as_of=date(2027, 1, 1)).staleness == 'expired'
    monkeypatch.setattr(config, 'APP_ENV', 'production')
    assert answer('emi', sample_registry(), as_of=DAY).status == 'unavailable'


def test_api_source_resolution_no_mutations_network_or_payload_telemetry(client, monkeypatch):
    from backend.controllers import education_controller as controller
    monkeypatch.setattr(controller, 'today', lambda: DAY)
    headers = auth(client)
    def forbidden(*args, **kwargs):
        pytest.fail('Research attempted a network call')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    def counts():
        with client.session_factory() as db:
            return {name: db.scalar(select(func.count()).select_from(table)) for name, table in Base.metadata.tables.items()}
    before = counts()
    topics = client.get('/education/topics', headers=headers)
    assert topics.status_code == 200 and len(topics.json()['topics']) == 4
    response = client.post('/education/answers', headers=headers, json={'topic': 'emi'})
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    result = response.json()
    assert result['as_of'] == '2026-11-07' and result['staleness'] == 'current'
    assert result['personalized_advice_enabled'] is False
    citation = result['sources'][0]
    resolved = client.get(citation['resolve_path'], headers=headers)
    assert resolved.status_code == 200 and resolved.json()['excerpt'] == result['text']
    assert resolved.json()['source'] == citation
    for extra in [{'owner_id': 2}, {'index': 'private'}, {'action': 'trade'}, {'question': 'my PAN-SYNTH-PRIVATE'}]:
        assert client.post('/education/answers', headers=headers, json={'topic': 'emi', **extra}).status_code == 422
    for topic in ['recommendation', 'trade', 'personalized']:
        unavailable = client.post('/education/answers', headers=headers, json={'topic': topic}).json()
        assert unavailable['status'] == 'unavailable' and unavailable['sources'] == []
    assert client.post('/education/answers', headers=headers, json={'topic': 'emi; trade()'}).status_code == 422
    assert counts() == before
    assert GLOSSARY['emi'] not in str(events) and 'PAN-SYNTH-PRIVATE' not in str(events)
    assert 'example.test' not in str(events)


def test_api_private_source_same_404_as_missing_even_for_owner(client, monkeypatch):
    from backend.controllers import education_controller as controller
    monkeypatch.setattr(controller, 'today', lambda: DAY)
    monkeypatch.setattr(controller, 'sample_registry', lambda: registry(fixture(owner_id=1)))
    a, b = auth(client), auth(client, 'public-foreign@example.com')
    for headers in (a, b):
        actual = client.get('/education/sources/fixture/versions/1', headers=headers)
        absent = client.get('/education/sources/missing/versions/1', headers=headers)
        assert actual.status_code == absent.status_code == 404
        assert actual.json()['message'] == absent.json()['message']
        result = client.post('/education/answers', headers=headers, json={'topic': 'emi'}).json()
        assert result['status'] == 'unavailable' and result['sources'] == []


@pytest.mark.parametrize('broken', ['missing', 'malformed', 'hash', 'private', 'object', 'duplicate'])
def test_catalog_failure_deterministic_unavailable(monkeypatch, broken):
    from backend.knowledge import sample_catalog
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path.name != 'sample-v1.json':
            return original(path, *args, **kwargs)
        if broken == 'missing':
            raise OSError('PAN-SYNTH-PRIVATE')
        if broken == 'malformed':
            return 'invalid json PAN-SYNTH-PRIVATE'
        if broken == 'object':
            return '{}'
        data = fixture().model_dump(mode='json')
        if broken == 'hash':
            data['content_hash'] = '0' * 64
        if broken == 'private':
            data['owner_id'] = 1
        return json.dumps([data, data] if broken == 'duplicate' else [data])
    monkeypatch.setattr(Path, 'read_text', read)
    result = answer('emi', sample_catalog.sample_registry(), as_of=DAY)
    assert result.status == 'unavailable' and result.sources == []
    assert 'PAN-SYNTH-PRIVATE' not in str(events)
