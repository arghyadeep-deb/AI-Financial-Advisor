# Stage H synthetic scope (D04 awaiting owner approval)

One individual resident, one employer, salary only, FY2024-25 / AY2025-26.
Old and new **sample** regimes are compared side by side. All parameters are
invented test parameters: **sample, unreviewed by tax professional**. This is
not a statutory FY2024-25 calculator. No official-reference accuracy claimed.
The archived salary engine is not used by this workflow.

Only `synthetic-salary-v1` structured fields are supported: fictional identity
reference, explicit financial year, salary and optional withholding in integer
paise. No PAN or original document is accepted. Form16, AIS, 26AS, Form168,
PDF, OCR, bank statements, multiple employers, nonresident/nonindividual,
other income (including business, gains, foreign), deductions/exemptions,
interest, late fees, surcharge and filing are unsupported. Actual statutory
sources/forms and independent tax-professional review remain release blockers.

Disagreement in identity, period, income or withholding blocks computation.
Review chooses a retained source field with an explanation; original sources
remain immutable. Missing withholding blocks a draft. Corrections create a new
case revision and require a fresh review. Never infer salary from bank cash flow
or FinanceSnapshot; these have no complete taxable-income contract.

Sample packs extend lane E's exact Fraction arithmetic and half-up aggregate
paise rounding. Each pack has effective/expiry dates, version and pinned file
SHA256. Period labels never substitute adjacent years. Packs are loaded only
from fixed repository paths. A changed/missing/expired pack or new case/review
revision makes historical drafts stale. No annual auto-refresh or real rates.

Sandbox writes require TAX_SANDBOX_ENABLED and test/development environment;
default false and always denied in production. Authenticated historical reads
remain available with current stale state even when writes are disabled.
No filing, LLM, external integration, certification or official acknowledgment.

## Backend contract for orchestrator

All routes use the existing bearer session and owner-scoped queries; foreign and
missing resources share `404 Tax resource not found.`. Writes use the shared
owner lock, immutable revision store and analysis daily quota (no duplicate
throttle service); export uses the shared exports daily quota. No provider cost.

- `POST /tax/cases`: CaseWrite with Operation fields and `data: TaxInputs`.
- `POST /tax/cases/{case_id}/revisions`: same shape, expected current case revision.
- `GET /tax/cases/{case_id}?revision=N`: latest or retained historical input.
- `POST /tax/cases/{case_id}/reviews`: Operation plus `confirmed: bool` and
  optional `resolutions: [{field, source_id, explanation}]`. Fields are identity,
  period, income, withholding. `expected_revision` means **case** revision.
  Returns immutable review with independent monotonically increasing revision.
- `GET /tax/reviews/{id}`: retained original review/selected field evidence.
- `POST /tax/cases/{case_id}/drafts`: Operation, expected **case** revision;
  server resolves latest review and fixed packs while holding owner lock.
  Unsupported/unresolved inputs return status/reasons and `persisted:false`;
  no draft row or amounts are published. Success returns an immutable sample
  draft with its own revision. Review corrections also invalidate earlier drafts.
- `GET /tax/drafts/{id}`: immutable snapshot plus dynamically evaluated
  `stale`/`stale_reasons`.
- `GET /tax/drafts/{id}/export`: JSON attachment, no-store, DRAFT label, snapshot
  SHA256, input/review/pack snapshots and current stale state. SHA256 covers the
  canonical JSON `data` only (UTF-8, sorted keys, separators comma/colon,
  ensure_ascii=False), so historical reproduction survives stale-state changes.

All Operation bodies require `expected_revision`, `idempotency_key` and `reason`.
Same key/exact request replays; changed request returns 409. A fresh correction
uses a new key. Replaying a draft returns its original snapshot and current stale
state. Schema rejects unknown fields, coercible/bool money, negative/overflow
amounts and unsupported layouts. No client-selected file path, rules or rates.
Source/review explanation text is never evaluated or sent to a model.

## Recovery

Only migration 0150, parent 0141. Stop writes/disable sandbox before operator
recovery. Use shared migrations_runner with verified backup. Empty downgrade
drops the table/trigger; populated downgrade refuses data loss. Forward-fix or
separately authorized privacy purge/restore is required for populated rollback.
Owner privacy export/purge includes all revisions; shared deletion suppression
blocks restored owners. No real database was migrated by this implementation.
PostgreSQL SQL is supplied but this lane tested SQLite only. Production retention
and backup expiry remain shared D03 decisions. Rule refresh requires new pack
files, version, explicit pins and independent fixtures/review; never replace a
pack and call it current statutory law. Pack metadata dates are synthetic fixture
metadata, not a record of tax-professional approval.
