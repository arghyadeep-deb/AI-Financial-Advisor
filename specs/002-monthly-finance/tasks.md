# Tasks — Monthly Finance Agent

Prerequisites are 001, [spec](spec.md), [plan](plan.md), [contract](contracts/import-and-report.md), and [data model](data-model.md).

## Setup

- [ ] T201 Confirm one pilot bank layout and CSV schema. Add synthetic fixtures for supported, duplicate, mismatch, unsupported, and overlapping cases under `tests/fixtures/statements/`.
- [x] T202 Add account, document, job, staged row, evidence, ledger, review, and report migrations in `migrations/` and `backend/models/`.
- [ ] T203 Add private upload, scanner interface, size/time limits, signed download policy, and storage fakes under `backend/finance/`.

## US1 Upload and verify

- [x] T204 [US1] Implement owned account and upload/job routes in `backend/controllers/statement_controller.py`.
- [ ] T205 [US1] Implement the PDF and CSV adapters in `backend/finance/importers/`. Preserve source page or row, balance evidence and parser version.
- [ ] T206 [US1] Implement worker claim, retry, and checkpoint integration in `backend/workers/` and `agents/monthly_finance_graph.py`.

## US2 Resolve ambiguity

- [ ] T207 [US2] Implement exact reconciliation, overlap matching, revision-safe review and idempotent resume in `backend/finance/ledger.py` and `agents/monthly_finance_graph.py`.
- [x] T208 [US2] Implement import status and review UI under `frontend/`. Display balance differences and source references. Test restart and cross-user denial.
- [ ] T209 [US2] Add verified transfer, card repayment, and refund links in `backend/finance/ledger.py`. Test distinct repeated amounts, one-sided coverage and ambiguous candidates.

## US3 Publish and inspect

- [x] T210 [US3] Implement transactional commit and reversal in `backend/finance/ledger.py`.
- [ ] T211 [US3] Implement immutable report, evidence drill-down, PDF/CSV export and stale states in `backend/services/monthly_report_service.py` and `frontend/`.
- [ ] T212 [US3] Surface canonical current facts in Dashboard, Reports and Chat. Verify the deficit fixture end to end.

## US4 Explain and release

- [ ] T213 [US4] Add merchant category suggestions and factual narration with a deterministic fallback in `agents/monthly_finance_graph.py`.
- [ ] T214 [US4] Add offline parser, reconciliation, tenant, failure and privacy evals under `evals/` and `tests/`. Optional sanitized LangSmith experiment follows the offline suite.
- [ ] T215 Run the [walkthrough](quickstart.md) and [review checklist](../review-checklist.md). Record operational limits and restore evidence before any real-data pilot.

## Detailed implementation and verification

- [ ] **T216** Implement FIN-01 through FIN-16 metric definitions and coverage states. Location: `backend/finance/ledger.py, tests/finance/`.
  - Done when: Independent exact totals; unknown credits never become salary and surplus never implies automatic affordability.
  - Evidence: pending implementation and independent verification.

- [ ] **T217** Implement shared-evidence reversal, cancellation and reprocess generations. Location: `backend/finance/, backend/workers/`.
  - Done when: All reversal contract scenarios pass under concurrent requests and worker restarts.
  - Evidence: pending implementation and independent verification.

- [ ] **T218** Implement multi-account/link revision vector and scope coverage. Location: `backend/services/monthly_report_service.py`.
  - Done when: Concurrent update in either account prevents stale current report; immutable historical export remains reproducible.
  - Evidence: pending implementation and independent verification.

- [ ] **T219** Integrate core budgets and explicit card scope. Location: `frontend/, backend/services/`.
  - Done when: Budget edits have revisions; unsupported cards show support status; US4 has real budget/confirmed bill inputs.
  - Evidence: pending implementation and independent verification.

- [ ] **T220** Run full real-data pilot readiness gate. Location: `tests/integration/, docs/releases/`.
  - Done when: 008 deletion, 009 restore/limits and 010 user journey evidence complete before enabling real uploads.
  - Evidence: pending implementation and independent verification.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

Build order and shared task ownership are defined in [implementation order](../implementation-order.md). IDs are stable identifiers, not execution order.
