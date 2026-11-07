from backend.core.config import config

FORMAT_ID = 'synthetic-inr-v1'
PARSER_VERSION = 'synthetic.v1'
CATEGORIES = frozenset({'unknown', 'income', 'purchase', 'fee', 'interest', 'loan_principal',
    'borrowing', 'investment', 'disposal', 'withdrawal', 'transfer', 'card_settlement',
    'refund', 'reimbursement', 'unsplit_debt'})
CREDIT = frozenset({'income', 'borrowing', 'disposal', 'refund', 'reimbursement'})
DEBIT = frozenset({'purchase', 'fee', 'interest', 'loan_principal', 'investment', 'unsplit_debt'})


def limits():
    return {'enabled': config.SYNTHETIC_STATEMENTS_ENABLED and not config.is_production_like,
        'synthetic_only': True, 'formats': [FORMAT_ID], 'account_types': ['synthetic_debit'],
        'max_bytes': config.STATEMENT_MAX_BYTES, 'max_rows': config.STATEMENT_MAX_ROWS,
        'max_pages': 0, 'timeout_seconds': config.STATEMENT_TIMEOUT_SECONDS,
        'pdf': 'unsupported', 'ocr': 'disabled', 'scanner': 'synthetic_text_allowlist',
        'source_retention_days': config.SOURCE_RETENTION_DAYS, 'categories': sorted(CATEGORIES)}


ERROR_MESSAGES = {
    'unsupported_pdf': 'PDF statements are not supported yet. Export a CSV from your bank instead.',
    'unsupported_scanned_or_image': 'Scanned documents and photos are not supported yet. Export a CSV from your bank instead. Nothing was sent to any outside service.',
    'quarantined_scan': 'The file was held back because it failed the safety check.',
    'file_too_large': 'The file is larger than the allowed size.',
    'row_limit': 'The file has more rows than the allowed maximum.',
    'unsupported_format': 'This file is not in a supported layout. Use the column mapping option for a CSV.',
    'balance_mismatch': 'Opening balance plus the rows does not equal the closing balance. Review before accepting.',
    'unverified_balance': 'No balances were provided, so totals could not be checked. Review before accepting.',
    'account_mismatch': 'The file belongs to a different account.',
}
