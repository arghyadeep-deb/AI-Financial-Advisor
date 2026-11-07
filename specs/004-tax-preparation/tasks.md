# Tasks — Tax preparation agent

- [ ] T401 Define the exact supported period, regime, taxpayer scope, documents and official-reference examples under `engines/tax/` and `tests/fixtures/tax/`.
- [ ] T402 [US1] Add case, period, source fields and revision storage in `backend/models/` and `migrations/`.
- [ ] T403 [US1] Add owned parser and field-evidence review under `backend/finance/tax/` and `frontend/`.
- [ ] T404 [US2] Implement versioned computation and unsupported-case checks under `engines/tax/`.
- [ ] T405 [US3] Add draft export, stale status and evidence drill-down under `backend/services/` and `frontend/`.
- [ ] T406 Test period boundaries, identity and withholding conflicts, scope refusals, draft consistency, authorization and trace payloads. Record review and release limits.

## Detailed implementation and verification

- [ ] **T407** Write tax scope matrix and source register. Location: `engines/tax/, docs/tax/`.
  - Done when: Exact forms/period/rules and exclusions chosen; all statutory parameters have official references.
  - Evidence: pending implementation and independent verification.

- [ ] **T408** Implement conflict resolution and rule-pack release gate. Location: `backend/finance/tax/, tests/tax/`.
  - Done when: Identity/period/income/withholding mismatch pauses; no draft from unsupported inputs.
  - Evidence: pending implementation and independent verification.

- [ ] **T409** Add annual refresh, boundary fixtures and draft revision tests. Location: `tests/tax/, frontend/`.
  - Done when: Independent boundary calculations pass; changed rule pack marks draft stale; export clearly says draft.
  - Evidence: pending implementation and independent verification.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

Build order and shared task ownership are defined in [implementation order](../implementation-order.md). IDs are stable identifiers, not execution order.
