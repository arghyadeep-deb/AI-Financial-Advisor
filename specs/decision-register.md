# Owner decision register

Approval to *implement* is recorded separately from approval to *launch*. A working sandbox is not completion of a production feature. Release gates stay in `release-gates.md`.

## 2026-11-07 decisions (owner)

### D04 Tax preparation (feature 004)
- APPROVED scope: one adult resident individual, one employer, salary only, one explicitly supported financial year.
- First historical rule pack: FY2024-25 / AY2025-26. Label it as a historical pack; never present as current-year coverage.
- Required: replace invented slabs/rates with the OFFICIAL rules for that exact period (applicable deductions, rebate, cess, surcharge, rounding, eligibility), or explicitly reject cases outside the implemented scope. Record sources; independently calculated boundary tests; fictional people/test data but real rules.
- Inputs: structured manual only. Form 16 / AIS / 26AS parsing = PENDING (not complete).
- Outputs: JSON for technical use and a readable PDF draft (breakdown, assumptions, evidence, rule-pack version).
- No reviewer appointed. Independent tax review and public-release readiness = PENDING. No invented reviewer approval. Filing stays disabled.

### D05 Allocation (feature 007)
- APPROVED scenario categories: cash, debt, equity, gold; no named products.
- Invented returns/volatility/risk limits are NOT approved for real recommendations; keep only in explicitly labelled synthetic tests.
- Required: versioned assumption register (sources, dates, methodology, uncertainty, expiry). Historical public data is never described as guaranteed future returns.
- 10% cash floor and 36-month rule: configurable, unvalidated prototype assumptions, not universal suitability rules.
- Blanket seven-day liquidity assumption removed. Liquidity depends on instrument, restrictions, settlement; unknown stays unknown.
- No reviewer appointed. Personalised recommendations stay gated. Document parameter validation and the separate public-advice eligibility decision as PENDING.
- Solver, constraint tests, scenarios, explanations continue; execution stays disabled.

### D06 Household privacy (feature 011)
- Account-by-account, READ-ONLY sharing (as feature 011 requires). NOT whole-view sharing.
- Household membership alone grants no access. Summaries, transactions, documents and exports each need their own explicit permission.
- Adult self-declaration for the controlled pilot, recorded as UNVERIFIED. No identity documents collected for this pilot. Production age assurance = unresolved launch decision.
- Ownership percentages stored precisely. Whole-paise allocation uses deterministic largest-remainder with a stable identifier as tie-break, so allocated amounts equal the total exactly. Reject totals above 100%; preserve any unallocated share (never silently redistribute).
- Reminders in-app only. Email deferred.

### Open launch decisions (not decided)
Tax-professional reviewer; allocation parameter validator and public-advice eligibility; production age assurance; providers for 005/013/014.

### Other decisions already taken
Mail: Resend (free tier) behind a provider interface; domain pending. MFA: TOTP, opt-in, `MFA_REQUIRED` flag default off. Deletion receipt: DB-backed throttle. Frontend: after all backend work. CI: GitHub Actions on `integration`.
