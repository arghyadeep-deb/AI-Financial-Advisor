# Market comparison and resulting scope

Research date: 2026-11-05. These are vendor-documented capabilities, not independent tests of their quality, performance or current user eligibility. Availability may vary by account, institution and plan. Recheck at implementation. Our baseline column refers to the previously reviewed prototype and v1 specs; this update did not retest the current app. Proposed differentiation is our design judgment.

| Reference and observed capability | Gap in the v1 plan | Our requirement |
|---|---|---|
| [Fold FAQ](https://fold.money/faq): transaction categorization, own-account transfers, partial refunds, recurring bills, read-only connections and export | Ledger foundation existed, but split expenses, refund remainder and recurring-bill behavior were underspecified | 002 accounting examples; 006 confirmed bills and split budgets; 014 format expansion |
| Fold explicitly says budgets are not yet available in its FAQ | Do not describe Fold as proof of delivered budgeting | Use YNAB as the budgeting reference |
| [YNAB features](https://www.ynab.com/features): targets, loan planning, reports, sharing and cross-device access | Goals/debt payoff and user experience largely absent | 006 budget and goals; 010 responsive UX; 011 sharing. Do not infer Indian bank support from YNAB's import claim |
| [INDmoney net worth](https://www.indmoney.com/networth): assets/liabilities, external holdings, goals and return comparison | Holdings scenarios alone are narrower | 003 performance; 006 goals; 011 ownership-aware net worth |
| [INDmoney family accounts](https://www.indmoney.com/networth/family-accounts): individual and combined views | No scoped sharing model | 011 explicit account grants, revocation and joint ownership |
| [ET Money Genius](https://www.etmoney.com/help/genius/about-genius/what-is-genius) and [portfolio descriptions](https://www.etmoney.com/help/genius/about-genius/what-are-the-different-portfolios-offered-under-genius): allocation and risk/time-horizon differentiated portfolios | Actual allocation planning deferred entirely | 007 constrained, versioned proposals with independent suitability gate; do not copy claimed returns or promise downside protection |
| [ClearTax product help](https://docs.cleartax.in/product-help-and-support/for-individuals/file-itr/file-itr-on-cleartax): document intake and tax preparation workflow | Tax outline lacks an explicit supported-input matrix and period release process | 004 exact scope, evidence reconciliation and annual rule-pack review; 005 filing remains distinct |
| [CIBIL disputes FAQ](https://www.cibil.com/faq/loan-rejections-disputes): dispute status and lender confirmation for corrections | Credit score alone is insufficient context | 005 dated observations, report discrepancies and user-controlled official dispute handoff; no promise that the app changes a bureau record |

## Deliberate additions beyond imitation
Evidence drill-down, safe partial reports, deterministic amounts during AI outages, import reversal, explicit affordability and account deletion are acceptance requirements even when a vendor page does not discuss them. They are engineering/product decisions, not claims about competitors' weaknesses.

## Coverage map
| Customer need | Spec owner | First delivery |
|---|---|---|
| Trust the numbers and sign in securely | 001 | R0 |
| Upload, reconcile, correct and export monthly activity | 002 | R1 |
| Track portfolio and calculate supported performance | 003 | R2 |
| Organize tax evidence and draft supported computation | 004 | R3 |
| Credit reports and authorized synchronization | 005 | Manual early; connections R4 |
| Budgets, recurring bills, goals, reserves and debt scenarios | 006 | Core R1; full R2 |
| Portfolio allocation from verified personal constraints | 007 | R3, independently gated |
| Consent, account lifecycle and deletion | 008 | Before real data |
| Reliability, deploy/restore, alerts and costs | 009 | Before real data |
| Accessible onboarding, responsive screens and feedback | 010 | Core R1 |
| Household net worth and insurance inventory | 011 | Optional R2 |
| Evidence-backed education and research | 012 | Education R2; research R3 |
| Paid plans, support and entitlements | 013 | Only if commercialization chosen |
| More banks, scanned/protected documents and cash corrections | 014 | Format-by-format R2 |

This is a capability roadmap, not market parity certification. Native mobile apps, payments, brokerage execution, insurance sales, institutional portfolio management, GST/business books and M&A are separate products or future amendments. They are not implied by completion of this roadmap.
