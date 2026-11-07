from datetime import date
import json

import pytest
from pydantic import ValidationError

from backend.finance.allocation_sources import synthetic_fixture, production_registry
from backend.knowledge.registry import Registry
from engines.allocation import evidence_current
from engines.allocation.contracts import AssumptionPack

DAY = date(2026, 11, 7)


def test_four_class_pack_has_dated_illustrative_metadata():
    pack, registry = synthetic_fixture('v2')
    assert {b.asset for b in pack.assets} == {'cash', 'debt', 'equity', 'gold'}
    assert pack.assumption_label == 'illustrative_not_a_forecast'
    assert pack.owner and pack.source_id and pack.source_version and pack.source_hash
    assert all(b.illustrative_return_bps is not None and b.illustrative_volatility_bps is not None for b in pack.assets)
    assert evidence_current(pack, registry, 1, DAY)
    for day in (date(2026, 11, 6), date(2027, 1, 1)):
        assert not evidence_current(pack, registry, 1, day)
    assert not evidence_current(pack, production_registry(), 1, DAY)


@pytest.mark.parametrize('change', ['tampered', 'unapproved', 'withdrawn', 'foreign', 'corrected'])
def test_source_revision_integrity_and_owner_fail_closed(change):
    pack, registry = synthetic_fixture('v2')
    source = registry.retrieve('allocation', owner_id=1, as_of=DAY)[0]
    updates = {'tampered': {'content_hash': '0'*64}, 'unapproved': {'approved': False},
               'withdrawn': {'version': 2, 'approved': False}, 'foreign': {'owner_id': 2},
               'corrected': {'version': 2, 'approved': False}}[change]
    changed = source.model_copy(update=updates)
    sources = (source, changed) if change in {'corrected', 'withdrawn'} else (changed,)
    assert not evidence_current(pack, Registry(sources, frozenset({'example.test'})), 1, DAY)


def test_v2_rejects_incomplete_or_named_universe():
    pack, _ = synthetic_fixture('v2')
    data = pack.model_dump(mode='json')
    data['assets'][0]['illustrative_volatility_bps'] = None
    with pytest.raises(ValidationError):
        AssumptionPack.model_validate_json(json.dumps(data))
    data = pack.model_dump(mode='json')
    data['assets'][-1]['asset'] = 'Named Gold Fund'
    with pytest.raises(ValidationError):
        AssumptionPack.model_validate_json(json.dumps(data))
    with pytest.raises(ValueError):
        synthetic_fixture('../untrusted')
