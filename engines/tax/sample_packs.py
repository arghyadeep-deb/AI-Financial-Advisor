"""Synthetic calculation harness. Contains no statutory tax rules or advice.

The archived salary engine is separate and remains unapproved. This harness
cannot load a real/approved pack, infer a period or perform filing.
"""
from datetime import date
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.core.money import MAX_PAISE, check_paise


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra='forbid')


class Slab(Contract):
    upper_paise: int = Field(ge=1, le=MAX_PAISE)
    rate_bps: int = Field(ge=0, le=10000)


class SamplePack(Contract):
    version: str = Field(pattern=r'^sample\.[a-z0-9.-]+$')
    synthetic_only: Literal[True]
    production_approved: Literal[False]
    period: str = Field(pattern=r'^SAMPLE-[0-9]{4}$')
    regime: Literal['sample']
    effective: date
    expires: date
    reviewed_on: date
    owner: str = Field(min_length=1, max_length=80)
    source: Literal['invented-test-parameters; not legislation']
    currency: Literal['INR']
    standard_deduction_paise: int = Field(ge=0, le=MAX_PAISE)
    supplement_bps: int = Field(ge=0, le=10000)
    rounding: Literal['aggregate-half-up-paise']
    slabs: tuple[Slab, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def dates_and_bounds(self):
        if not self.reviewed_on <= self.effective < self.expires:
            raise ValueError('Invalid sample pack dates')
        bounds = [s.upper_paise for s in self.slabs]
        if bounds != sorted(set(bounds)):
            raise ValueError('Sample slab bounds must strictly increase')
        return self


class SampleCase(Contract):
    period: str
    regime: str
    resident: bool
    employer_count: int = Field(ge=0, le=100)
    salary_paise: int = Field(ge=0, le=MAX_PAISE)
    withholding_paise: int | None = Field(default=None, ge=0, le=MAX_PAISE)
    other_income: tuple[str, ...] = ()
    deductions_claimed: bool = False
    evidence_complete: bool = False
    conflicts: tuple[Literal['identity', 'period', 'income', 'withholding'], ...] = ()
    input_revision: int = Field(ge=1)


def load_pack(path: Path, *, expected_sha256: str) -> SamplePack:
    """Operator/test file only; no request can select an arbitrary path."""
    raw = path.read_bytes()
    if len(raw) > 32000 or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Sample pack size/hash mismatch')
    return SamplePack.model_validate_json(raw)


def pack_digest(pack: SamplePack):
    return sha256(pack.model_dump_json().encode()).hexdigest()


def _round(value):
    quotient, remainder = divmod(value.numerator, value.denominator)
    return check_paise(quotient + int(remainder * 2 >= value.denominator))


def calculate(case: SampleCase, pack: SamplePack, *, as_of: date) -> dict:
    envelope = {'label': 'SYNTHETIC SAMPLE — not a tax draft or advice', 'synthetic_only': True,
        'production_approved': False, 'filing_enabled': False, 'rule_version': pack.version,
        'pack_digest': pack_digest(pack), 'pack_effective': pack.effective.isoformat(),
        'pack_expires': pack.expires.isoformat(), 'source': pack.source, 'period': case.period,
        'input_revision': case.input_revision, 'input_digest': sha256(case.model_dump_json().encode()).hexdigest(),
        'as_of': as_of.isoformat(), 'tax_paise': None}
    unsupported = []
    if (case.period, case.regime) != (pack.period, pack.regime):
        unsupported.append('Select the exact sample period and regime; no adjacent-period substitution.')
    if not case.resident or case.employer_count != 1 or case.other_income or case.deductions_claimed:
        unsupported.append('Only the fictional single-employer resident salary sample is supported.')
    if max(0, case.salary_paise - pack.standard_deduction_paise) > pack.slabs[-1].upper_paise:
        unsupported.append('Income exceeds the sample slab scope.')
    if unsupported:
        return {**envelope, 'status': 'unsupported', 'reasons': unsupported}
    review = list(case.conflicts)
    if not case.evidence_complete:
        review.append('evidence_incomplete')
    if not pack.effective <= as_of < pack.expires:
        review.append('sample_pack_not_current')
    if review:
        return {**envelope, 'status': 'needs_review', 'reasons': review}
    taxable = max(0, case.salary_paise - pack.standard_deduction_paise)
    lower, exact_tax, breakdown = 0, Fraction(0), []
    for slab in pack.slabs:
        portion = max(0, min(taxable, slab.upper_paise) - lower)
        exact = Fraction(portion * slab.rate_bps, 10000)
        exact_tax += exact
        breakdown.append({'taxable_paise': portion, 'rate_bps': slab.rate_bps,
                          'exact_tax_fraction_paise': str(exact)})
        lower = slab.upper_paise
    supplement = exact_tax * Fraction(pack.supplement_bps, 10000)
    total = _round(exact_tax + supplement)
    balance = None if case.withholding_paise is None else total - case.withholding_paise
    return {**envelope, 'status': 'synthetic_sample', 'reasons': [], 'taxable_paise': taxable,
        'slabs': breakdown, 'base_tax_paise': _round(exact_tax), 'supplement_paise': _round(supplement),
        'tax_paise': total, 'balance_payable_paise': None if balance is None else max(0, balance),
        'refund_paise': None if balance is None else max(0, -balance),
        'missing_inputs': ['withholding'] if balance is None else [],
        'excluded': ['statutory rules', 'rebates', 'marginal relief', 'surcharge', 'interest', 'filing', 'advice']}


def stale(result: dict, case: SampleCase, pack: SamplePack, *, as_of: date):
    return (result['pack_digest'] != pack_digest(pack) or
            result['input_digest'] != sha256(case.model_dump_json().encode()).hexdigest() or
            not pack.effective <= as_of < pack.expires)
