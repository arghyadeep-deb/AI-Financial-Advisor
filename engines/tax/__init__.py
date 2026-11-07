"""Pure archived-period salary estimate, not a tax return or filing service."""
from pydantic import BaseModel, ConfigDict, Field

from backend.core.money import MAX_PAISE
from .rules import SALARY_FY2024_25


class SalaryCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    financial_year: str
    assessment_year: str
    regime: str
    resident: bool
    employer_count: int = Field(ge=0)
    salary_paise: int = Field(ge=0, le=MAX_PAISE)
    withholding_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    other_income_categories: tuple[str, ...] = ()
    other_deductions_claimed: bool
    evidence_complete: bool
    identity_period_conflict: bool


def round_statutory_ten(paise: int) -> int:
    """288A/B: discard paise first, then nearest ten rupees, ties upward."""
    from backend.core.money import check_paise
    check_paise(paise)
    if paise < 0:
        raise ValueError("round nonnegative payable/refund separately")
    return ((paise // 100 + 5) // 10) * 1000


def estimate(case: SalaryCase) -> dict:
    p = SALARY_FY2024_25
    reasons = []
    if (case.financial_year, case.assessment_year, case.regime) != (p.financial_year, p.assessment_year, p.regime):
        reasons.append("Only FY2024-25 / AY2025-26 new regime supported")
    if not case.resident or case.employer_count != 1:
        reasons.append("Only one-employer resident salary case supported")
    if case.salary_paise > 500000000:
        reasons.append("Income above INR50 lakh excluded; surcharge unsupported")
    if case.other_income_categories or case.other_deductions_claimed:
        reasons.append("Other income, exemptions and deductions unsupported")
    if not case.evidence_complete or case.identity_period_conflict:
        reasons.append("Resolve evidence coverage, identity and period conflicts")
    envelope = {"rule_version": p.version, "financial_year": p.financial_year,
                "assessment_year": p.assessment_year, "sources": list(p.sources),
                "production_approved": False, "filing_enabled": False}
    if reasons:
        return {**envelope, "status": "unsupported", "reasons": reasons, "tax_paise": None}
    deduction = min(case.salary_paise, p.standard_deduction_paise)
    taxable = round_statutory_ten(case.salary_paise - deduction)
    lower = 0
    breakdown = []
    for upper, rate in p.slabs:
        portion = max(0, min(taxable, upper) - lower)
        breakdown.append({"taxable_paise": portion, "rate_bps": rate, "tax_paise": portion * rate // 10000})
        lower = upper
    gross_tax = sum(b["tax_paise"] for b in breakdown)
    rebate = min(gross_tax, p.rebate_maximum_paise) if taxable <= p.rebate_threshold_paise else 0
    relief = max(0, gross_tax - (taxable - p.rebate_threshold_paise)) if taxable > p.rebate_threshold_paise else 0
    after_relief = gross_tax - rebate - relief
    cess = after_relief * p.cess_bps // 10000
    unrounded = after_relief + cess
    balance = None if case.withholding_paise is None else unrounded - case.withholding_paise
    return {**envelope, "status": "sandbox_estimate", "standard_deduction_paise": deduction,
            "taxable_paise": taxable, "slabs": breakdown, "gross_tax_paise": gross_tax,
            "rebate_paise": rebate, "marginal_relief_paise": relief, "cess_paise": cess,
            "tax_paise": round_statutory_ten(unrounded),
            "balance_payable_paise": None if balance is None else round_statutory_ten(max(0, balance)),
            "refund_paise": None if balance is None else round_statutory_ten(max(0, -balance)),
            "missing_inputs": ["withholding"] if balance is None else [],
            "excluded": ["interest", "late fees", "filing", "statutory certification"]}
