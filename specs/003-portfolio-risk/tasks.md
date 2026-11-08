# Tasks — Portfolio tracking and risk

- [x] T301 [US1] Define owned holding, instrument, observation and dated valuation schemas in `backend/models/` and `migrations/`.
- [x] T302 [US1] Implement validated, repeat-safe CSV/manual ingestion and read APIs in `backend/finance/` and `backend/controllers/`.
- [ ] T303 [US1] Implement explicit current/partial/unavailable valuation and position drill-down under `backend/services/` and `frontend/`.
- [x] T304 [US2] Add scenario math and verified contribution constraints in `engines/`. Add shortfall and missing-input tests in `tests/`.
- [ ] T305 [US3] Add concentration, currency and coverage checks and explanations in `backend/services/` and `frontend/`.
- [ ] T306 Test authorization, projection separation, price/source coverage and advice gating. Record Codex acceptance against the [review checklist](../review-checklist.md).

## Detailed implementation and verification

- [x] **T307** Implement observation identity and duplicate/source-conflict review. Location: `backend/finance/holdings/, migrations/`.
  - Done when: Manual/import overlap, closed position and stale observation fixtures pass.
  - Evidence: pending implementation and independent verification.

- [ ] **T308** Implement supported returns and benchmark contracts. Location: `engines/portfolio/, tests/portfolio/`.
  - Done when: Independent dated-flow examples; missing basis, no-solution and unsupported corporate action cases are unavailable.
  - Evidence: pending implementation and independent verification.

- [ ] **T309** Version valuation sources and downstream invalidation. Location: `backend/services/`.
  - Done when: Price/holding correction invalidates affected plans/net worth; no fabricated quote fallback.
  - Evidence: pending implementation and independent verification.

- [ ] **T310** Verify 007/011 snapshot consumers and UI. Location: `tests/contracts/, frontend/`.
  - Done when: Source date, partial coverage, returns method and projection distinction visible; public advice gate enforced.
  - Evidence: pending implementation and independent verification.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

Build order and shared task ownership are defined in [implementation order](../implementation-order.md). IDs are stable identifiers, not execution order.
