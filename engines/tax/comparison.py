"""Fixed synthetic old/new sample packs. Never statutory parameters."""
from pathlib import Path
from engines.tax.sample_packs import load_pack
from engines.tax.sample_packs import SampleCase, calculate, pack_digest

ROOT = Path(__file__).resolve().parents[2] / 'knowledge_base' / 'tax'
# Fixed release pins; loading a missing/corrupt pack must not break app startup.
# Manifest is a review artifact, never an authority supplied by a request.
PINNED = {
    'old': 'ba0d467c7ba859d9a57c795f94774fae8f83b9fec6f876397b584541fcb43145',
    'new': '40a91750e59093912313873515db423511b40b5d0866bbf78dcbc495a9bd3e92',
}


def packs():
    return {regime: load_pack(ROOT / f'sample-{regime}-h1.json', expected_sha256=digest)
            for regime, digest in PINNED.items()}


LABEL = 'DRAFT / EDUCATIONAL SAMPLE — sample, unreviewed by tax professional'


def compare(inputs, review, *, revision, as_of, pair=None):
    """Exact sample comparison; all blockers produce no draft amounts."""
    envelope = {'label': LABEL, 'financial_year': inputs.financial_year,
        'assessment_year': inputs.assessment_year, 'production_approved': False,
        'filing_enabled': False, 'synthetic_only': True, 'regimes': None}
    unsupported = []
    if (inputs.financial_year, inputs.assessment_year) != ('2024-25', '2025-26'):
        unsupported.append('unsupported_period')
    if not inputs.individual or not inputs.resident or inputs.employer_count != 1:
        unsupported.append('only_individual_resident_single_employer')
    if inputs.other_income or inputs.deductions_claimed:
        unsupported.append('unsupported_income_or_deductions')
    if unsupported:
        return {**envelope, 'status': 'unsupported', 'reasons': unsupported}
    if (not review or review['case_revision'] != revision or not review['confirmed']
            or review['status'] != 'reconciled'):
        return {**envelope, 'status': 'needs_review', 'reasons': ['confirm_current_conflict_free_evidence']}
    pair = packs() if pair is None else pair
    regimes = {}
    for regime, pack in pair.items():
        case = SampleCase(period=pack.period, regime=pack.regime, resident=True, employer_count=1,
            salary_paise=review['fields']['salary_paise'], withholding_paise=review['fields']['withholding_paise'],
            evidence_complete=True, input_revision=revision)
        regimes[regime] = calculate(case, pack, as_of=as_of)
    failures = [r for r in regimes.values() if r['status'] != 'synthetic_sample']
    if failures:
        return {**envelope, 'status': 'unsupported' if any(r['status'] == 'unsupported' for r in failures)
            else 'needs_review', 'reasons': [reason for r in failures for reason in r['reasons']]}
    return {**envelope, 'status': 'sample_draft', 'reasons': [], 'regimes': regimes,
        'pack_vector': {k: pack_digest(p) for k, p in pair.items()},
        'pack_file_sha256': dict(PINNED),
        'pack_snapshots': {k: p.model_dump(mode='json') for k, p in pair.items()},
        'as_of': as_of.isoformat(), 'case_revision': revision,
        'evidence': review['evidence'], 'difference_old_minus_new_paise':
            regimes['old']['tax_paise'] - regimes['new']['tax_paise']}
