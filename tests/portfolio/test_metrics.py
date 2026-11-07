from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from engines.portfolio import Position, metrics, shock

DAY = date(2026, 11, 7)


def position(id="A", **changes):
    return Position(**{**dict(observation_id=id, instrument_id=id, issuer_id=id, asset_class="equity",
                              units=Decimal("2.5"), price_paise=10000, price_date=DAY,
                              source_id="synthetic", source_version=1, expires=date(2026, 11, 8),
                              cost_basis_paise=20000, corporate_actions_supported=True), **changes})


def test_independent_valuation_concentration_gain():
    # A = 2.5*10000 =25000; B=7.5*10000=75000. HHI=.25^2+.75^2=5/8.
    p = (position(), position("B", units=Decimal("7.5"), cost_basis_paise=60000))
    result = metrics(p, as_of=DAY)
    assert result["total_value_paise"] == 100000
    assert result["issuer_hhi"] == "5/8" and result["largest_issuer_share"] == "3/4"
    assert result["absolute_gain_paise"] == 20000
    assert result == metrics(p, as_of=DAY)
    assert shock(100000, -2500)["scenario_value_paise"] == 75000
    assert result["xirr"] is None and result["benchmark"] is None


def test_aggregate_exact_rounding():
    # Two half-paise valuations: sum exact first gives 1 paise, not zero.
    p = (position(units=Decimal("0.5"), price_paise=1),
         position("B", units=Decimal("0.5"), price_paise=1))
    assert metrics(p, as_of=DAY)["total_value_paise"] == 1


@pytest.mark.parametrize("changes", [dict(price_paise=None), dict(price_date=None), dict(currency="USD"),
                                     dict(source_id=None), dict(source_version=None), dict(expires=DAY),
                                     dict(price_date=date(2026, 11, 8))])
def test_missing_stale_foreign_future_is_partial(changes):
    r = metrics((position(), position("B", **changes)), as_of=DAY)
    assert r["status"] == "partial" and r["total_value_paise"] is None
    assert r["known_subtotal_paise"] == 25000 and r["absolute_gain_paise"] is None


def test_missing_basis_actions_classification_never_low_risk():
    r = metrics((position(cost_basis_paise=None, issuer_id=None, asset_class=None),), as_of=DAY)
    assert r["absolute_gain_paise"] is None and r["issuer_hhi"] is None
    assert r["unknown_issuer_paise"] == 25000 and r["unknown_class_paise"] == 25000
    assert r["low_risk_claim"] is False
    assert metrics((position(corporate_actions_supported=False),), as_of=DAY)["absolute_gain_paise"] is None
    assert metrics((), as_of=DAY)["status"] == "unavailable"


def test_invalid_overlap_precision_overflow():
    with pytest.raises(ValueError, match="overlap"):
        metrics((position(), position()), as_of=DAY)
    for units in (Decimal("NaN"), Decimal("Infinity"), Decimal("-1"), Decimal("0.000000001")):
        with pytest.raises(ValidationError):
            position(units=units)
    with pytest.raises(ValueError):
        metrics((position(units=Decimal("1000000000000")),), as_of=DAY)
    with pytest.raises(ValueError):
        shock(100, -10001)
