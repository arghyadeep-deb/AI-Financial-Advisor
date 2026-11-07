from uuid import uuid4

import pytest

from backend.services import chat_service
from backend.services.output_guard import named_products_enabled
from tests.api.test_chat import sse
from tests.api.test_tenancy import PROFILE, signup


@pytest.mark.parametrize('with_profile', [False, True])
def test_environment_cannot_enable_named_advice_with_or_without_profile(client, monkeypatch, with_profile):
    owner = signup(client)
    if with_profile:
        assert client.post('/profile', headers=owner, json=PROFILE).status_code == 200
    monkeypatch.setenv('NAMED_PRODUCT_RECOMMENDATIONS', 'true')
    monkeypatch.setenv('ALLOCATION_SANDBOX_ENABLED', 'true')
    assert not named_products_enabled()
    monkeypatch.setattr(chat_service, 'call_llm', lambda **kw: 'Buy HDFC fund now.')
    response = client.post('/chat', headers=owner, json={'message': 'Name a fund', 'client_message_id': uuid4().hex})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'degraded'
    assert 'HDFC' not in response.json()['reply']
    monkeypatch.setattr(chat_service, 'stream_llm', lambda **kw: iter(['Buy HD', 'FC fund now.']))
    events = sse(client.post('/chat/stream', headers=owner,
        json={'message': 'Name a fund', 'client_message_id': uuid4().hex}))
    assert events[-1]['status'] == 'degraded' and events[-1]['replace']
    assert 'HDFC' not in events[-1]['full_reply']
    assert client.post('/allocation-proposals', headers=owner).json()['status'] == 'gated'
