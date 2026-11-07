"""Offline planning contracts. Money is strict integer paise; assumptions are explicit."""
from datetime import date
from typing import Annotated, Literal
from pydantic import Field, StrictInt, StrictBool
from backend.schemas.statements import Contract
from backend.core.money import MAX_PAISE

Money = Annotated[StrictInt, Field(ge=0, le=MAX_PAISE)]
Category = Annotated[str, Field(min_length=1, max_length=40, pattern=r'^[a-z][a-z0-9_]*$')]


class Budget(Contract):
    month: str = Field(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$')
    currency: Literal['INR'] = 'INR'
    lines: dict[Category, Money] = Field(min_length=1, max_length=50)
    rollover: Literal['none', 'positive'] = 'none'
    archived: StrictBool = False


class Obligation(Contract):
    label: str = Field(min_length=1, max_length=80)
    amount_paise: Money
    due_date: date
    cadence: Literal['once', 'monthly', 'annual'] = 'once'
    variable: StrictBool = False
    paused: StrictBool = False
    archived: StrictBool = False
    reminder_opt_in: StrictBool = False
    candidate_entry_ids: list[str] = Field(default_factory=list, max_length=100)


class Settlement(Contract):
    obligation_id: str
    expected_obligation_revision: StrictInt = Field(ge=1)
    entry_id: str
    expected_entry_revision: StrictInt = Field(ge=1)
    reversed: StrictBool = False


class Receivable(Contract):
    purchase_entry_id: str
    expected_entry_revision: StrictInt = Field(ge=1)
    due_paise: Money
    archived: StrictBool = False


class Goal(Contract):
    label: str = Field(min_length=1, max_length=80)
    target_paise: Money
    allocated_paise: Money = 0
    target_date: date
    value_basis: Literal['present', 'future'] = 'future'
    inflation_bps: StrictInt = Field(default=0, ge=0, le=3000)
    annual_return_bps: Literal[0] = 0
    priority: StrictInt = Field(default=1, ge=1, le=100)
    funding_account_id: str
    archived: StrictBool = False


class Debt(Contract):
    label: str = Field(min_length=1, max_length=80)
    obligation_id: str
    principal_paise: Money
    annual_rate_bps: StrictInt | None = Field(default=None, ge=0, le=100000)
    rate_type: Literal['fixed', 'floating'] = 'fixed'
    convention: Literal['monthly_reducing'] = 'monthly_reducing'
    minimum_payment_paise: Money
    monthly_fee_paise: Money = 0
    prepayment_fee_paise: Money = 0
    term_months: StrictInt | None = Field(default=None, ge=1, le=600)
    evidence_date: date
    archived: StrictBool = False


class RevisionWrite(Contract):
    expected_revision: StrictInt = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r'^[A-Za-z0-9._:-]+$')
    reason: str = Field(min_length=1, max_length=200)


class BudgetWrite(RevisionWrite):
    data: Budget


class ObligationWrite(RevisionWrite):
    data: Obligation


class SettlementWrite(RevisionWrite):
    data: Settlement


class ReceivableWrite(RevisionWrite):
    data: Receivable


class GoalWrite(RevisionWrite):
    data: Goal


class DebtWrite(RevisionWrite):
    data: Debt


class Capacity(Contract):
    """User-declared future assumptions, never inferred from a monthly surplus."""
    report_id: str
    expected_planning_vector: dict[str, StrictInt]
    evidence_date: date
    income_paise: Money
    spending_paise: Money
    eligible_liquid_paise: Money
    reserve_funding_paise: Money = 0
    earmarks_paise: Money = 0
    included_obligation_ids: list[str] = Field(default_factory=list, max_length=100)
    obligations_complete: StrictBool = False
    assumptions_confirmed: StrictBool = False


class GoalPlan(Capacity):
    as_of: date
    reserve_months: StrictInt = Field(default=6, ge=0, le=36)
    essential_expenses_paise: Money = 0


class DebtScenario(Capacity):
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r'^[A-Za-z0-9._:-]+$')
    strategy: Literal['avalanche', 'snowball']
    extra_payment_paise: Money = 0
    max_months: StrictInt = Field(default=360, ge=1, le=600)
