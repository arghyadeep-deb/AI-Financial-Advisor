# Tasks — Onboarding, responsive UI, accessibility and notifications

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T1001** Create screen/state inventory and flows. Location: `docs/ux/`. Requirements: F010-FR01, F010-FR02.
  - Done when: Every enabled feature maps to a screen and all failure/stale states.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1002** Build onboarding and isolated demo. Location: `frontend/`. Requirements: F010-FR01, F010-FR04.
  - Done when: Demo cannot mix with real account; supported formats and privacy visible before upload.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1003** Build report/transaction review interactions. Location: `frontend/`. Requirements: F010-FR02.
  - Done when: Filters persist, source drill-down works, revision conflicts preserve user input.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1004** Implement accessibility and responsive checks. Location: `frontend/ and tests/ui/`. Requirements: F010-FR03.
  - Done when: Keyboard/screen-reader smoke and 360/768/1440px checks pass; charts have text summaries.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1005** Implement notification preferences and delivery. Location: `backend/services/notifications/ and frontend/`. Requirements: F010-FR05.
  - Done when: Opt-out, quiet hours, duplicate event and invalid channel tests pass.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1006** Run usability and locale acceptance. Location: `docs/ux/ and evals/ux/`. Requirements: F010-FR04, F010-FR06.
  - Done when: Record real completion results; Hindi/Hinglish release requires amount/evidence parity fixtures.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
