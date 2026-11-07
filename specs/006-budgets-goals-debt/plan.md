# Implementation plan — Budgets, recurring bills, goals and debt planning

Planning only. Read [spec](spec.md), [tasks](tasks.md), [architecture](../architecture.md), [constitution](../constitution.md) and [release gates](../release-gates.md). Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## Data and service contract
BudgetVersion, BudgetLine, RecurringCandidate, Obligation, SettlementLink, Goal and FundingAllocation. `POST/GET/PATCH /budgets`, `/goals`, `/obligations` use expected revisions. `POST /debt-scenarios` returns an immutable scenario and assumptions, never modifies a loan. Keep a distinct present-cash and future-flow capacity breakdown.

## Implementation sequence
1. Resolve only this feature's prerequisite decisions and pin its schema/API examples.
2. Add migrations with synthetic legacy fixtures and owner/revision constraints.
3. Implement deterministic services and immutable result snapshots before model narrative.
4. Add authenticated API and user-facing complete/partial/stale/error states.
5. Exercise wrong-owner, concurrency, retry, source change and provider outage cases.
6. Run feature acceptance, independent evaluations and appropriate operational checks; hand off actual evidence.

## Constitution check and recovery
Financial amounts come from tools; external text cannot authorize actions. All resources are owned and covered by deletion. Avoid storing payloads in traces. Use feature flags and source/rule versions. On rollback disable new work for this capability, preserve inspectable history and use documented database recovery. Dependent plans/reports become stale when evidence changes. No schema downgrade may silently delete customer evidence. Migration and rollback details must be completed against the chosen implementation, not invented now.

## Validation evidence
Each task below has an acceptance statement. Attach code revision, test command, fixture version, result, skipped checks and residual risk. Include browser evidence for visible flows. For numerical engines compare to independently calculated fixtures; for AI evaluate held-out examples with deterministic fact checking. Implementation paths are proposed module boundaries, not claims that modules already exist.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
