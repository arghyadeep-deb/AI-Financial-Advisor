"""Synthetic, read-only household contracts. Integer paise and basis-point shares."""
from datetime import date
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from backend.core.money import MAX_PAISE

Paise = Annotated[int, Field(strict=True, ge=0, le=MAX_PAISE)]


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Observation(Contract):
    reference: str = Field(min_length=1, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')
    kind: Literal['asset', 'liability']
    value_paise: Paise
    share_bps: int = Field(strict=True, ge=1, le=10000)
    valued_on: date
    currency: Literal['INR'] = 'INR'
    source: Literal['user_declared'] = 'user_declared'
    liquidity: Literal['liquid', 'illiquid', 'unknown'] = 'unknown'
    projected: Literal[False] = False

    @model_validator(mode='after')
    def observed(self):
        if self.valued_on > date.today():
            raise ValueError('Future valuations are not observations')
        if self.value_paise * self.share_bps % 10000:
            raise ValueError('Ownership must resolve to whole paise')
        return self


class NetWorth(Contract):
    observations: list[Observation] = Field(max_length=200)
    coverage: Literal['partial'] = 'partial'

    @model_validator(mode='after')
    def consistent_references(self):
        seen = {}
        for item in self.observations:
            if item.reference in seen and seen[item.reference] != item:
                raise ValueError('Conflicting duplicate reference')
            seen[item.reference] = item
        return self


class Write(Contract):
    expected_revision: int = Field(strict=True, ge=0)
    idempotency_key: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=200)


class NetWorthWrite(Write):
    data: NetWorth


class HouseholdCreate(Contract):
    label: str = Field(min_length=1, max_length=80)
    adult_confirmed: Literal[True]


class InviteCreate(Contract):
    member_id: int = Field(strict=True, ge=1)
    expected_revision: int = Field(strict=True, ge=1)
    adult_confirmed: Literal[True]


class InviteAccept(Contract):
    token: SecretStr = Field(min_length=43, max_length=43)
    adult_confirmed: Literal[True]


class GrantWrite(Contract):
    member_id: int = Field(strict=True, ge=1)
    view: Literal['networth', 'protection']
    expected_revision: int = Field(strict=True, ge=0)
    granted: bool = Field(strict=True)


class MembershipRevoke(Contract):
    expected_revision: int = Field(strict=True, ge=1)


class Policy(Contract):
    reference: str = Field(min_length=1, max_length=80)
    policy_type: Literal['life', 'health', 'property', 'other', 'unknown'] = 'unknown'
    insurer: str | None = Field(None, min_length=1, max_length=100)
    coverage_paise: Paise | None = None
    premium_paise: Paise | None = None
    renewal_date: date | None = None
    exclusions: str | None = Field(None, max_length=500)
    waiting_period: str | None = Field(None, max_length=200)
    dependent_coverage: str | None = Field(None, max_length=200)
    evidence: dict[str, str] = Field(default_factory=dict, max_length=8)
    nominee_check_complete: bool = Field(False, strict=True)
    emergency_location_check_complete: bool = Field(False, strict=True)
    reminder_opt_in: bool = Field(False, strict=True)
    archived: bool = Field(False, strict=True)
    source: Literal['user_declared'] = 'user_declared'

    @model_validator(mode='after')
    def evidenced(self):
        fields = {'insurer', 'coverage_paise', 'premium_paise', 'renewal_date',
                  'exclusions', 'waiting_period', 'dependent_coverage', 'policy_type'}
        if set(self.evidence) - fields or any(not value.strip() or len(value) > 160 for value in self.evidence.values()):
            raise ValueError('Invalid evidence references')
        for name in fields:
            if getattr(self, name) not in (None, 'unknown') and name not in self.evidence:
                raise ValueError('Entered policy facts require a declaration/evidence reference')
        if self.reminder_opt_in and self.renewal_date is None:
            raise ValueError('Renewal date required for reminders')
        return self


class Protection(Contract):
    policies: list[Policy] = Field(max_length=100)

    @model_validator(mode='after')
    def unique(self):
        if len({p.reference for p in self.policies}) != len(self.policies):
            raise ValueError('Duplicate policy reference')
        return self


class ProtectionWrite(Write):
    data: Protection
