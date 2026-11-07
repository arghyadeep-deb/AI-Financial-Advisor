# Synthetic allocation fixture v1

These invented INR asset-class bounds, fees and shocks test arithmetic only.
They describe no investible product, licensed price or production-approved advice.
All assumptions share the date, owner, expiry and hashed source in the pack.
The registry is the only source authorization boundary. Test approval of the
example.test source is restricted to offline synthetic use. The production
catalog is empty. No expected return is inferred from prose.

## Illustrative v2 (awaiting owner approval)

`synthetic-v2.json` adds gold, with invented annual return and volatility in basis
points, annual fees, liquidity days, weight bounds and one-year adverse/favourable
shocks for each class. All fields inherit the pack's explicit effective date,
expiry, owner and exact hashed source file. These are illustrative assumptions,
not prices, forecasts, verified liquidity or an approved recommendation universe.
No named instrument is accepted by the closed class enum. All four classes are
INR scenario buckets; no FX conversion, leverage or shorting is supported.

The transparent allocator uses weights/constraints rather than maximizing the
illustrative return. Volatility is disclosed as an input; there is no covariance
model or probabilistic risk claim. Keep production registry empty, public gate
false and sandbox off by default. A missing, tampered, corrected, unapproved,
not-yet-effective or expired registry source fails closed. Retain v1 for historical
regressions; do not rewrite old immutable plans. Owner must approve parameters,
freshness, source rights and applicability before any release.
