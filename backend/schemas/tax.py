"""Synthetic tax-review contracts. No PAN, real forms, paths or model text."""
from typing import Literal
from pydantic import Field, StrictBool, StrictInt
from backend.schemas.statements import Contract, Operation
from backend.schemas.planning import Money


class TaxSource(Contract):
    source_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    layout: Literal['synthetic-salary-v1']
    identity_ref: str = Field(pattern=r'^fictional-[A-Za-z0-9_-]{1,40}$')
    financial_year: str = Field(max_length=16)
    salary_paise: Money
    withholding_paise: Money | None = None


class TaxInputs(Contract):
    financial_year: str = Field(max_length=16)
    assessment_year: str = Field(max_length=16)
    individual: StrictBool
    resident: StrictBool
    employer_count: StrictInt = Field(ge=0, le=100)
    identity_ref: str = Field(pattern=r'^fictional-[A-Za-z0-9_-]{1,40}$')
    other_income: list[str] = Field(default_factory=list, max_length=20)
    deductions_claimed: StrictBool = False
    sources: list[TaxSource] = Field(min_length=1, max_length=10)


class CaseWrite(Operation):
    data: TaxInputs


class FieldResolution(Contract):
    field: Literal['identity', 'period', 'income', 'withholding']
    source_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    explanation: str = Field(min_length=1, max_length=200)


class ReviewWrite(Operation):
    resolutions: list[FieldResolution] = Field(default_factory=list, max_length=4)
    confirmed: StrictBool


class DraftWrite(Operation):
    pass
