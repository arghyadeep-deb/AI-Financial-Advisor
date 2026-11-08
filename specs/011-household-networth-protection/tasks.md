# Tasks — Household net worth and protection inventory

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [x] **T1101** Implement assets/liabilities and ownership shares. Location: `backend/models/ and backend/finance/networth/`. Requirements: F011-FR01, F011-FR06.
  - Done when: Duplicate asset and partial share fixtures produce correct consolidated totals.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1102** Implement household invites/grants. Location: `backend/services/household/`. Requirements: F011-FR02.
  - Done when: Expired/replayed invites fail; membership does not grant account access.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T1103** Enforce revocation on every view/export. Location: `backend/controllers/ and tests/`. Requirements: F011-FR02, F011-FR03.
  - Done when: Cached dashboard, chat and queued export deny access after revocation.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1104** Implement protection inventory and reminders. Location: `backend/services/protection/ and frontend/`. Requirements: F011-FR04, F011-FR05.
  - Done when: Missing policy fields remain unknown; reminders require preferences.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1105** Build net-worth and household UI. Location: `frontend/`. Requirements: F011-FR01, F011-FR05, F011-FR06.
  - Done when: Each value shows date/source/share; personal versus shared context is clear.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1106** Evaluate joint ownership and privacy. Location: `tests/household/`. Requirements: F011-FR03, F011-FR06.
  - Done when: Concurrent grant changes, double allocation and private-tax-document access tested.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
