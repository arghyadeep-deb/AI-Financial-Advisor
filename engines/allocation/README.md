# Synthetic allocation v1

Contracts precede consumers: suitability answers, assumption pack, constraints,
holdings and result are strict frozen Pydantic contracts. The caller supplies a
canonical owned FinanceSnapshot and explicit eligible liquid cash after commitments
and reserves; budget is the lesser of that cash and canonical contribution.
Profile-aggregate snapshots remain declared scenarios, never verified liquidity.

The source registry must resolve the exact pack version/hash, authorize its owner,
and validate effective/expiry dates. The parsed source must match every pack field.
The only supplied pack is synthetic. Production source catalog is empty.

The allocator assigns rounded-up minima, then rounded-down targets, then remaining
capacity, always in cash/debt/equity order. Every paise is conserved within bounds;
no shorting/leverage. Default cash minimum is 10%. Low/moderate/high stated capacity
caps equity at 10/40/60%; a horizon or essential goal under 36 months, or unstable
income, caps it at zero. These are conservative synthetic v1 policy assumptions,
not validated investment guidance. Contradictory high tolerance blocks calculation
before these caps; it is never silently converted into high capacity.

Cost comparison retains holdings and uses new contributions first. Annual fees
are synthetic estimates rounded up once. Sales have unknown transaction cost,
exit load and tax without a supported disposal pack; no net improvement is claimed.
The baseline retains current holdings and adds all new cash to cash. Stress applies
bounded one-year class shocks; delayed-income new contribution is zero. A volatility
model, dated backtests and independent held-out release evaluation are absent.

AllocationPlan stores all inputs and deterministic outputs. SQL UPDATE triggers
protect saved evidence in migrated SQLite/PostgreSQL databases. New calculations
append records. Reads compare profile, supplied suitability/holdings/assumption
revisions and current source authorization/expiry, returning a separate stale flag.
These internal service inputs must come from owned upstream services; those domain
stores, revision fencing and privacy lifecycle integration remain unfinished.

`output_guard.guard_allocation` drops all model output. No model narrative or model
amount is displayed, and no public eligibility can be supplied by a model. Public
proposals always return gated. Existing named-product flag reader is reused; it
cannot enable allocation publication. No allocation router, chat tool, export,
frontend flow, external market source, execution adapter or public proposal exists.
