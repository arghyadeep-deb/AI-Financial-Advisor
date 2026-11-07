"""User-mapped CSV import. The user says which column is which; nothing is guessed.

Pure functions, no I/O. Output is converted to the canonical synthetic text so the existing sandboxed parser,
reconciliation and review path stay the single route into the ledger. No real bank layout is encoded here.
"""
import csv
import io
import re
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from backend.core.money import rupees_to_paise, check_paise, MoneyError

AMOUNT = re.compile(r'^-?(\d+|\d{1,3}(,\d{2,3})+)(\.\d{1,2})?$')   # plain or Indian/Western grouping, max 2 decimals
FORMULA_LEAD = ('=', '+', '-', '@', '\t', '\r')
MAGIC = (b'%PDF', b'\x89PNG', b'\xff\xd8\xff', b'GIF8', b'II*\x00', b'MM\x00*', b'BM', b'RIFF')


class MappingError(ValueError):
    pass


class Mapping(BaseModel):
    model_config = ConfigDict(extra='forbid')
    delimiter: Literal[',', ';', '\t'] = ','
    has_header: bool = True
    date_column: StrictInt = Field(ge=0, le=50)
    date_format: Literal['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']   # explicit; never guessed
    description_column: StrictInt = Field(ge=0, le=50)
    reference_column: StrictInt | None = Field(default=None, ge=0, le=50)
    amount_mode: Literal['signed', 'debit_credit']
    amount_column: StrictInt | None = Field(default=None, ge=0, le=50)
    debit_column: StrictInt | None = Field(default=None, ge=0, le=50)
    credit_column: StrictInt | None = Field(default=None, ge=0, le=50)

    @model_validator(mode='after')
    def consistent(self):
        if self.amount_mode == 'signed' and (self.amount_column is None or self.debit_column is not None
                                             or self.credit_column is not None):
            raise ValueError('signed mode needs exactly an amount column')
        if self.amount_mode == 'debit_credit' and (self.amount_column is not None or self.debit_column is None
                                                    or self.credit_column is None or self.debit_column == self.credit_column):
            raise ValueError('debit_credit mode needs distinct debit and credit columns')
        return self


def reject_binary(content):
    if any(content.startswith(m) for m in MAGIC):
        raise MappingError('unsupported_scanned_or_image')
    if b'EICAR' in content or any(b < 32 and b not in (9, 10, 13) for b in content):
        raise MappingError('quarantined_scan')


def safe_text(value):
    value = ''.join(ch for ch in value.strip() if ch >= ' ' or ch == '\t').replace('\t', ' ')
    return ("'" + value) if value.startswith(FORMULA_LEAD) else value


def _cell(fields, index):
    return fields[index].strip() if index is not None and index < len(fields) else None


def _money(text, *, negate=False):
    if not text or not AMOUNT.match(text):
        raise MappingError('invalid_amount')
    try:
        value = check_paise(rupees_to_paise(text, allow_negative=True))
    except MoneyError as exc:
        raise MappingError('invalid_amount') from exc
    return -value if negate else value


def preview(content, mapping, *, max_rows, max_bytes, sample=20):
    """Validate every row; return a bounded sample plus all problems. `ok` only when nothing is wrong."""
    if len(content) > max_bytes:
        raise MappingError('file_too_large')
    reject_binary(content)
    try:
        text = content.decode('utf-8-sig')
    except UnicodeError as exc:
        raise MappingError('not_utf8') from exc
    try:
        records = list(csv.reader(io.StringIO(text), delimiter=mapping.delimiter, strict=True))
    except csv.Error as exc:
        raise MappingError('invalid_csv') from exc
    headers = records[0] if records and mapping.has_header else []
    start = 2 if mapping.has_header else 1
    body = records[1:] if mapping.has_header else records
    body = [(n, r) for n, r in enumerate(body, start) if any(c.strip() for c in r)]
    if len(body) > max_rows:
        raise MappingError('row_limit')
    rows, errors, warnings, references, seen = [], [], [], set(), {}
    needed = [i for i in (mapping.date_column, mapping.description_column, mapping.reference_column,
                          mapping.amount_column, mapping.debit_column, mapping.credit_column) if i is not None]
    for line, fields in body:
        if len(fields) <= max(needed):
            errors.append({'line': line, 'code': 'missing_columns'})
            continue
        problems = []
        try:
            posted = datetime.strptime(fields[mapping.date_column].strip(), mapping.date_format).date()
            if posted > date.today():
                problems.append('future_date')
        except ValueError:
            posted = None
            problems.append('invalid_date')
        raw_description = fields[mapping.description_column].strip()
        description = safe_text(raw_description)
        if not 1 <= len(description) <= 200:
            problems.append('invalid_description')
        amount = None
        try:
            if mapping.amount_mode == 'signed':
                amount = _money(_cell(fields, mapping.amount_column))
            else:
                debit, credit = _cell(fields, mapping.debit_column), _cell(fields, mapping.credit_column)
                if bool(debit) == bool(credit):
                    raise MappingError('invalid_amount')
                amount = _money(debit, negate=True) if debit else _money(credit)
            if amount == 0:
                raise MappingError('invalid_amount')
        except MappingError:
            problems.append('invalid_amount')
        reference = (_cell(fields, mapping.reference_column) or '')[:80] or None
        if reference and reference in references:
            problems.append('duplicate_reference')
        if reference:
            references.add(reference)
        if problems:
            errors.extend({'line': line, 'code': p} for p in problems)
            continue
        key = (posted, amount, description)
        if key in seen:
            warnings.append({'line': line, 'code': 'possible_duplicate_of_line', 'other_line': seen[key]})
        seen.setdefault(key, line)
        if raw_description.startswith(FORMULA_LEAD):
            warnings.append({'line': line, 'code': 'formula_like_text_neutralised'})
        rows.append({'line': line, 'posting_date': posted.isoformat(), 'description': description,
                     'reference': reference, 'amount_paise': amount})
    if not rows and not errors:
        errors.append({'line': 0, 'code': 'empty_statement'})
    return {'headers': [h[:80] for h in headers], 'row_count': len(rows), 'rows': rows[:sample], 'all_rows': rows,
            'errors': errors[:200], 'error_count': len(errors), 'warnings': warnings[:200],
            'start_date': min((r['posting_date'] for r in rows), default=None),
            'end_date': max((r['posting_date'] for r in rows), default=None),
            'ok': not errors and bool(rows)}


def to_canonical(account_token, result):
    """Canonical synthetic text: unknown category and no balances, so review and balance checks stay explicit."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['SYNTHETIC-INR-v1', account_token, result['start_date'], result['end_date'], '', ''])
    writer.writerow(['date', 'description', 'reference', 'signed_rupees', 'category'])
    for r in result['all_rows']:
        sign = '-' if r['amount_paise'] < 0 else ''
        paise = abs(r['amount_paise'])
        writer.writerow([r['posting_date'], r['description'], r['reference'] or '',
                         f'{sign}{paise // 100}.{paise % 100:02d}', 'unknown'])
    return out.getvalue().encode('utf-8')
