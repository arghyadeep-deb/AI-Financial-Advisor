# Partial portfolio arithmetic, feature 003

`portfolio-metrics.v1` accepts normalized unique INR instrument observations,
exact units (8 decimal places), integer paise quotes, source/version, date and
explicit expiry. The caller owns approval, licensing, per-asset market calendars,
ownership and observation deduplication. Duplicate instruments fail closed here;
multi-account consolidation requires the future owned holdings service.

Unknown/stale/future/foreign quotes leave a priced subtotal and unavailable total;
no price fallback. Aggregate exact rational values before half-even paise rounding.
Rounded class/issuer display subtotals may differ by a paise from the rounded total.
Issuer HHI is exact sum of squared issuer shares; unknown issuer or partial prices
leave HHI unavailable. Largest known issuer share is explicitly over priced assets.
Neither concentration nor missing coverage constitutes a low-risk claim.

Absolute gain requires complete prices, cost bases and explicit corporate-action
support. XIRR, TWR, benchmark, volatility estimation and performance histories stay
unavailable; dated-flow solvers and multiple-root validation remain unimplemented.
Shocks are hypothetical and never replace observed values. No database, API,
ingestion, named proposals, market feed or execution integration is included.
