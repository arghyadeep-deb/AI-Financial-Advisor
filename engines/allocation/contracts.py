"""Exact INR asset-class sandbox contracts. No security selection or execution."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.money import MAX_PAISE
from backend.finance.allocation_assumptions import Assumption, AssumptionRegister, policy_value

Asset = Literal["cash", "debt", "equity", "gold"]
ASSET_ORDER = ("cash", "debt", "equity", "gold")


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class LiquidityEvidence(Contract):
    instrument: str = Field(min_length=1)
    restrictions: str = Field(min_length=1)
    settlement: str = Field(min_length=1)
    source: str = Field(min_length=1)
    as_of: date
    expires: date

    @model_validator(mode='after')
    def dates(self):
        if self.expires <= self.as_of:
            raise ValueError('invalid liquidity evidence dates')
        return self


class Bound(Contract):
    asset: Asset
    minimum_bps: int = Field(ge=0, le=10000)
    target_bps: int = Field(ge=0, le=10000)
    maximum_bps: int = Field(ge=0, le=10000)
    adverse_return_bps: int = Field(ge=-10000, le=0)
    favourable_return_bps: int = Field(ge=0, le=10000)
    annual_fee_bps: int = Field(ge=0, le=10000)
    liquidity_days: int | None = Field(default=None, ge=0)
    liquidity_evidence: LiquidityEvidence | None = None
    illustrative_return_bps: int | None = Field(default=None, ge=-10000, le=10000)
    illustrative_volatility_bps: int | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="after")
    def ordered(self):
        if (self.liquidity_days is None) != (self.liquidity_evidence is None):
            raise ValueError('liquidity days require instrument, restriction and settlement evidence')
        if not self.minimum_bps <= self.target_bps <= self.maximum_bps:
            raise ValueError("bounds must contain target")
        return self


class RiskLimit(Contract):
    asset: Literal["equity", "gold"]
    low: int = Field(ge=0, le=10000)
    moderate: int = Field(ge=0, le=10000)
    high: int = Field(ge=0, le=10000)


class AssumptionPack(Contract):
    version: str = Field(min_length=1)
    universe_version: Literal["inr-classes.synthetic.v1", "inr-classes.synthetic.v2"] = "inr-classes.synthetic.v1"
    synthetic_only: Literal[True] = True
    assumption_label: Literal["illustrative_not_a_forecast"] = "illustrative_not_a_forecast"
    source_id: str
    source_version: int = Field(gt=0)
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective: date
    expires: date
    owner: str = Field(min_length=1)
    assets: tuple[Bound, ...]
    status: Literal["synthetic_test"] = "synthetic_test"
    register: AssumptionRegister | None = None
    risk_limits: tuple[RiskLimit, ...] = ()

    @model_validator(mode="after")
    def universe(self):
        expected = set(ASSET_ORDER if self.universe_version.endswith('.v2') else ASSET_ORDER[:3])
        if {b.asset for b in self.assets} != expected or len(self.assets) != len(expected):
            raise ValueError("exactly the supported INR classes required")
        if self.universe_version.endswith('.v2') and any(
            b.illustrative_return_bps is None or b.illustrative_volatility_bps is None for b in self.assets
        ):
            raise ValueError("each illustrative assumption requires return and volatility")
        if sum(b.target_bps for b in self.assets) != 10000 or self.expires <= self.effective:
            raise ValueError("invalid pack dates or target weights")
        if self.register is not None:
            expected = {f'{b.asset}.{k}': v for b in self.assets
                        for k, v in b.model_dump().items() if k not in {'asset', 'liquidity_evidence'} and v is not None}
            expected.update({f'risk.{r.asset}.{k}': getattr(r, k) for r in self.risk_limits
                             for k in ('low', 'moderate', 'high')})
            if {a.id: a.value for a in self.register.assumptions} != expected:
                raise ValueError('register must cover every parameter exactly')
            if any(a.status != 'synthetic_test' for a in self.register.assumptions):
                raise ValueError('invented parameters must remain synthetic_test')
        return self


class Constraints(Contract):
    # Explicit current cash after unfunded commitments/reserves, each counted once.
    eligible_liquid_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    liquidity_floor_bps: int = Field(default_factory=lambda: policy_value("cash_floor_bps"), ge=0, le=10000)
    near_term_months: int = Field(default_factory=lambda: policy_value("near_term_months"), ge=1, le=1200)
    excluded: tuple[Asset, ...] = ()
    bounds: tuple[Bound, ...] | None = None
    maximum_liquidity_days: int | None = Field(default=None, ge=0, le=3650)


class Holding(Contract):
    asset: Asset
    value_paise: int = Field(ge=0, le=MAX_PAISE)


class AllocationResult(Contract):
    rule_version: Literal["allocation.v2"] = "allocation.v2"
    status: Literal["feasible", "infeasible", "insufficient_data", "gated"]
    reasons: tuple[str, ...] = ()
    budget_paise: int = Field(default=0, ge=0, le=MAX_PAISE)
    amounts: tuple[Holding, ...] = ()
    binding_constraints: tuple[str, ...] = ()
    liquidity_days: dict[str, int | None] = Field(default_factory=dict)
    liquidity_explanation: str = "Unknown liquidity is never treated as liquid; instrument, restriction and settlement evidence required."
    policy_status: Literal["unvalidated_prototype"] = "unvalidated_prototype"
    policy_assumptions: tuple[Assumption, ...] = ()
    policy_configuration: dict[str, int] = Field(default_factory=dict)
    policy_explanation: str = "unvalidated_prototype: configurable scenario policy, not universal suitability rules."
    assumption_status: Literal['synthetic_test'] = 'synthetic_test'
    assumption_version: str
    coverage: Literal["synthetic_scenario"] = "synthetic_scenario"
