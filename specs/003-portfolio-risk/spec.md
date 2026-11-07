# Feature specification — Portfolio tracking and risk

**Suggested branch** `003-portfolio-risk` · **Status** Proposed; awaiting user selection

## User stories and independent acceptance

- **US1 (P1) View observed holdings.** Import one documented holdings CSV or enter positions manually. Given valid units and a dated price in the correct currency, show observed value and allocation. Given missing or stale prices, show coverage and unavailable values.
- **US2 (P2) Compare a user-selected scenario.** Given a hypothetical contribution or a market shock selected by the user, show the change in mix, cash need, and scenario assumptions. A verified monthly shortfall prevents the UI from presenting a positive contribution as affordable. A hypothetical scenario can still be labeled as such.
- **US3 (P2) Understand concentration.** Show exposures by available asset class and issuer. Label the share of holdings that cannot be classified. Explain how each concentration value was calculated.

## Functional requirements

- **FR-001** Store owner, source, instrument ID, units, currency, dated valuation and optional cost basis. Distinguish holdings as of a date from transactions and projections. Import is idempotent and reviewable. Support one INR asset scope for the pilot.
- **FR-002** Never substitute mock data, assumed prices or zero for missing prices. Include valuation source, date, coverage and stale status. Return and tax metrics require adequate dated cost and transaction evidence.
- **FR-003** Calculate allocation and concentration in code. Scenario results are deterministic, versioned and read-only. Separate chosen assumptions from observed data and report affordability against the selected verified cash-flow snapshot.
- **FR-004** Put named security recommendations and any execution capability outside this release. Route chat to the same owned facts and scenario contract.
- **F003-FR05** Track instrument identity, account/folio, ownership and observation date. Distinguish current observation from transaction-derived position; conflicting sources require review. Corporate actions, distributions, fees and closures need explicit support or incomplete flags.
- **F003-FR06** Define absolute gain, XIRR and optional time-weighted return with evidence prerequisites. Cost basis missing means gain unavailable. Benchmark uses comparable dates/cash flows/currency and source. XIRR failures/multiple roots are explicit.
- **F003-FR07** Source data licenses, freshness and stale market days must be configured per asset. Missing quotes never become zero or low risk. Corporate-action unsupported periods cannot imply complete performance.
- **F003-FR08** Feed owned dated snapshots to 007 allocation and 011 net worth. No duplicate manual/imported holding or joint ownership double count. Raw bank outflow cannot establish units purchased.

## Success criteria

- **SC-001** Golden portfolios test units, exact values, repeated imports, missing price, partial holdings, and concentration. Health-only analysis preserves holdings and valuation.
- **SC-002** A ₹10,000 shortfall produces zero verified discretionary contribution. A user-selected hypothetical scenario remains distinct from affordable amounts.

Read [implementation order](../implementation-order.md) for build prerequisites and release gates. See [acceptance mapping](acceptance.md) for requirement-to-task evidence.
