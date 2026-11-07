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
