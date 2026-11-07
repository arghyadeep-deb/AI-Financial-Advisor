"""Offline fixture loader. Never supplies a production-approved registry."""
from datetime import date
import os
from hashlib import sha256
from pathlib import Path

from backend.knowledge.registry import Registry, SourceVersion
from engines.allocation.contracts import AssumptionPack


def synthetic_fixture(version: str = 'v1') -> tuple[AssumptionPack, Registry]:
    if os.getenv('APP_ENV') != 'test':
        raise ValueError('Synthetic assumptions are test fixtures only; assumptions not validated')
    if version not in {'v1', 'v2'}:
        raise ValueError('Unsupported illustrative pack version')
    text = (Path(__file__).resolve().parents[2] / f"tests/fixtures/allocation/synthetic-{version}.json").read_text(encoding="utf-8")
    digest = sha256(text.encode()).hexdigest()
    import json
    data = json.loads(text)
    data["source_hash"] = digest
    pack = AssumptionPack.model_validate_json(json.dumps(data))
    published = date(2026, 1, 1) if version == 'v1' else pack.effective
    source = SourceVersion(source_id=pack.source_id, version=pack.source_version, title="Synthetic allocation fixture ONLY",
                           url="https://example.test/allocation", jurisdiction="IN", licence="synthetic test fixture",
                           reviewer=pack.owner, approved=True, published=published, fetched=published,
                           effective=pack.effective, expires=pack.expires, topic="allocation", text=text,
                           content_hash=digest)
    return pack, Registry((source,), frozenset({"example.test"}))


def production_registry() -> Registry:
    return Registry((), frozenset())
