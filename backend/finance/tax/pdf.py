"""Deterministic, dependency-free PDF 1.4 review draft.

Fixed Courier font and bounded, wrapped ASCII text. No HTML, scripts, attachments,
network, paths, current timestamp or random document IDs enter this renderer.
Amounts come only from the persisted immutable draft (never recalculated here).
"""
from fractions import Fraction
from textwrap import wrap
import json


def money(value):
    if value is None:
        return 'unavailable'
    amount = Fraction(value) / 100
    if amount.denominator == 1:
        return f'INR {amount.numerator:,}'
    # Exact rational display prevents introducing a second rounding policy.
    return f'INR {amount}'


def lines_for(draft):
    data = draft['data']
    lines = [
        'HISTORICAL TAX REVIEW DRAFT', 'FY2024-25 / AY2025-26 - historical, not current-year coverage',
        'Draft, not filed, not reviewed by a tax professional',
        'Independent tax review: PENDING. Public-release readiness: PENDING.',
        'STALE: ' + ('YES - ' + ', '.join(draft['stale_reasons']) if draft['stale'] else 'NO'),
        'Draft ID: ' + draft['id'], 'Calculation date: ' + data['as_of'],
        'Case revision: ' + str(data['case_revision']), '',
        'INPUTS AND EVIDENCE (manual declarations; not verified documents)',
    ]
    for field, evidence in sorted(data['evidence'].items()):
        value = money(evidence['value']) if field in {'income', 'withholding'} else str(evidence['value'])
        lines.append(f"{field}: {value}; source {evidence['source_id']}; field {evidence['field']}")
        if evidence.get('resolution'):
            lines.append('Review explanation: ' + evidence['resolution']['explanation'])
    lines.append('Manual claims: ' + json.dumps(data.get('manual_claim_evidence', {}), sort_keys=True))
    lines += ['', 'BOTH REGIMES - STEP BY STEP']
    names = [
        ('gross_salary_paise','1. Gross salary plus taxable allowances'),
        ('standard_deduction_paise','2. Standard deduction (capped at salary)'),
        ('chapter_VIA_allowed_paise','3. Chapter VI-A allowed (capped at income)'),
        ('taxable_before_rounding_paise','4. Taxable income before s.288A rounding'),
        ('taxable_paise','5. Taxable income after s.288A rounding'),
        ('base_tax_exact_paise','6. Slab income tax'),
        ('rebate_including_marginal_relief_exact_paise','7. s.87A rebate including marginal relief'),
        ('surcharge_before_relief_exact_paise','8. Surcharge before marginal relief'),
        ('surcharge_marginal_relief_exact_paise','9. Surcharge marginal relief'),
        ('tax_and_surcharge_exact_paise','10. Tax and surcharge after relief'),
        ('cess_exact_paise','11. Health and education cess (4%)'),
        ('tax_before_rounding_exact_paise','12. Tax before s.288B rounding'),
        ('tax_paise','13. Tax after s.288B rounding'),
        ('withholding_paise','14. Declared withholding total (credit not certified)'),
        ('balance_payable_paise','15. Draft balance payable (rounded)'),
        ('refund_paise','16. Draft refund (rounded)'),
    ]
    for regime, result in sorted(data['regimes'].items()):
        lines += ['', regime.upper() + ' REGIME: ' + result['status']]
        if result['status'] != 'historical_draft':
            lines += ['UNSUPPORTED / INELIGIBLE: ' + ', '.join(result['reasons'])]
        else:
            lines += [label + ': ' + money(result[key]) for key,label in names]
            for slab in result['slabs']:
                lines.append(f"  Slab portion {money(slab['taxable_paise'])} at {slab['rate_bps']/100:g}%: {money(slab['exact_tax_fraction_paise'])}")
            lines.append('Allowed deduction groups (paise): ' + json.dumps(result['deductions_paise'],sort_keys=True))
            lines += ['Assumption: ' + a for a in result['assumptions']]
        pack = data['pack_snapshots'][regime]
        lines += ['Rule pack id/version: ' + pack['version'],
                  'Rule pack file SHA256 (LF bytes): ' + data['pack_file_sha256'][regime],
                  'Snapshot digest: ' + data['pack_vector'][regime],
                  'Transcription date: ' + pack['transcribed_on'],
                  'Rounding: ss.288A/288B v1; unverified_against_act_text']
        for source in pack['sources']:
            lines.append(source['id'] + ': ' + source['url'])
    difference = data.get('difference_old_minus_new_paise')
    lines += ['', 'Old minus new tax: ' + money(difference),
              'No regime comparison is available when a regime is unsupported.' if difference is None else 'Positive difference means the new-regime draft has lower tax.',
              'Form16 / AIS / 26AS parsing: PENDING, not implemented.',
              'Salary only; one adult resident individual, one employer.',
              'No filing / e-filing / statutory certification / external services.',
              'Retain evidence and obtain independent professional review before use.']
    out=[]
    for line in lines:
        clean = ''.join(c if 32 <= ord(c) <= 126 else '?' for c in line)
        out.extend(wrap(clean, width=88, replace_whitespace=False) or [''])
    return out


def render(draft):
    """A4 pages, 10pt Courier (6pt/character), 88 columns within 499pt width."""
    lines = lines_for(draft)
    pages = [lines[i:i+54] for i in range(0,len(lines),54)]
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>']
    page_ids=[]
    def literal(line):
        return line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    for index, content in enumerate(pages):
        pid=len(objects)+1; page_ids.append(pid)
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {pid+1} 0 R >>'.encode())
        text=['BT /F1 9 Tf 13 TL 40 792 Td']
        text += ['('+literal(line)+') Tj T*' for line in content]
        text += ['ET', f'BT /F1 8 Tf 40 30 Td (HISTORICAL DRAFT - not filed - Page {index+1} of {len(pages)}) Tj ET']
        stream='\n'.join(text).encode('ascii')
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    objects[1]=f"<< /Type /Pages /Count {len(page_ids)} /Kids [{' '.join(str(p)+' 0 R' for p in page_ids)}] >>".encode()
    result=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'); offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(result)); result.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref=len(result)
    result.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]: result.extend(f'{offset:010} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)
