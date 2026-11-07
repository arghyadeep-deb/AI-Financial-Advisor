# Portfolio arithmetic and owned observations

`portfolio-metrics.v2` uses exact units (eight decimal places), integer paise,
source/version, quote date and expiry. Aggregate rational values are rounded
half-even once. Class/issuer amounts use largest remainders (ties by string key)
to conserve the rounded total. The same security may occur in distinct accounts;
duplicate account/instrument observations require explicit review.

`backend/services/portfolio_service.py` owns confirmed full-book revisions.
An edit replaces the complete book, preserving history. CSV is a bounded text
preview of the header in `CSV_COLUMNS`, followed by explicit owner confirmation.
It does not accept binary documents, parse bank flows or infer instrument units.
Quotes and ownership remain **owner_confirmed_unverified** even if arithmetic is
complete. A book from another date is stale; its dated subtotal remains inspectable
but its current total is unavailable. Missing/future/expired/foreign quotes never
become zero. Price/source licensing and per-asset market calendars remain absent;
the caller declares quote expiry. No verified net-worth eligibility is asserted.

Absolute gain needs cost basis and explicit corporate-action support. Observed
books do not contain performance histories, so their XIRR/TWR/benchmark stay null.
`returns.py` separately accepts explicit dated flows: conventional ACT/365 XIRR
uses bounded Decimal bisection, and end-flow TWR compounds exact fractions.
Nonconventional sign patterns, multiple-root possibilities, missing action support
and roots outside the documented domain are unavailable. No cash flow or terminal
valuation is inferred. Benchmark data, histories and market feeds remain disabled.

Portfolio shocks/contributions are hypothetical, read-only, and distinct from
affordability. Allocation consumes owned snapshots through its existing solver;
shared planning capacity handles existing commitments, reserves and goal funding.
Named recommendations, filing, trades and execution are disabled.
