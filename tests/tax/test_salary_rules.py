"""Synthetic boundary goldens, independent arithmetic in INR comments."""
import pytest
from pydantic import ValidationError

from engines.tax import SalaryCase, estimate, round_statutory_ten


def case(salary, **changes):
    return SalaryCase(**{**dict(financial_year="2024-25", assessment_year="2025-26", regime="new",
                                resident=True, employer_count=1, salary_paise=salary,
                                other_deductions_claimed=False, evidence_complete=True,
                                identity_period_conflict=False), **changes})


@pytest.mark.parametrize("salary,tax", [(0, 0), (37500000, 0), (77500000, 0),
                                       (78500000, 1040000), (107500000, 5200000),
                                       (127500000, 8320000), (157500000, 14560000)])
def test_hand_calculated_boundaries(salary, tax):
    # Standard deduction 75k. At taxable 10L: 4L*5%+3L*10%=50k; cess2k.
    # At 12L: 50k+2L*15%=80k, cess3.2k. At 15L: 80k+3L*20%=140k, cess5.6k.
    # At 7.1L: base21k reduced to excess10k, cess400 =>10,400.
    result = estimate(case(salary))
    assert result["tax_paise"] == tax
    assert result["balance_payable_paise"] is None
    assert result["production_approved"] is False


def test_marginal_relief_and_settlement():
    r = estimate(case(78500000, withholding_paise=1200000))
    assert r["gross_tax_paise"] == 2100000
    assert r["marginal_relief_paise"] == 1100000
    assert r["refund_paise"] == 160000 and r["balance_payable_paise"] == 0
    assert estimate(case(107500000, withholding_paise=5000000))["balance_payable_paise"] == 200000


@pytest.mark.parametrize("paise,rounded", [(499, 0), (500, 1000), (1499, 1000), (1500, 2000)])
def test_statutory_rounding(paise, rounded):
    assert round_statutory_ten(paise) == rounded


@pytest.mark.parametrize("changes", [dict(financial_year="2025-26"), dict(assessment_year="2026-27"),
                                     dict(regime="old"), dict(resident=False), dict(employer_count=2),
                                     dict(other_income_categories=("capital_gain",)), dict(other_deductions_claimed=True),
                                     dict(evidence_complete=False), dict(identity_period_conflict=True)])
def test_scope_refusal(changes):
    r = estimate(case(100000000, **changes))
    assert r["status"] == "unsupported" and r["tax_paise"] is None and r["reasons"]


def test_surcharge_and_invalid_money():
    assert estimate(case(500000001))["status"] == "unsupported"
    for amount in (-1, True, 10**14, float("nan")):
        with pytest.raises(ValidationError):
            case(amount)
