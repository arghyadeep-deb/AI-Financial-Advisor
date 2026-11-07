# Synthetic statement v1

Fictional INR debit accounts only, no real bank layout or customer data. Not a
released bank or card adapter. CSV and text use the identical UTF-8 CSV grammar.

First line: `SYNTHETIC-INR-v1,account_token,YYYY-MM-DD,YYYY-MM-DD,opening_rupees,closing_rupees`.
Both balances may be empty (unverified); exactly one missing balance is invalid.
Next line must be `date,description,reference,signed_rupees,category`.
Subsequent lines are posted activity: ISO date, description (1..200), optional
account-scoped stable reference (max 80), signed exact rupees, category. Positive
means credit. Never supply an actual bank identifier. Categories are synthetic
user assertions, not inferred salary or bank-confirmed facts; `unknown` is valid.
API `/statement-formats` enumerates categories and runtime limits. Splits use
signed integer paise. Dates outside declared coverage or in the future fail closed.

`supported.csv`: FIN-01 income 4,500,000 paise, spending 5,500,000, shortfall
1,000,000; opening 2,000,000 -> closing 1,000,000. Exact duplicates use these
same bytes in tests (no duplicate fixture copy). `overlap.csv` corroborates both
January entries and adds a February fee. `distinct.csv` proves identical genuine
debits without references remain two entries. `mismatch.csv` has a 100-paise
difference and cannot publish. `unsupported.txt` cannot reach staging.

PDF, scanned/protected inputs, OCR, real bank formats and external scanners are
unsupported/disabled. Text allowlist scanning is solely a synthetic development
control; OS sandboxing and a production scanner remain release requirements.
