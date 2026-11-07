# Allocation assumption register (D05)

`register-v1.json` records the configurable cash-floor and near-term prototype
policies. Each entry has an id, version, value, source name/URL/publisher, as-of
date, methodology, uncertainty, expiry and status. Both are
`unvalidated_prototype`. The source is the repository owner decision, not an
external empirical study. Parameter validation is PENDING; no reviewer appointed.
The separate public-advice eligibility decision is also PENDING.

All invented returns, volatility, risk caps, bounds, fees and shocks are confined
to `tests/fixtures/allocation/`, explicitly `synthetic_test`, with a per-scalar
register. The loader refuses those files outside APP_ENV=test. Production source
registry remains empty. Historical public data never guarantees future returns.
No validated market or suitability parameters are supplied.

Liquidity defaults to unknown for every class, including cash. A duration requires
instrument, restriction, settlement, source and dated unexpired evidence. No class
label establishes liquidity. Unknown liquidity cannot meet a requested deadline.
Immutable old plans remain readable as historical receipts and require revalidation;
never rewrite user history to retrofit the register.
