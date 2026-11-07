"""Reviewed synthetic application artifact. No customer data or network ingestion.

These examples are not attributed to a bank, regulator or licensed publisher.
The fixed expiry deliberately fails closed rather than extending on each boot.
"""
import json
from pathlib import Path

from backend.core.config import config
from backend.knowledge.registry import Registry, SourceVersion


def sample_registry() -> Registry:
    if config.is_production_like:
        return Registry((), frozenset())
    path = Path(__file__).resolve().parents[2] / 'knowledge_base/education/sample-v1.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, list):
            return Registry((), frozenset())
        versions = tuple(SourceVersion.model_validate(v) for v in data)
        if any(v.owner_id is not None for v in versions):
            return Registry((), frozenset())
        return Registry(versions, frozenset({'example.test'}))
    except (OSError, ValueError):
        # Never serve a partially loaded catalog or fall back to a private/legacy
        # index. No exception text is logged: it may contain document contents.
        return Registry((), frozenset())
