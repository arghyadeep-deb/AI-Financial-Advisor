# Implementation plan — Personalized allocation and portfolio optimization

Planning only. Read [spec](spec.md), [tasks](tasks.md), [architecture](../architecture.md), [constitution](../constitution.md) and [release gates](../release-gates.md). Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## Data and service contract
SuitabilityRevision, UniverseVersion, AssumptionPack and AllocationPlan. `POST /allocation-scenarios` and gated `POST /allocation-proposals` accept snapshot IDs and constraints; return feasible, infeasible, insufficient_data or gated status, allocation, costs, sources and reasons. `GET /allocation-plans/{id}` checks owner. Use exact monetary constraints even if numerical optimization uses bounded tolerances; validate final rounded amounts deterministically.

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

## D05 implementation contract

Reuse the shared source registry, suitability, FinanceSnapshot, AllocationPlan,
owned-store hooks and output_guard. Store the nonpersonal prototype register as
versioned repository JSON, loaded through strict Pydantic contracts; no new table
or migration is needed. Expose authenticated GET /allocation-assumptions. Freeze
the used policy register and scenario overrides in existing immutable plan receipts.

Market/risk/cost assumptions are per-scalar synthetic_test registers under
 tests/fixtures/allocation (test environment only). Both source hashes and individual
as-of/expiry dates fail closed. Register revisions and expiry invalidate saved plans.
No validated pack exists; real recommendations refuse "assumptions not validated".
The public-advice eligibility decision remains a separate hard-false gate.

Cash-floor and near-term policy defaults come from the unvalidated_prototype
register; request overrides retain that label and disclose applied values separately.
Liquidity duration is optional and requires instrument/restriction/settlement/source
and validity dates. Unknown/expired liquidity excludes a class under a deadline;
a scenario without a deadline explicitly disclaims verified liquidity.
