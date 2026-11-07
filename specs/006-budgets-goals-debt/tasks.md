# Tasks — Budgets, recurring bills, goals and debt planning

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T0601** Define budget/goal/obligation schemas and migrations. Location: `backend/models/ and migrations/`. Requirements: F006-FR01, F006-FR03.
  - Done when: Old reports retain their budget revision; archived budgets remain auditable.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0602** Implement budget APIs and category splits. Location: `backend/finance/budgets/ and backend/controllers/`. Requirements: F006-FR01.
  - Done when: 5,000/5,500 fixture shows 500 overspend; splits conserve paise; two-user checks pass.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0603** Implement recurring candidate and settlement rules. Location: `backend/finance/obligations/`. Requirements: F006-FR02.
  - Done when: Variable/annual bills, false positives, duplicate payments and paused bills are tested.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0604** Implement goal and reserve calculation. Location: `engines/planning/`. Requirements: F006-FR03, F006-FR05.
  - Done when: Zero return, inflation, deadline already passed and competing goals have independently computed fixtures.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0605** Implement debt scenarios. Location: `engines/debt/`. Requirements: F006-FR04, F006-FR05.
  - Done when: Interest and payoff match independent schedules; negative amortization and missing rates are flagged.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0606** Build planning UI and reminders. Location: `frontend/ and backend/services/notifications/`. Requirements: F006-FR06.
  - Done when: User can edit, undo and explain a budget; no reminder before opt-in; outage does not duplicate delivery.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0607** Evaluate full planning flows. Location: `tests/planning/ and evals/`. Requirements: F006-FR05, F006-FR06.
  - Done when: Deficit profile receives no positive allocation; golden totals and trace isolation pass.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
