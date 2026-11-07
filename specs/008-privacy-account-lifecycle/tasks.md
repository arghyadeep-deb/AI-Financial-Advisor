# Tasks — Privacy, consent and account lifecycle

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T0801** Create data inventory and retention configuration. Location: `docs/privacy/ and backend/core/`. Requirements: F008-FR01, F008-FR06.
  - Done when: Every storage surface and processor mapped; no unresolved retention default before real-data release.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0802** Implement sessions, recovery and reauthentication. Location: `backend/core/ and backend/services/auth_service.py`. Requirements: F008-FR04.
  - Done when: Reset replay fails, sessions revoke, enumeration responses match, rate limits tested.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0803** Implement consent records and revocation checks. Location: `backend/models/ and backend/services/consent/`. Requirements: F008-FR06.
  - Done when: A job queued before revocation cannot fetch or publish afterward.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0804** Implement owned data export. Location: `backend/services/privacy/`. Requirements: F008-FR02.
  - Done when: Export requires recent auth and expires; second user cannot read it.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0805** Implement deletion orchestrator and suppression journal. Location: `backend/workers/ and backend/services/privacy/`. Requirements: F008-FR02, F008-FR03.
  - Done when: Injected failure resumes; all listed stores covered; backup restoration cannot reactivate deleted user.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0806** Configure encryption, access and audit controls. Location: `deployment/ and backend/core/`. Requirements: F008-FR05.
  - Done when: Key rotation and least-privilege denial exercised; operator access recorded without payloads.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0807** Verify lifecycle acceptance. Location: `tests/privacy/ and docs/privacy/`. Requirements: F008-FR03, F008-FR06.
  - Done when: Complete export/delete/restore drills with fictional unique identifiers and recorded evidence.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
