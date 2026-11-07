# Tasks — Commercial readiness, subscriptions and customer support

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [x] **T1301** Record pricing and service policy. Location: `docs/product/`. Requirements: F013-FR01, F013-FR05.
  - Done when: No fabricated pricing assumptions; owner decides tiers and support capacity.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1302** Implement provider sandbox and event machine. Location: `backend/integrations/billing/`. Requirements: F013-FR02.
  - Done when: Replay, signature failure, refund and out-of-order event tests pass.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T1303** Implement entitlements and downgrade. Location: `backend/services/entitlements/`. Requirements: F013-FR03.
  - Done when: Downgraded user retains privacy/export access; client flag cannot unlock paid capability.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1304** Build safe support tools. Location: `backend/services/support/ and frontend/`. Requirements: F013-FR04, F013-FR05.
  - Done when: Request-ID lookup is audited; raw documents require explicit authorized access.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T1305** Implement privacy-safe analytics. Location: `backend/observability/`. Requirements: F013-FR06.
  - Done when: Payload capture shows no financial/customer document fields.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1306** Run commercial acceptance. Location: `tests/billing/ and docs/releases/`. Requirements: F013-FR02, F013-FR06.
  - Done when: Cancellation/refund/restore and unknown-outcome scenarios verified before live payments.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
