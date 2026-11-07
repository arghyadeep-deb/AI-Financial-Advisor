# Stage H tax preparation progress

No commits/pushes; working tree for orchestrator. No frontend changes.
All Python commands use `C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe`.

## Sequential task evidence

- T401 **partial**: `backend/schemas/tax.py`, `engines/tax/comparison.py`,
  `knowledge_base/tax/sample-{old,new}-h1.json`, `stage-h-manifest.json`,
  `docs/tax/stage-h-scope.md`, `tests/tax/test_stage_h.py`.
  Scope/contracts tested before consumers. Command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest
  tests/tax/test_stage_h.py -q -p no:cacheprovider -W ignore`: first **1 passed**,
  then **2 passed**. Official-reference examples and professional validation absent.
  D04 assumption awaiting approval: FY2024-25/AY2025-26 single-employer individual
  resident salary only, both old/new *invented sample* packs. No statutory claim.
  No migration needed for T401; no real data or integrations enabled.

- T402 **done (selected synthetic backend scope)**: `TaxRevision` in models,
  `migrations/versions/0150_tax_revisions.py`, `backend/core/owned_stores.py`.
  Same command as T401: **3 passed**. Real Alembic 0141→0150→0141→0150,
  model/column sync, populated downgrade refusal, immutable SQL update refusal,
  owner export and foreign/idempotent purge. One revision table retains case,
  source fields/period, reviews, calculation snapshots. No production DB touched.
- T403 **partial**: `backend/finance/tax/__init__.py`, tax service/controller,
  schemas/config/main router line and tests. Exact synthetic structured fields,
  original-source retention, per-field evidence selection with explanation,
  deterministic conflicts, owner 404, replay/CAS, default-off production-denied
  writes. Same command: collection initially failed (undefined `_bool`, fixed);
  then **4 passed**. Official-layout document ingestion, upload and frontend
  review are absent, rather than duplicating the shared statement runtime.
- T404 **partial**: `engines/tax/comparison.py`, sample packs and tests.
  Command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/tax/test_stage_h.py
  tests/tax/test_salary_rules.py -q -p no:cacheprovider -W ignore` → **43 passed**.
  Hand-derived old/new zero/slab/fractional boundaries, missing withholding,
  validity and scope refusals pass. Statutory implementation and professional
  verification intentionally missing; sample results never approved for real tax.
- T405 **partial**: tax service/controller export and draft routes and tests.
  Same focused command as T401 → **22 passed**. Owned immutable sample drafts,
  JSON review-pack download, stable snapshot SHA256, exact evidence/pack/input
  snapshots, stale after case/review/expiry, disabled-write historical read,
  foreign/missing 404 and exact export/engine consistency verified. Shared
  analysis/export quota reservations reused. No temporary export side store.
  Frontend and official forms absent. Replays preserve original draft and current
  stale state. No official acknowledgment/filing, PDF or external calls.
- T406 **partial**: `tests/tax/test_stage_h.py`,
  `tests/fixtures/tax/stage-h-goldens.json`, this progress file and scope runbook.
  Latest focused test **30 passed**; tax + all-route auth/tenancy + telemetry
  **170 passed, 7 skipped** (public-route skips). Coverage: period/validity and
  fractional boundaries; individual/residency/employer/income/deduction refusal;
  identity/period/income/withholding disagreements; preventing cross-person/year
  amount-field mixing; source preservation; replay and two-session SQLite CAS;
  draft/export exactness/staleness; rule correction/unavailability; quotas;
  foreign/missing 404; owner privacy export/delete/restore suppression; metadata.
  Review remains partial: no professional statutory review, official-reference
  examples, real forms, independent held-out evaluation, PostgreSQL runtime,
  CI/external review, production restore/load/privacy approvals or tax UI/browser
  journey. Existing browser regression suite **18 passed**; this is not tax UI
  acceptance. Full backend regression: **563 passed, 9 skipped** (H4 below).

## Review findings and disposition

- Fixed potential field mix: selecting matching identity/period from source A
  must not authorize salary/withholding from mismatching source B. Reconciler
  checks identity/year on each selected amount field; regression test explicitly
  attempts the cross-source mix and stays needs_review.
- Fixed import-time availability coupling: release pins are code constants, not
  an import-time file read; corrupt/missing optional packs cannot prevent app
  startup. Runtime failure returns bounded needs_review/stale reasons without
  file paths or exception payloads. Manifest is a review artifact, not authority.
- Unknown withholding is never zero; conflict-free explicit owner review of the
  current case is mandatory. Adjacent FY/AY is an unsupported result, not a
  substituted pack. No FinanceSnapshot/bank observation is treated as tax proof.
- Export is JSON (review pack), not an official form, and never contains an
  acknowledgment or filing capability. Snapshot SHA256 excludes dynamic stale
  metadata; historical amounts/evidence are reproduced exactly.
- Shared owner lock, atomic wrapper, auth/deletion checks, analysis/export quotas,
  telemetry, privacy registry and migrations_runner reused. No competing parser,
  upload, worker, throttle, finance or authorization service was introduced.

## Migration / recovery

0150 only, parent 0141. Table/model columns match; owner FK/index and unique
owner+operation and owner+case+kind+revision. SQLite and PostgreSQL UPDATE trigger
definitions forbid evidence mutation (only SQLite executed here). Authorized
privacy DELETE remains possible. Empty downgrade is reversible; populated
downgrade refuses. Disable TAX_SANDBOX_ENABLED before operator recovery; use the
shared migrations_runner and verified backup, prefer forward-fix for populated
tables. No actual user DB migration/rollback performed. No export file side store.
Shared legal retention/backup-expiry questions remain unresolved.

## Exact command log

H1 (run sequentially during T401, T402, T403, T405 and final review):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/tax/test_stage_h.py -q -p no:cacheprovider -W ignore`
Results in order: **1 passed**, **2 passed**, **3 passed**, **collection error
(NameError `_bool`; no tests ran)**, **4 passed**, **22 passed**, **30 passed in
11.52s**. Collection failure fixed before continuing T403. Latest H1 includes
updated file-backed independent goldens and code pins.

H2 (T404):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/tax/test_stage_h.py tests/tax/test_salary_rules.py -q -p no:cacheprovider -W ignore`
Result: **43 passed in 3.87s**. Archived engine unchanged and unused by new API.

H3 (T406 acceptance):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/tax tests/api/test_tenancy.py tests/api/test_telemetry.py -q -p no:cacheprovider -W ignore`
Result: **170 passed, 7 skipped in 124.08s**. Public routes explicitly skipped.

H4 (full backend regression):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Result: **563 passed, 9 skipped in 371.73s (0:06:11)**. Skips: seven explicitly public authentication routes and two opt-in PostgreSQL tests. All providers/tracing disabled by shared conftest; isolated SQLite migrations/fixtures. No backend failures.

H5 (existing browser suite, run once):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore`
Result: **18 passed in 59.45s**. Local server, temporary SQLite, providers disabled.

`git diff --check`: exit 0. The full suite regenerated `evals/results/latest.json`; restored its initially clean HEAD content with checkout CRLF line endings using read-only git show and a worktree-only write. No unrelated evaluation artifact retained. No staging, commit, push or deploy performed.

## Remaining / disabled and every open owner question

- T401 partial: approve D04 exact statutory FY/AY, age/person/residency/employer,
  old/new regimes, deductions and supported forms/layouts. Which official sources,
  independent examples and tax-professional reviewer will approve the pack?
  Assumed FY2024-25/AY2025-26 single-employer fictional individual;
  no age-based statutory rules exist here. Both regimes are invented samples only.
- T403 partial: real Form16/AIS/26AS/other supported-layout parser in shared
  isolated ingestion path, official-source identity matching and tax review UI.
  Should source review remain a structured synthetic import or expand to exact
  approved layouts? Default synthetic-only, no originals/PAN accepted.
- T404 partial: statutory rules, professional validation, official-source parameter
  register and full regime-specific relief/rounding/payment semantics. Existing
  sample packs do not satisfy statutory acceptance. No current-year substitution.
- T405 partial: orchestrator frontend evidence/review/draft/export/stale journeys;
  no tax UI/browser acceptance. JSON is the selected draft review-pack format;
  confirm whether a separately designed PDF is wanted later.
- T406 partial: professional/independent release acceptance, real-format and
  PostgreSQL concurrency/trigger execution, CI/external review, production
  lifecycle/retention/load approval and tax browser walkthrough. G4 not approved.
- Shared D02/D03/D07/D12 production location/keys/retention/budgets/legal questions
  remain with their existing owners. No approval inferred from passing tests.
- Tax sandbox defaults off; all production tax creation is denied even if toggled.
  Official filing/e-filing, certification, external tax/LLM/provider actions, real
  data, billing, trading, push/deploy remain disabled. No shared checklist ticked.
  T407–T409 are outside this lane; their unfulfilled statutory/UI/refresh acceptance
  is not claimed complete by this sample workflow.

## Decisions / remaining

Use lane E sample arithmetic, not archived statutory engine. Sample period inside
the existing harness is SAMPLE-2026 (pack validity year), explicitly wrapped by
the separate FY2024-25 case scope; it never supplies legal period rules.
Official forms/PDF/OCR are unsupported; structured synthetic fields only. No
second upload/parser/queue implementation. All rules say sample, unreviewed by
tax professional. Production writes always denied; sandbox toggle default off.
Real tax release, statutory sources, owner D04 approval, frontend/review UX and
  independent professional acceptance remain missing.
