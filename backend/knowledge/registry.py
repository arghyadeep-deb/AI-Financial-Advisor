"""Reviewed, immutable evidence catalog. No network or model execution.

Registry construction is a trusted application boundary, never a user endpoint.
Corrections append versions; retrieval only exposes the latest approved version.
"""
from datetime import date
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from backend.core.telemetry import traceable


class SourceVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_id: str = Field(min_length=1)
    version: int = Field(gt=0)
    title: str = Field(min_length=1)
    url: HttpUrl
    jurisdiction: Literal["IN"]
    licence: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    approved: bool = False
    published: date
    fetched: date
    effective: date
    expires: date
    owner_id: int | None = Field(default=None, gt=0)
    topic: str = Field(min_length=1)
    text: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_evidence(self):
        if self.expires <= self.effective or self.fetched < self.published:
            raise ValueError("invalid evidence dates")
        if sha256(self.text.encode()).hexdigest() != self.content_hash:
            raise ValueError("evidence hash mismatch")
        if not self.licence.strip() or not self.reviewer.strip():
            raise ValueError("licence and reviewer required")
        return self


class Registry:
    def __init__(self, versions: tuple[SourceVersion, ...], approved_hosts: frozenset[str]):
        self._versions = tuple(versions)
        self._hosts = frozenset(approved_hosts)
        keys = [(v.source_id, v.version) for v in versions]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate evidence version")
        for source_id in {v.source_id for v in versions}:
            owners = {v.owner_id for v in versions if v.source_id == source_id}
            if len(owners) != 1:
                raise ValueError("source ownership cannot change")

    def _latest(self):
        latest = {}
        for v in self._versions:
            if v.source_id not in latest or v.version > latest[v.source_id].version:
                latest[v.source_id] = v
        return latest.values()

    def public_catalog(self, topic: str) -> tuple[SourceVersion, ...]:
        """Public metadata boundary, including stale versions for explicit labels.

        Private evidence is excluded even for its owner. A withdrawal on the
        newest version never resurrects an older approved version.
        """
        return tuple(sorted((v for v in self._latest() if v.owner_id is None and
            v.approved and v.url.scheme == 'https' and v.url.host in self._hosts and v.topic == topic),
            key=lambda v: v.source_id))

    @traceable(name="knowledge.retrieve")
    def retrieve(self, topic: str, *, owner_id: int, as_of: date) -> tuple[SourceVersion, ...]:
        return tuple(v for v in self._latest() if (
            v.approved and v.url.scheme == "https" and v.url.host in self._hosts
            and v.owner_id in (None, owner_id) and v.topic == topic
            and v.published <= as_of and v.fetched <= as_of
            and v.effective <= as_of < v.expires))

    def resolve(self, source_id: str, version: int, topic: str, *, owner_id: int, as_of: date):
        return next((v for v in self.retrieve(topic, owner_id=owner_id, as_of=as_of)
                     if (v.source_id, v.version) == (source_id, version)), None)
