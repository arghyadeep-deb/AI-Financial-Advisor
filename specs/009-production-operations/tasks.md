# Tasks — Production reliability, deployment and cost controls

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T0901** Define reproducible deployment and CI. Location: `deployment/, .github/workflows/, docs/operations/`. Requirements: F009-FR01.
  - Done when: Clean environment deploys; missing production secrets fails startup; migration recovery tested.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0902** Implement durable queue recovery. Location: `backend/workers/`. Requirements: F009-FR02.
  - Done when: Lease expiry and stale worker fencing prevent duplicate commit; atomic outbox and orphan cleanup tested.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0903** Implement quotas and cost budgets. Location: `backend/core/limits/`. Requirements: F009-FR04.
  - Done when: 429/retry paths work; exhausted model budget returns deterministic report; no runaway retries.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0904** Add privacy-safe metrics and alerts. Location: `backend/observability/`. Requirements: F009-FR05.
  - Done when: Synthetic incidents trigger actionable alerts; exporter outage has no ledger effect.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0905** Run load and failure experiments. Location: `tests/load/ and tests/integration/`. Requirements: F009-FR03.
  - Done when: Record dataset, hardware and p95 against ratified targets, including concurrent same-account imports.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0906** Implement backup/restore and incident runbooks. Location: `docs/operations/ and deployment/`. Requirements: F009-FR06.
  - Done when: Time a restore and compare exact totals, record counts and deleted-account suppression.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0907** Prepare release evidence and cost model. Location: `docs/releases/`. Requirements: F009-FR03, F009-FR04, F009-FR06.
  - Done when: Named owner, limits, monthly cost assumptions, rollback and residual risks recorded; no checkbox-only approval.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
