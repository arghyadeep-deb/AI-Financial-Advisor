"""Exact INR asset-class sandbox contracts. No security selection or execution."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.core.money import MAX_PAISE

Asset = Literal["cash", "debt", "equity", "gold"]
ASSET_ORDER = ("cash", "debt", "equity", "gold")


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class Bound(Contract):
    asset: Asset
    minimum_bps: int = Field(ge=0, le=10000)
    target_bps: int = Field(ge=0, le=10000)
    maximum_bps: int = Field(ge=0, le=10000)
    adverse_return_bps: int = Field(ge=-10000, le=0)
    favourable_return_bps: int = Field(ge=0, le=10000)
    annual_fee_bps: int = Field(ge=0, le=10000)
    liquidity_days: int = Field(ge=0)
    illustrative_return_bps: int | None = Field(default=None, ge=-10000, le=10000)
    illustrative_volatility_bps: int | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="after")
    def ordered(self):
        if not self.minimum_bps <= self.target_bps <= self.maximum_bps:
            raise ValueError("bounds must contain target")
        return self


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
        return self


class Constraints(Contract):
    # Explicit current cash after unfunded commitments/reserves, each counted once.
    eligible_liquid_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    liquidity_floor_bps: int = Field(default=1000, ge=0, le=10000)
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
    assumption_version: str
    coverage: Literal["synthetic_scenario"] = "synthetic_scenario"
