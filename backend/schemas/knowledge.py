"""Public sample education contracts. No private-evidence or action inputs."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class EducationRequest(Contract):
    topic: str = Field(min_length=1, max_length=80, pattern=r'^[a-z_]+$')


class Citation(Contract):
    source_id: str
    version: StrictInt
    title: str
    url: str
    content_hash: str
    published: date
    fetched: date
    effective: date
    expires: date
    licence: str
    jurisdiction: Literal['IN']
    staleness: Literal['current', 'expired', 'not_yet_current']
    sample_only: Literal[True] = True
    resolve_path: str


class EducationAnswer(Contract):
    topic: str
    kind: Literal['generic_education'] = 'generic_education'
    status: Literal['complete', 'unavailable']
    text: str
    reason: str | None = None
    as_of: date
    staleness: Literal['current', 'expired', 'not_yet_current', 'unavailable', 'conflicting']
    sources: list[Citation]
    corpus: Literal['public_sample_only'] = 'public_sample_only'
    rule_version: Literal['education.v1'] = 'education.v1'
    personalized_advice_enabled: Literal[False] = False
