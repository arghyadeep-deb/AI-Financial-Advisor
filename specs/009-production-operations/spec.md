# Feature specification — Production reliability, deployment and cost controls

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: Pilot requirements before R1; broader targets before public launch. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Recover processing.** A worker killed before or after commit resumes without duplicated transactions or a permanently spinning UI.
- **US2 (P1) Operate under pressure.** An overloaded service rejects or queues bounded work with clear status, preserving existing reports.
- **US3 (P2) Restore safely.** An operator restores a backup into isolation and proves balances, tenant boundaries and deletion suppression before reopening access.

## Functional requirements
### F009-FR01 — Environment and deployment
Document local/staging/production configuration, pinned builds, secrets management, HTTPS, health/readiness, DB migration order and rollback. Staging uses synthetic data. CI tests schema upgrades and rejects accidental secrets and vulnerable release dependencies according to recorded policy.

### F009-FR02 — Queue recovery
Use leases, fencing, heartbeat, bounded retries, dead-letter inspection and backlog metrics. Atomic outbox avoids stored file with no job. Orphan objects have expiry cleanup; sweepers must not delete active uploads. Cancellation and deletion checked at commit boundary.

### F009-FR03 — Proposed service targets
Pilot test baseline: 25 concurrent sessions, 5 concurrent imports, 10 MB/50-page/10,000-row limits per supported text file; p95 non-upload read API <1s; p95 supported text import <60s excluding user review. Targets are proposals to benchmark and ratify, not achieved claims. Public launch candidate availability 99.5% monthly, RPO <=24h and RTO <=4h; tighten if business use requires it.

### F009-FR04 — Resource and spend controls
Per-user upload/storage/job/model quotas and global circuit breakers. Cap AI steps, tokens, retries and wall time; no infinite agent loops. Record cost per completed report, including failed attempts, storage and OCR. Product owner chooses monetary caps before enabling paid providers; exhausted budget preserves deterministic access.

### F009-FR05 — Monitoring and response
Metrics for queue age, failed reconciliation, partial report rate, auth abuse, p95 latency, model cost and deletion lag. Trace/exporter outage must not block processing. Runbooks assign an on-call owner, severity and recovery actions. Alert on stale jobs and financial correctness regressions, with no raw user data.

### F009-FR06 — Backups and release evidence
Encrypted scheduled backups, restoration drill, deletion replay, schema compatibility and rollback/forward fix. Canary by feature flag; stop new imports on parser regression. Preserve source and report versions. Independent security review and load/restore acceptance precede broad release.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
