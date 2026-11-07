"""Offline research contract and exact scenario arithmetic; live adapter disabled."""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from datetime import date


class ResearchFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    instrument_id: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    currency: Literal["INR"]
    period: str = Field(min_length=1)
    basis: Literal["standalone", "consolidated"]
    units: Literal["paise"]
    restated: bool
    price_date: date
    source_id: str = Field(min_length=1)
    source_version: int = Field(gt=0)
    value: int | None = Field(ge=0, strict=True)


def ratio(numerator: ResearchFact, denominator: ResearchFact) -> Decimal | None:
    keys = ("instrument_id", "exchange", "currency", "period", "basis", "units", "restated", "price_date")
    if any(getattr(numerator, k) != getattr(denominator, k) for k in keys):
        raise ValueError("incompatible research facts")
    if numerator.value is None or denominator.value in (None, 0):
        return None
    return Decimal(numerator.value) / Decimal(denominator.value)


def discounted_scenario(cashflows: tuple[int, ...], discount: Decimal) -> dict:
    if not discount.is_finite() or discount <= 0 or any(type(c) is not int for c in cashflows):
        raise ValueError("positive finite discount and integer paise required")
    value = sum((Decimal(c) / (1 + discount) ** t for t, c in enumerate(cashflows, 1)), Decimal(0))
    return {"kind": "assumption_scenario", "value_paise_unrounded": value,
            "discount": discount, "rule_version": "research.v1",
            "limitation": "User assumptions; no terminal value or target price"}


class DisabledMarketAdapter:
    def fetch(self, instrument_id: str):
        return {"status": "unavailable", "reason": "Licensed feed and research release review required"}
