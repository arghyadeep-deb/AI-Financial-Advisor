"""Pure dated INR valuation, concentration and shock math, without proposals."""
from datetime import date
from decimal import Decimal
from fractions import Fraction

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.core.money import MAX_PAISE, check_paise
from .rules import RULES


class Position(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    observation_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    account_ref: str = 'unspecified'
    issuer_id: str | None = None
    asset_class: str | None = None
    currency: str = "INR"
    units: Decimal
    price_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    price_date: date | None = None
    source_id: str | None = None
    source_version: int | None = Field(default=None, gt=0)
    expires: date | None = None
    cost_basis_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    corporate_actions_supported: bool = False

    @field_validator("units")
    @classmethod
    def exact_units(cls, v):
        if not v.is_finite() or not 0 <= v <= Decimal("1000000000000") or v.as_tuple().exponent < -8:
            raise ValueError("units must be finite, nonnegative, at most 8 decimal places")
        return v


def _rounded(value: Fraction) -> int:
    # Fraction avoids context-dependent Decimal multiplication rounding.
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 > value.denominator or (remainder * 2 == value.denominator and quotient % 2):
        quotient += 1
    return check_paise(quotient)


def _conserved_groups(groups, unknown):
    """Largest remainders conserve the aggregate rounded subtotal exactly."""
    values = {**groups, None: unknown}
    rounded = {k: v.numerator // v.denominator for k, v in values.items()}
    remainder = _rounded(sum(values.values(), Fraction(0))) - sum(rounded.values())
    order = sorted(values, key=lambda k: (-(values[k] - rounded[k]), str(k)))
    for k in order[:remainder]:
        rounded[k] += 1
    return {k: v for k, v in rounded.items() if k is not None}, rounded[None]


def metrics(positions: tuple[Position, ...], *, as_of: date) -> dict:
    if len({p.observation_id for p in positions}) != len(positions) or len({(p.account_ref, p.instrument_id) for p in positions}) != len(positions):
        raise ValueError("overlapping observations require review before aggregation")
    values, missing, issuers, classes = [], [], {}, {}
    basis = 0
    basis_complete = True
    actions_supported = True
    unknown_issuer = Fraction(0)
    unknown_class = Fraction(0)
    for p in positions:
        if (p.currency != RULES.currency or p.price_paise is None or p.price_date is None
            or not p.source_id or p.source_version is None or p.expires is None
            or p.price_date > as_of or not p.price_date <= as_of < p.expires):
            missing.append(p.observation_id)
            continue
        value = Fraction(p.units) * p.price_paise
        check_paise(_rounded(value))
        values.append(value)
        if p.issuer_id:
            issuers[p.issuer_id] = issuers.get(p.issuer_id, Fraction(0)) + value
        else:
            unknown_issuer += value
        if p.asset_class:
            classes[p.asset_class] = classes.get(p.asset_class, Fraction(0)) + value
        else:
            unknown_class += value
        basis_complete &= p.cost_basis_paise is not None
        basis += p.cost_basis_paise or 0
        check_paise(basis)
        actions_supported &= p.corporate_actions_supported
    total = sum(values, Fraction(0))
    rounded_classes, rounded_unknown_class = _conserved_groups(classes, unknown_class)
    rounded_issuers, rounded_unknown_issuer = _conserved_groups(issuers, unknown_issuer)
    complete = bool(positions) and not missing
    hhi = sum(((v / total) ** 2 for v in issuers.values()), Fraction(0)) if total else None
    return {"rule_version": RULES.version, "status": "complete" if complete else "partial" if values else "unavailable",
            "as_of": as_of.isoformat(), "currency": "INR", "priced_positions": len(values),
            "total_positions": len(positions), "missing_price_observations": missing,
            "known_subtotal_paise": _rounded(total), "total_value_paise": _rounded(total) if complete else None,
            "asset_class_paise": rounded_classes,
            "issuer_paise": rounded_issuers,
            "unknown_class_paise": rounded_unknown_class, "unknown_issuer_paise": rounded_unknown_issuer,
            "issuer_hhi": str(hhi) if hhi is not None and unknown_issuer == 0 and complete else None,
            "largest_issuer_share": str(max(issuers.values()) / total) if issuers and total else None,
            "concentration_scope": "priced subset only", "low_risk_claim": False,
            "absolute_gain_paise": _rounded(total - basis) if complete and basis_complete and actions_supported else None,
            "xirr": None, "twr": None, "benchmark": None,
            "performance_status": "unavailable: dated flows/valuations and corporate-action support required",
            "source_revision_vector": {p.observation_id: {"source_id": p.source_id, "version": p.source_version,
                                                         "price_date": None if p.price_date is None else p.price_date.isoformat()}
                                       for p in positions}}


def shock(value_paise: int, shock_bps: int) -> dict:
    check_paise(value_paise)
    if value_paise < 0 or type(shock_bps) is not int or not -10000 <= shock_bps <= 10000:
        raise ValueError("invalid non-leveraged shock")
    return {"rule_version": RULES.version, "status": "hypothetical",
            "scenario_value_paise": _rounded(Fraction(value_paise * (10000 + shock_bps), 10000)),
            "observed_value_paise": value_paise}
