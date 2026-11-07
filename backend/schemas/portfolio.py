"""Owner-confirmed full-book observations; never inferred from bank movements."""
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import Field, StrictBool, StrictInt, field_validator, model_validator
from backend.schemas.statements import Contract, Operation
from backend.schemas.planning import Money, GoalPlan
from backend.finance.suitability import Suitability
from engines.allocation.contracts import Asset


class Observation(Contract):
    account_ref: str = Field(min_length=1, max_length=80)
    instrument_id: str = Field(min_length=1, max_length=80)
    issuer_id: str | None = Field(default=None, max_length=80)
    asset_class: Asset | None = None
    currency: Literal['INR'] = 'INR'
    units: str = Field(max_length=40)
    observation_date: date
    price_paise: Money | None = None
    price_date: date | None = None
    price_source: str | None = Field(default=None, min_length=1, max_length=100)
    price_version: StrictInt | None = Field(default=None, ge=1)
    price_expires: date | None = None
    cost_basis_paise: Money | None = None
    corporate_actions_supported: StrictBool = False
    closed: StrictBool = False

    @field_validator('units')
    @classmethod
    def units_valid(cls, value):
        try:
            d = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError('Units require an exact decimal string.') from exc
        if not d.is_finite() or not 0 <= d <= Decimal('1000000000000') or d.as_tuple().exponent < -8:
            raise ValueError('Units require a nonnegative decimal with at most eight places.')
        return value

    @model_validator(mode='after')
    def consistent(self):
        if self.closed and Decimal(self.units) != 0:
            raise ValueError('Closed positions require zero units.')
        if self.price_date and self.price_expires and self.price_expires <= self.price_date:
            raise ValueError('Price expiry must follow price date.')
        return self


class Holdings(Contract):
    confirmed: Literal[True]
    source: Literal['manual', 'csv']
    as_of: date
    inventory_complete: StrictBool = False
    observations: list[Observation] = Field(max_length=500)

    @field_validator('confirmed', mode='before')
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError('Explicit owner confirmation required.')
        return value

    @model_validator(mode='after')
    def no_overlap(self):
        keys = [(p.account_ref, p.instrument_id) for p in self.observations]
        if len(keys) != len(set(keys)):
            raise ValueError('Overlapping account/instrument sources require review; submit one confirmed observation.')
        if any(p.observation_date != self.as_of for p in self.observations):
            raise ValueError('All observations must share the book date.')
        return self


class HoldingsWrite(Operation):
    data: Holdings


class SuitabilityWrite(Operation):
    data: Suitability


class CSVPreview(Contract):
    csv_text: str = Field(min_length=1, max_length=250000)
    as_of: date


class ShockRequest(Contract):
    expected_revision: StrictInt = Field(ge=1)
    as_of: date
    shock_bps: StrictInt = Field(ge=-10000, le=10000)
    contribution_paise: Money = 0


class AllocationScenario(Operation):
    expected_profile_revision: StrictInt = Field(ge=1)
    expected_holdings_revision: StrictInt = Field(ge=1)
    expected_suitability_revision: StrictInt = Field(ge=1)
    expected_planning_vector: dict[str, StrictInt]
    assumptions_accepted: Literal[True]
    eligible_liquid_paise: Money | None = None
    planning_capacity: GoalPlan | None = None
    excluded_assets: list[Asset] = Field(default_factory=list, max_length=4)
    liquidity_floor_bps: StrictInt = Field(default=1000, ge=0, le=10000)
    maximum_liquidity_days: StrictInt | None = Field(default=None, ge=0, le=3650)

    @field_validator('assumptions_accepted', mode='before')
    @classmethod
    def explicit_acceptance(cls, value):
        if value is not True:
            raise ValueError('Explicit synthetic assumptions acceptance required.')
        return value
