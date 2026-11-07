# Feature specification — Monthly Finance Agent

**Suggested branch** `002-monthly-finance` · **Status** Proposed; awaiting user selection · **Date** 2026-11-05

## User stories and independent acceptance

- **US1 (P1) Import and verify a supported statement.** Given a supported PDF or CSV, the user uploads it to an owned account and sees the resulting verified rows or actionable exceptions. Uploading the same file twice returns the existing import. A worker restart preserves progress.
- **US2 (P1) Review and resolve ambiguity.** Given an overlapping statement or a mismatch, show the conflicting source rows and balance difference. The user corrects permitted fields, confirms a match, or replaces the statement. An unauthorized or stale resume is refused. Reconciliation runs again after edits.
- **US3 (P1) Publish a monthly report.** Given two overlapping inputs with a transfer, a card repayment, and a refund, the app generates one report with correct totals and links to sources. A partial report shows its coverage. A failing account stays under review. A user can export and safely reverse an eligible import.
- **US4 (P2) Understand what changed.** Given current and previous verified months, the agent explains differences with evidence and shows recurring bills and budget comparisons where supported. If the model fails, the report remains usable.

## Functional requirements

- **FR-001** Pilot supports one selected Indian bank’s text-PDF layout and one documented CSV schema. Confirm the bank using a synthetic or authorized sanitized layout fixture before implementation. Detect unsupported, scanned, protected, oversized, and corrupt inputs with actionable states. Provide upload progress and retry.
- **FR-002** User owns account, import, document, staged row, ledger row, report, and export. Keep private encrypted documents, expiry on download links, file scan and parser limits. Store exact INR values, posting date, direction, original description, optional bank reference and source row/page.
- **FR-003** Verify stated balances when present and surface source coverage. A format without balance evidence is labeled unverified for that account. A failed balance check blocks verified publication. Account-level cash conservation and household-level expense classification are separate checks.
- **FR-004** Deduplicate identical content per owner and account. Across overlapping files, prefer a stable bank reference scoped to the account. Suggest matching using amount, date, and description only when evidence is sufficient. Preserve legitimate identical transactions and source lineage. Require review for ambiguous matches.
- **FR-005** Match own-account transfers and card repayments when both sides are available. Count a card purchase once. Treat unmatched movements explicitly, record refunds as linked adjustments when confirmed, and preserve all underlying debit/credit rows. Expose unknown categories and user corrections.
- **FR-006** Generate versioned report metrics using selected accounts and calendar-month boundaries in Asia/Kolkata. Show coverage, income, spending, cash movement, bills, EMIs, category/budget differences, and surplus with explicit definitions. Enable source drill-down and CSV/PDF export of the snapshot.
- **FR-007** Use a durable workflow with safe retries, an authenticated review interrupt, and idempotent publication. Cancel/reverse by creating a new ledger/report revision with preserved lineage. Shared canonical facts serve Dashboard, Reports and Chat.
- **FR-008** Allow AI category suggestions and explanations over sanitized data within approved schema. Retain the report if explanation fails. Use user-visible provenance and privacy-safe traces.
- **F002-FR09** Implement [canonical financial rules](../financial-rules.md) including loan principal, card settlement, investments, withdrawals, partial refunds and unknown classifications. Balance reconciliation and classification completeness are independent flags.
- **F002-FR10** Implement [evidence-aware cancellation and reversal](contracts/reversal-and-concurrency.md). Shared evidence, cross-account links and explicit reprocess generations must remain consistent.
- **F002-FR11** Account coverage uses intervals and declared inventory; report publication compares all included account/link/rule revisions. A partial account cannot imply complete household coverage.
- **F002-FR12** Core budget comparison is delivered by 006's versioned budgets; recurring obligations use confirmed candidates. Do not mark US4 complete with narration alone.
- **F002-FR13** Scanner timeout/unavailability quarantines files; worker leases/outbox and resource quotas come from 009; parser isolation T1402 is part of the initial upload implementation. No unbounded parser in the API process. Source page access reauthorizes every request.
- **F002-FR14** Decide whether the first bank layout covers debit accounts only. Card purchase fixtures are valid canonical ledger tests but must not imply a released card-statement adapter. Unsupported account/layout types stay blocked until independently tested.

## Success criteria

- **SC-001** Golden tests cover duplicate bytes, overlapping dates, distinct identical transactions, malformed PDFs, unmatched transfers, refund timing, and coverage gaps. All reconciled totals match exact expected paise.
- **SC-002** Duplicate job submission, parallel imports, restart and repeated resume produce zero duplicate ledger commits. Cross-user review and download attempts fail.
- **SC-003** Pilot test yields verified ₹45,000 income, ₹55,000 expense, and ₹10,000 shortfall consistently across all views. A separate fixture verifies proper handling of transfer, card repayment, and refund.
- **SC-004** Users can inspect each report line’s contributing rows, safely reverse an import, and reproduce the export. Failed reconciliation and AI outage remain distinguishable.

Read [implementation order](../implementation-order.md) for build prerequisites and release gates. See [acceptance mapping](acceptance.md) for requirement-to-task evidence.
