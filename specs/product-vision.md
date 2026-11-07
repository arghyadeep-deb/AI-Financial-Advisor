# Product vision and scope decisions

Version 2.1 · Planning only · 2026-11-05

## What we are building
An India-first personal finance workspace that explains what happened to a person's money, checks the evidence, and helps them plan their next month and longer-term goals. A user can upload supported documents, correct errors, track assets and debts, compare scenarios, and prepare supported tax drafts. The experience must work for someone unfamiliar with finance. An automated workflow handles routine processing; uncertainty becomes a clear question or unavailable result rather than an invented answer.

The first audience is adults with INR bank accounts and straightforward household finances. The first tax audience is a separately defined salaried-resident case. Business accounting, international tax, minors, estate administration and institutional investing are outside the initial product. Do not silently accept these as supported cases.

## User journey
1. Understand supported banks/documents and privacy choices before signup or upload.
2. Create an account, choose a goal, and use a fictional demo or add their own accounts.
3. Upload statements; see processing, coverage and any corrections required.
4. Open a monthly report: money earned, money spent, debt payments, investments, transfers and unexplained movements.
5. Set a budget, confirm bills and see a practical plan based on available money.
6. Add holdings and debts; inspect net worth and goals without counting the same asset twice.
7. Compare investment scenarios and eligible allocation proposals when that feature is approved.
8. Build a tax evidence pack for supported cases; inspect every assumption.
9. Manage sharing, exports, notifications, consent and deletion from one settings area.

## Positioning and product promises
Compete on verifiable amounts, understandable explanations, privacy and correction/recovery—not a claim to outperform markets or replace every finance profession. Every number has a source, computation or explicit assumption. Every recommendation says why it is relevant, what evidence is missing, and when it becomes stale. A successful graph run alone is not a successful financial result.

No mandatory CA/CFA is inserted into the routine supported user journey. Users review ambiguous inputs themselves. An AI persona does not hold professional credentials. Product owners must establish applicable permissions before regulated advice, research distribution, certification or filing is offered. Unsupported cases stop with a useful checklist or user-controlled export. Disclaimers alone are not a release control.

## Scope ladder
| Release | Scope | Dependencies and explicit exclusions |
|---|---|---|
| R0 internal stabilization | 001 plus synthetic evaluation and basic operation controls | No claim of production readiness |
| R1 controlled monthly pilot | 002; core 006 budgets; 008 privacy; 009 pilot operations; 010 core UX | One bank text-PDF and CSV; no live links, optimization or filing |
| R2 personal planning beta | 003 holdings; full 006 goals/debt; 014 approved import formats; optional 011 | Each feature enabled only after its acceptance evidence |
| R3 advanced modules | 004 supported tax drafts; 007 allocation; 012 research | Independently scoped; advice and research gates apply |
| R4 connected/commercial | Selected 005 integrations and 013 billing/support | Partner authorization, operational capacity and pricing decision |

These are decision stages, not a delivery schedule. Numbered directories are capability IDs, not a strictly sequential implementation order. No task authorizes implementation until the user chooses it.

## Definition of good
A pilot user can upload a supported statement, understand an exception, inspect accurate totals, correct a category, set a budget and export a reproducible report without developer assistance. The system rejects another user's data, recovers from restart, stays useful during model outage, and honors deletion. A later allocation plan must fit cash flow and goals. Track activation, successful reconciled reports, correction burden, repeat monthly use, evidence comprehension and cost per completed report. Do not optimize only for chat volume.
