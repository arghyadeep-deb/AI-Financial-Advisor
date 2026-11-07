# Feature specification — Personalized allocation and portfolio optimization

**Status: D05 scenario/backend implementation authorized; public release pending.** Version 2.2 · 2026-11-05

Release: R3; user-selected sandbox first; public proposals independently gated. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Understand suitability.** Given high stated risk tolerance but a near-term essential goal, explain the capacity conflict and request a resolution rather than assume high equity risk is appropriate.
- **US2 (P1) Compare feasible plans.** Given complete holdings and a verified contribution cap, return reproducible constrained alternatives with costs and assumptions, or an explicit no-feasible-plan result.
- **US3 (P2) Review a changed plan.** After salary, goals, prices or holdings change, show the old plan as stale and calculate a new version without executing trades.

## Functional requirements
### F007-FR01 — Suitability record
Collect horizon, essential goals, dependants, income stability, debt, reserve needs, experience, loss tolerance and capacity. Version questionnaire, answers and contradictions. Never infer capacity from age or income alone. Incomplete material fields block personalized publication.

### F007-FR02 — Supported universe
Start with asset-class scenarios for documented INR instruments. Define liquidity, bounds, concentration, prohibited assets and price/source freshness. Named security proposals require a separately approved universe, evidence and release gate; a label of educational does not bypass that gate.

### F007-FR03 — Deterministic solver
Use a documented constraint solver or transparent rule-based allocator, with cash conservation, no leverage/shorting by default, minimum liquidity and user exclusions. Return feasibility/status and binding constraints. Do not choose expected returns from model prose; use versioned assumptions and sensitivity ranges.

### F007-FR04 — Costs and taxes
Compare new-contribution-only adjustment before sales. Estimate transaction costs, exit loads and taxes only with sufficient data and a supported rule pack; otherwise show excluded/unknown costs and block a claimed net improvement.

### F007-FR05 — Robustness and explanations
Compare against current allocation and a simple documented baseline; test adverse returns, delayed income and volatility. Show uncertainty, horizon and trade-offs, not a guaranteed return or risk-free claim. Backtests require point-in-time inputs and fees; historical performance is not a future guarantee.

### F007-FR06 — Autonomy boundary
Agent gathers authorized facts, asks only for missing inputs, computes, validates and drafts. A plan has input revisions, model assumptions, expiry/revalidation and eligibility status. It never places an order. Public personalized advice remains disabled until the applicability decision in compliance-register.md is resolved.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

## Owner decision D05 (2026-11-07)

Implementation is authorized for cash/debt/equity/gold scenarios only. A versioned
assumption register records each parameter's id/version, source name/URL/publisher,
as-of date, methodology, uncertainty/range, expiry and status (synthetic_test,
unvalidated_prototype or validated). Real recommendation paths refuse explicitly
with "assumptions not validated" unless every used assumption is validated and
current. No supplied assumption is validated. Historical data never guarantees
future returns. Invented returns, volatility and risk limits belong only in
explicit synthetic_test fixtures used by automated tests.

The cash-floor and near-term thresholds are configurable unvalidated_prototype
policies; their labels and effective values appear in explanations. They are not
universal suitability rules. Liquidity is unknown for every class/instrument unless
instrument, restriction and settlement evidence provides a dated duration; unknown
never counts as liquid and cannot meet a deadline. Old immutable receipts remain
historical, stale when evidence changes, without rewriting their original numbers.

Parameter validation and the separate public-advice eligibility decision are
PENDING; no reviewer appointed. Public eligibility stays hard-false and execution
stays disabled independently of solver feasibility or parameter-validation status.
