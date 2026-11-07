from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from backend.core.money import MAX_PAISE
from backend.finance.importers.registry import CATEGORIES, CREDIT, DEBIT


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AccountCreate(Contract):
    label: str = Field(min_length=1, max_length=80)
    token: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    account_type: Literal['synthetic_debit'] = 'synthetic_debit'


class Operation(Contract):
    expected_revision: StrictInt = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r'^[A-Za-z0-9._:-]+$')
    reason: str = Field(min_length=1, max_length=200)


class RowDecision(Contract):
    row_id: str
    category: str
    match_entry_id: str | None = None
    distinct: bool = False

    @model_validator(mode='after')
    def valid(self):
        if self.category not in CATEGORIES or self.match_entry_id and self.distinct:
            raise ValueError('Invalid row decision')
        return self


class Review(Operation):
    decisions: list[RowDecision] = Field(default_factory=list, max_length=10000)
    acknowledge_unverified: bool = False


class Component(Contract):
    category: str
    amount_paise: StrictInt = Field(ge=-MAX_PAISE, le=MAX_PAISE)
    obligation_id: str | None = Field(default=None, max_length=64)
    budget_category: str | None = Field(default=None, min_length=1, max_length=40, pattern=r'^[a-z][a-z0-9_]*$')

    @model_validator(mode='after')
    def valid(self):
        if self.category not in CATEGORIES or self.amount_paise == 0:
            raise ValueError('Invalid component')
        if self.category in CREDIT and self.amount_paise < 0 or self.category in DEBIT and self.amount_paise > 0:
            raise ValueError('Invalid category direction')
        return self


class Split(Operation):
    components: list[Component] = Field(min_length=1, max_length=50)


class LinkCreate(Operation):
    left_id: str
    right_id: str
    expected_right_revision: StrictInt = Field(ge=1)
    kind: Literal['transfer', 'card_settlement', 'refund', 'reimbursement']
    amount_paise: StrictInt = Field(gt=0, le=MAX_PAISE)


class ReportCreate(Contract):
    month: str = Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    account_ids: list[str] = Field(min_length=1, max_length=50)
    expected_vector: dict[str, list[StrictInt]]
    restates_report_id: str | None = None
    restatement_refund_ids: list[str] = Field(default_factory=list, max_length=100)
    restatement_reason: str | None = Field(default=None, min_length=1, max_length=200)
