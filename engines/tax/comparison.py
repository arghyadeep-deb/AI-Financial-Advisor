"""Pinned HISTORICAL FY2024-25 / AY2025-26 salary comparison; no filing."""
from engines.tax.historical import packs, pack_digest, calculate, PINNED

LABEL = 'HISTORICAL FY2024-25 / AY2025-26 - DRAFT, not filed, not reviewed by a tax professional'


def compare(inputs, review, *, revision, as_of, pair=None):
    envelope = dict(label=LABEL, financial_year=inputs.financial_year,
        assessment_year=inputs.assessment_year, historical=True, production_approved=False,
        filing_enabled=False, regimes=None, document_parsing='PENDING: Form16/AIS/26AS not implemented',
        independent_tax_review='PENDING', public_release_readiness='PENDING')
    unsupported = []
    if (inputs.financial_year, inputs.assessment_year) != ('2024-25', '2025-26'):
        unsupported.append('unsupported_period')
    if not inputs.individual or not inputs.resident or inputs.employer_count != 1:
        unsupported.append('only_individual_resident_single_employer')
    if inputs.age_at_year_end is None or inputs.age_at_year_end < 18:
        unsupported.append('adult_age_required')
    if inputs.other_income:
        unsupported.append('unsupported_income')
    if unsupported:
        return dict(envelope, status='unsupported', reasons=unsupported)
    if (not review or review['case_revision'] != revision or not review['confirmed']
            or review['status'] != 'reconciled'):
        return dict(envelope, status='needs_review', reasons=['confirm_current_conflict_free_evidence'])
    pair = packs() if pair is None else pair
    regimes = {k: calculate(inputs, review['fields'], p) for k, p in pair.items()}
    valid = [r for r in regimes.values() if r['status'] == 'historical_draft']
    if not valid:
        return dict(envelope, status='unsupported', regimes=regimes,
                    reasons=sorted({reason for r in regimes.values() for reason in r['reasons']}))
    return {**envelope, 'status': 'historical_draft', 'reasons': [], 'regimes': regimes,
        'pack_vector': {k: pack_digest(p) for k, p in pair.items()},
        'pack_file_sha256': dict(PINNED), 'pack_snapshots': {k:p.model_dump(mode='json') for k,p in pair.items()},
        'as_of': as_of.isoformat(), 'case_revision': revision, 'evidence': review['evidence'],
        'manual_claim_evidence': {name:getattr(inputs,name) for name in
            ('age_at_year_end','allowances_paise','deductions_paise','senior_self_or_spouse','senior_parent')},
        'difference_old_minus_new_paise': regimes['old']['tax_paise'] - regimes['new']['tax_paise']
            if len(valid) == 2 else None}
