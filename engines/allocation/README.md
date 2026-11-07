# Deterministic allocation sandbox (D05)

The allocator consumes the shared owned FinanceSnapshot, versioned suitability,
registered assumption pack and exact constraints. It conserves every paise using
ceil minima, floor maxima, targets and stable cash/debt/equity/gold residual order.
It never executes, selects named products or optimizes invented expected returns.

Real recommendation calls refuse with `assumptions not validated`. Synthetic
calculation requires an explicit synthetic_test argument and APP_ENV=test. Invented
market/risk/cost numbers live exclusively in labelled test fixtures. Production
registry is empty. Public eligibility remains hard-false independently of parameter
validation, environment flags or model prose. Parameter validation and the separate
public-advice decision are PENDING; no reviewer is appointed.

The policy register supplies configurable defaults (cash floor 1000 bps; near-term
horizon 36 months), labelled unvalidated_prototype. Scenario overrides are reported
separately from original registered defaults. These are not universal suitability
rules. Both suitability and the solver consume the configured near-term boundary.

Every class has unknown liquidity unless dated instrument/restriction/settlement
and source evidence provides a duration. Unknown or expired evidence fails a
liquidity deadline; without a deadline, a synthetic allocation makes no claim that
its holdings are liquid. Cash floor denotes class weight only, not verified cash
availability. Declared eligible cash still cannot exceed shared contribution capacity.

Costs/stress remain synthetic comparisons. Sales costs and taxes are unknown;
net improvement is blocked. Source/policy changes and expiry mark immutable plans
stale while preserving original inputs/results. Existing privacy export/purge
hooks cover the existing AllocationPlan store; the file-backed global register has
no personal data and introduces no table. Model output is discarded by output_guard.

Authenticated GET /allocation-assumptions exposes the prototype register. Existing
scenario/plan routes remain default-off; test-only synthetic calculation does not
authorize public advice, external integrations, execution or a frontend release.
