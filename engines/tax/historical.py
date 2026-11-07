"""Historical salary rules; integer paise / rational intermediate arithmetic only."""
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from backend.core.money import check_paise

ROOT = Path(__file__).resolve().parents[2] / 'knowledge_base/tax'
# Release pins use LF bytes, irrespective of the host checkout convention.
PINNED = {'old': 'dd7fc0fb78de0e9747282380102a0311834674704c73991f2614a22ff07145e1', 'new': '88f10b97af7c08662ff58a043f27a925c5375b585e1e1492a3f19ff924b33842'}  # filled with the released data-file digests below

class HistoricalPack(BaseModel):
    model_config = ConfigDict(extra='allow', frozen=True)
    version: str
    regime: str
    financial_year: str
    assessment_year: str
    historical: bool
    production_approved: bool
    standard_deduction_paise: int
    slabs_by_age: dict
    rebate: dict
    surcharge: list
    cess_bps: int
    deduction_caps_paise: dict
    rounding: dict


def packs():
    result = {}
    for regime, digest in PINNED.items():
        raw = (ROOT / f'ay2025-26-{regime}-h2.json').read_bytes().replace(b'\r\n', b'\n')
        if len(raw) > 32000 or sha256(raw).hexdigest() != digest:
            raise ValueError('Historical pack hash mismatch')
        result[regime] = HistoricalPack.model_validate_json(raw)
    return result


def pack_digest(pack):
    return sha256(pack.model_dump_json().encode()).hexdigest()


def round_ten(value):
    """ss.288A/288B v1: drop fractional INR, round INR to nearest ten, ties up.

    Unverified against Act text. Applied only at named statutory boundaries.
    Input and output are paise, intermediate input may be a Fraction.
    """
    return (int(value // 100) + 5) // 10 * 1000


def slab_tax(income, pack, age):
    band = 'all' if pack.regime == 'new' else 'super_senior' if age >= 80 else 'senior' if age >= 60 else 'adult'
    lower, total, rows = 0, Fraction(0), []
    for upper, rate in pack.slabs_by_age[band]:
        amount = max(0, min(income, upper if upper is not None else income) - lower)
        tax = Fraction(amount * rate, 10000)
        total += tax
        rows.append(dict(taxable_paise=amount, rate_bps=rate, exact_tax_fraction_paise=str(tax)))
        if upper is not None:
            lower = upper
    return total, rows


def post_rebate(income, base, pack):
    rule = pack.rebate
    if income <= rule['threshold_paise']:
        return max(Fraction(0), base - rule['cap_paise'])
    if rule['marginal_relief']:
        return min(base, Fraction(income - rule['threshold_paise']))
    return base


def tax_and_surcharge(income, pack, age):
    base, _ = slab_tax(income, pack, age)
    after = post_rebate(income, base, pack)
    applicable = [(threshold, rate) for threshold, rate in pack.surcharge if income > threshold]
    nominal = after * (1 + Fraction(applicable[-1][1], 10000)) if applicable else after
    # Recursing only to a strictly smaller threshold also handles overlapping relief.
    if applicable:
        threshold = applicable[-1][0]
        ceiling = tax_and_surcharge(threshold, pack, age)[0] + income - threshold
        relieved = min(nominal, ceiling)
    else:
        relieved = nominal
    return relieved, after, nominal


def calculate(inputs, fields, pack):
    reasons = []
    claims = inputs.deductions_paise
    known = {'80C', '80CCD(1B)', '80D_self', '80D_parents', '80D_preventive_self', '80D_preventive_parents'}
    if inputs.deductions_claimed and not claims:
        reasons.append('unlisted_deductions')
    if set(claims) - known:
        reasons.append('unsupported_deduction')
    if set(inputs.allowances_paise) - {'taxable_allowances'}:
        reasons.append('unsupported_allowance_or_exemption')
    if pack.regime == 'new' and any(claims.values()):
        reasons.append('chapter_VIA_claim_ineligible_new_regime')
    envelope = dict(rule_version=pack.version, historical=True, financial_year=pack.financial_year,
                    assessment_year=pack.assessment_year, tax_paise=None, rounding=pack.rounding)
    if reasons:
        return dict(envelope, status='unsupported', reasons=reasons)
    gross = check_paise(fields['salary_paise'] + sum(inputs.allowances_paise.values()))
    standard = min(gross, pack.standard_deduction_paise)
    deductions = {}
    if pack.regime == 'old':
        caps = pack.deduction_caps_paise
        deductions['80C'] = min(claims.get('80C', 0), caps['80C'])
        deductions['80CCD(1B)'] = min(claims.get('80CCD(1B)', 0), caps['80CCD(1B)'])
        # Preventive checkups have one combined INR 5,000 sublimit, within 80D.
        remaining = caps['80D_preventive_within_80D']
        for group, senior in [('self', inputs.age_at_year_end >= 60 or inputs.senior_self_or_spouse), ('parents', inputs.senior_parent)]:
            preventive = min(claims.get('80D_preventive_' + group, 0), remaining)
            remaining -= preventive
            cap = caps['80D_' + group + ('_senior' if senior else '')]
            deductions['80D_' + group] = min(claims.get('80D_' + group, 0) + preventive, cap)
    allowed = min(gross - standard, sum(deductions.values()))
    taxable_before_rounding = gross - standard - allowed
    taxable = round_ten(taxable_before_rounding)
    base, slabs = slab_tax(taxable, pack, inputs.age_at_year_end)
    combined, after, nominal = tax_and_surcharge(taxable, pack, inputs.age_at_year_end)
    cess = combined * Fraction(pack.cess_bps, 10000)
    exact_total = combined + cess
    total = round_ten(exact_total)
    # Withholding is a declared total only; credit eligibility is not certified.
    balance = total - fields['withholding_paise']
    return dict(envelope, status='historical_draft', reasons=[], gross_salary_paise=gross,
        standard_deduction_paise=standard, deductions_paise=deductions,
        chapter_VIA_allowed_paise=allowed, taxable_before_rounding_paise=taxable_before_rounding,
        taxable_paise=taxable, slabs=slabs, base_tax_exact_paise=str(base),
        rebate_including_marginal_relief_exact_paise=str(base-after),
        surcharge_before_relief_exact_paise=str(nominal-after),
        surcharge_marginal_relief_exact_paise=str(nominal-combined),
        tax_and_surcharge_exact_paise=str(combined), cess_exact_paise=str(cess),
        tax_before_rounding_exact_paise=str(exact_total), tax_paise=total,
        withholding_paise=fields['withholding_paise'],
        balance_payable_paise=round_ten(max(0, balance)), refund_paise=round_ten(max(0, -balance)),
        assumptions=['Owner-declared manual salary and taxable allowances; no perquisites or arrears.',
                     '80C includes aggregate 80CCC/80CCD(1); preventive 80D sublimit allocated self then parents.',
                     'Withholding total only, credit eligibility not verified.',
                     'Rounding ss.288A/288B unverified_against_act_text.'])
