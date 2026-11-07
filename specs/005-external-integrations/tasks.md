# Tasks — Credit tracking and external integrations

- [ ] T501 [US1] Implement dated source-labeled credit observations and debt/card views in `backend/models/`, `backend/services/` and `frontend/`.
- [ ] T502 [US1] Test unknown, user-reported, stale, and missing limit behavior in `tests/`.
- [x] T503 [US2] Document partner eligibility, supported institutions, consent, use restrictions, retention and incident ownership before adding any bank or bureau credentials.
- [x] T504 [US2] Add a test-only bank adapter and consent/replay tests in `backend/integrations/` and `tests/`. Enforce the 002 ledger contract.
- [ ] T505 [US3] Define separate bureau and ERI contracts once partner evidence exists. Add signed callback, acknowledgement, explicit user confirmation and failure tests for each supported action.
- [ ] T506 Obtain separate product approval and Codex review for each live flag. Record provider limitations, rollback and consent checks.

## Detailed implementation and verification

- [ ] **T507** Implement manual credit evidence and discrepancy flow. Location: `backend/services/credit/, frontend/`.
  - Done when: Unknown/stale/different-bureau results cannot become a false single trend or loan eligibility claim.
  - Evidence: pending implementation and independent verification.

- [x] **T508** Implement sync/PDF overlap and consent-race contract tests. Location: `tests/integrations/`.
  - Done when: Revocation during fetch stops commit; repeated/out-of-order provider evidence never duplicates ledger.
  - Evidence: pending implementation and independent verification.

- [x] **T509** Implement external operation unknown-outcome state machine in mocks. Location: `backend/integrations/, tests/`.
  - Done when: Timeout after submission leads to status reconciliation, not duplicate action.
  - Evidence: pending implementation and independent verification.

- [x] **T510** Document provider onboarding and exit readiness. Location: `docs/integrations/`.
  - Done when: Eligibility, licensed use, scopes, credentials, incident owner, retention, outages and exit plan recorded per adapter.
  - Evidence: pending implementation and independent verification.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

Build order and shared task ownership are defined in [implementation order](../implementation-order.md). IDs are stable identifiers, not execution order.
