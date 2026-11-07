"""Versioned, file-backed allocation evidence. No reviewer approval is inferred."""
from datetime import date
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    publisher: str = Field(min_length=1)


class Assumption(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    id: str = Field(min_length=1)
    version: int = Field(gt=0)
    value: int
    source: Source
    as_of: date
    methodology: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    expires: date
    status: Literal['synthetic_test', 'unvalidated_prototype', 'validated']

    @model_validator(mode='after')
    def dates(self):
        if self.expires <= self.as_of:
            raise ValueError('assumption expiry must follow as-of date')
        return self

    def current(self, day: date) -> bool:
        return self.as_of <= day < self.expires


class AssumptionRegister(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)
    version: str = Field(min_length=1)
    assumptions: tuple[Assumption, ...] = Field(min_length=1)
    historical_data_notice: Literal['Historical data never guarantees future returns.'] = 'Historical data never guarantees future returns.'

    @model_validator(mode='after')
    def unique(self):
        if len({a.id for a in self.assumptions}) != len(self.assumptions):
            raise ValueError('duplicate assumption id')
        return self

    def validated(self, day: date) -> bool:
        return all(a.status == 'validated' and a.current(day) for a in self.assumptions)


def load_register() -> AssumptionRegister:
    path = Path(__file__).resolve().parents[2] / 'knowledge_base/allocation/register-v1.json'
    register = AssumptionRegister.model_validate_json(path.read_text(encoding='utf-8'))
    values = {a.id: a.value for a in register.assumptions}
    if (set(values) != {'cash_floor_bps', 'near_term_months'}
            or not 0 <= values['cash_floor_bps'] <= 10000
            or not 1 <= values['near_term_months'] <= 1200):
        raise ValueError('invalid prototype policy configuration')
    return register


def policy_value(identity: str) -> int:
    return next(a.value for a in load_register().assumptions if a.id == identity)
