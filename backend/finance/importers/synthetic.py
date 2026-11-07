"""Strict synthetic CSV/text parser. Descriptions never execute or reach a model."""
import csv
import io
import re
from datetime import date
from backend.core.money import rupees_to_paise, check_paise
from backend.finance.importers.registry import CATEGORIES, CREDIT, DEBIT


class ParseError(ValueError):
    pass


def iso(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ParseError('invalid_date')
    return date.fromisoformat(value)


def parse(content, max_rows, max_bytes):
    if len(content) > max_bytes:
        raise ParseError('file_too_large')
    if content.startswith(b'%PDF'):
        raise ParseError('unsupported_pdf')
    # This scanner is deliberately restricted to synthetic UTF-8 text, not an AV claim.
    if b'EICAR' in content or any(b < 32 and b not in (9, 10, 13) for b in content):
        raise ParseError('quarantined_scan')
    try:
        reader = csv.reader(io.StringIO(content.decode('utf-8')), strict=True)
        head = next(reader)
        if len(head) != 6 or head[0] != 'SYNTHETIC-INR-v1' or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', head[1]):
            raise ParseError('unsupported_format')
        start, end = iso(head[2]), iso(head[3])
        if start > end or end > date.today():
            raise ParseError('invalid_period')
        opening = None if head[4] == '' else rupees_to_paise(head[4], allow_negative=True)
        closing = None if head[5] == '' else rupees_to_paise(head[5], allow_negative=True)
        if (opening is None) != (closing is None):
            raise ParseError('missing_balance')
        if next(reader) != ['date', 'description', 'reference', 'signed_rupees', 'category']:
            raise ParseError('unsupported_columns')
        rows, references = [], set()
        total = 0
        for ordinal, fields in enumerate(reader, 3):
            if len(rows) >= max_rows:
                raise ParseError('row_limit')
            if len(fields) != 5:
                raise ParseError('invalid_row')
            posting, description, reference, amount, category = fields
            if not start <= iso(posting) <= end:
                raise ParseError('out_of_period')
            value = rupees_to_paise(amount, allow_negative=True)
            if not value or category not in CATEGORIES or not 1 <= len(description) <= 200 or len(reference) > 80:
                raise ParseError('invalid_row')
            if (category in CREDIT and value < 0) or (category in DEBIT and value > 0):
                raise ParseError('invalid_direction')
            if reference and reference in references:
                raise ParseError('duplicate_reference')
            if reference:
                references.add(reference)
            total = check_paise(total + value)
            rows.append({'ordinal': ordinal, 'posting_date': posting, 'description': description,
                'reference': reference or None, 'amount_paise': value, 'category': category})
        if not rows:
            raise ParseError('empty_statement')
        difference = check_paise(opening + total - closing) if opening is not None else None
        from backend.finance.importers.registry import PARSER_VERSION
        return {'parser_version': PARSER_VERSION, 'account_token': head[1], 'start_date': start.isoformat(), 'end_date': end.isoformat(),
            'opening_paise': opening, 'closing_paise': closing, 'difference_paise': difference, 'rows': rows}
    except (UnicodeError, csv.Error, StopIteration, ValueError) as exc:
        if isinstance(exc, ParseError):
            raise
        raise ParseError('invalid_statement') from exc
