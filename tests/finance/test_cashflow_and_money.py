"""T104 / T105 / T115 — exact money and cash-flow rules with INDEPENDENT expected values.

Expected figures are written out by hand from specs/financial-rules.md, not
derived by calling the implementation under test.
"""
import math
from decimal import Decimal

import pytest

from backend.core.money import (MAX_PAISE, MoneyError, format_inr, paise_to_decimal, parse_rupees,
                                rupees_to_paise, sum_paise)
from engines.cashflow import (build_snapshot, contribution_from_capacity, emergency_gap_paise,
                              flow_capacity_paise, reserve_funding_paise)

R = 100  # paise per rupee


def snap(**kw):
    base = dict(income_paise=0, expenses_paise=0, savings_paise=0, investments_paise=0,
                debt_balance_paise=0, monthly_debt_payment_paise=0, credit_score=None)
    base.update(kw)
    return build_snapshot(base, owner_id=1, profile_revision=1)


# ── FIN-01 ────────────────────────────────────────────────────────────────
def test_FIN01_deficit_45000_vs_55000():
    s = snap(income_paise=45_000 * R, expenses_paise=55_000 * R, savings_paise=0)
    assert s.surplus_paise == -10_000 * R
    assert s.shortfall_paise == 10_000 * R
    assert s.available_contribution_paise == 0
    assert s.contribution_status == "none"


# ── FIN-14 (flow capacity is 3,000, never the naive 10,000) ───────────────
def test_FIN14_flow_capacity_counts_each_commitment_once():
    cap = flow_capacity_paise(income=65_000 * R, spending=55_000 * R, obligations=4_000 * R,
                              reserve_funding=3_000 * R)
    assert cap == 3_000 * R


def test_contribution_is_never_negative_and_keeps_a_buffer():
    assert contribution_from_capacity(-5_000 * R) == 0
    assert contribution_from_capacity(0) == 0
    assert contribution_from_capacity(10_000 * R) == 9_000 * R          # 10% buffer, exact
    assert contribution_from_capacity(1) == 0                            # floors, never rounds up


def test_emergency_gap_and_reserve_funding_hand_computed():
    # 6 months of 20,000 = 120,000; savings 30,000 -> gap 90,000 -> 7,500/month over 12
    gap = emergency_gap_paise(30_000 * R, 20_000 * R)
    assert gap == 90_000 * R
    assert reserve_funding_paise(gap) == 7_500 * R
    assert emergency_gap_paise(500_000 * R, 20_000 * R) == 0
    assert reserve_funding_paise(0) == 0
    assert reserve_funding_paise(1) == 1                                  # ceiling: never under-funds


def test_positive_surplus_scenario_matches_hand_calculation():
    # income 100,000 ; expenses 40,000 ; savings 240,000 (=6 months, gap 0); debt payment 10,000
    s = snap(income_paise=100_000 * R, expenses_paise=40_000 * R, savings_paise=240_000 * R,
             debt_balance_paise=500_000 * R, monthly_debt_payment_paise=10_000 * R)
    assert s.flow_capacity_paise == 50_000 * R
    assert s.available_contribution_paise == 45_000 * R
    assert s.contribution_status == "available"


def test_reserve_top_up_cannot_exceed_available_cash():
    # gap 330,000 -> naive top-up 27,500/month, but only 10,000 is left after expenses
    s = snap(income_paise=65_000 * R, expenses_paise=55_000 * R, savings_paise=0)
    assert s.emergency_gap_paise == 330_000 * R
    assert s.reserve_funding_paise == 10_000 * R
    assert s.flow_capacity_paise == 0
    assert s.available_contribution_paise == 0 and s.contribution_status == "none"


def test_debt_balance_without_payment_makes_contribution_unavailable_not_positive():
    s = snap(income_paise=100_000 * R, expenses_paise=40_000 * R, savings_paise=240_000 * R,
             debt_balance_paise=500_000 * R, monthly_debt_payment_paise=None)
    assert s.available_contribution_paise is None
    assert s.contribution_status == "unavailable"
    assert "monthly_debt_payment" in s.missing_inputs and s.status == "partial"


def test_zero_balance_profile_is_valid_and_zero_not_unknown():
    s = snap(income_paise=50_000 * R, expenses_paise=50_000 * R)
    assert s.surplus_paise == 0 and s.shortfall_paise == 0
    assert s.available_contribution_paise == 0


def test_unknown_credit_score_is_listed_missing_and_not_defaulted():
    s = snap(income_paise=1 * R, expenses_paise=0)
    assert s.credit_score is None and "credit_score" in s.missing_inputs
    assert s.metric_provenance["credit_score"] == "unavailable"


def test_snapshot_carries_required_envelope_fields():
    s = snap(income_paise=1 * R, expenses_paise=0).to_dict()
    for key in ("owner_id", "schema_version", "source_revision_vector", "rule_version", "created_at",
                "as_of", "coverage", "status", "metric_provenance", "missing_inputs"):
        assert key in s
    assert s["source_revision_vector"] == {"profile_revision": 1}


# ── Exact money ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("value,paise", [
    (0, 0), (1, 100), (45000, 4_500_000), (0.1, 10), (1234.5, 123_450), ("1,23,456.78", 12_345_678),
    (Decimal("99.99"), 9_999), (19.99, 1_999),
])
def test_rupees_to_paise_exact(value, paise):
    assert rupees_to_paise(value) == paise


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 1.005, 0.001, -1, True, None, "abc",
                                 "", 10 ** 15, [1], {"a": 1}])
def test_invalid_money_is_rejected_not_coerced(bad):
    with pytest.raises(MoneyError):
        rupees_to_paise(bad)


def test_binary_float_artifacts_do_not_leak():
    # 0.1 + 0.2 is 0.30000000000000004 in binary floats: the artefact is refused, the typed value is exact.
    with pytest.raises(MoneyError):
        rupees_to_paise(0.1 + 0.2)
    assert rupees_to_paise(0.3) == 30
    assert sum_paise([rupees_to_paise(0.1), rupees_to_paise(0.2)]) == 30


def test_paise_round_trip_and_bounds():
    for p in (0, 1, 99, 100, 123_456_789, MAX_PAISE):
        assert rupees_to_paise(paise_to_decimal(p)) == p
    with pytest.raises(MoneyError):
        paise_to_decimal(MAX_PAISE + 1)
    with pytest.raises(MoneyError):
        sum_paise([MAX_PAISE, MAX_PAISE])


def test_indian_grouping_format():
    assert format_inr(1_234_567_800) == "Rs 1,23,45,678"
    assert format_inr(-1_000_000) == "-Rs 10,000"
    assert format_inr(12_345) == "Rs 123.45"
    assert format_inr(None) == "unavailable"
