# Tasks — Document coverage, OCR and transaction corrections

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T1401** Create format registry and support UI. Location: `backend/finance/importers/ and frontend/`. Requirements: F014-FR01.
  - Done when: Supported versus unsupported/scanned/protected states are explicit.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1402** Implement isolated parser/scanner runtime. Location: `backend/workers/ and deployment/`. Requirements: F014-FR02.
  - Done when: Oversize, malicious, timeout and unavailable-scanner cases cannot reach publication.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T1403** Implement manual cash and split API. Location: `backend/finance/ledger.py and backend/controllers/`. Requirements: F014-FR05.
  - Done when: Paise conserved; later bank import match and cash withdrawal do not double count.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1404** Add one additional approved adapter. Location: `backend/finance/importers/ and tests/fixtures/`. Requirements: F014-FR01, F014-FR06.
  - Done when: Held-out files pass exact fields and reconciliation; support matrix records actual scope.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1405** Implement optional protected/OCR path. Location: `backend/finance/importers/`. Requirements: F014-FR03, F014-FR04.
  - Done when: No password persistence; low-confidence critical field pauses; external OCR disabled without appropriate data-sharing choice.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1406** Verify adapter regression/reprocess. Location: `evals/importers/ and tests/integration/`. Requirements: F014-FR06.
  - Done when: Parser rollback, drift quarantine, restart and unchanged old snapshot tests pass.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
