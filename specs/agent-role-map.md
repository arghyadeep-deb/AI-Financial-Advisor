# Agent responsibilities, reuse and finance job-role coverage

Agents are bounded workflows/tool users, not licensed professionals. Do not create one free-roaming agent for every job title. Separate arithmetic, evidence, user interaction and release policy; multiple personas do not provide independent verification if all repeat the same model output.

| Component | Inputs and tools | Output / restrictions | Spec |
|---|---|---|---|
| Intake/reconciliation workflow | Owned document IDs; parser, balance and dedupe services | Verified rows or review items; no network in parser, no inferred money | 002/014 |
| Budget/goal planner | Ledger snapshots, user budgets, obligations and goals | Feasible monthly plan and shortfalls; cannot move funds | 006 |
| Portfolio/risk planner | Observed holdings, prices, suitability and constraints | Tracking, scenarios and gated allocation drafts; no orders | 003/007 |
| Tax preparation workflow | Period-specific fields, deterministic rule pack | Supported draft, evidence conflicts or checklist; no certification | 004 |
| Credit explainer | Dated user/provider observations and debts | Explain fields and official dispute route; no invented score/loan approval | 005 |
| Education/research assistant | Approved retrieval, statement/valuation tools | Sourced education or gated research; no unsupported buy/sell claim | 012 |
| Explanation validator | Typed canonical results and source map | Reject unsupported facts; deterministic template on failure | All |
| Operations supervisor | Metadata metrics, queue and spend status | Retry permitted jobs, alert operator; cannot alter financial truth | 009 |

## Requested profession coverage
| Job role | Useful capability here | Disposition |
|---|---|---|
| Equity Research Analyst | Sourced company statements, ratios and scenarios | Optional 012; named recommendations gated |
| Investment Banking Analyst | Capital raising and acquisition structuring | Outside household product; separate business-finance scope |
| Financial Analyst | Household cash flow and optional company ratio analysis | 002/006; company research 012 |
| Portfolio Manager | Allocation monitoring and proposal generation | 003/007; no discretionary asset management |
| Asset Management Analyst | Exposure, performance and risk analysis | 003/007; no managed-account authority |
| Wealth Management Analyst | Goals, assets, debts, household planning | 006/011; complex estate work excluded |
| Investment Advisor | Suitability and constrained personalized drafts | 007 behind independent applicability/release gate |
| Risk Analyst | Concentration, liquidity and stress scenarios | 003/007; uncertainty explicit |
| Credit Analyst | Debt affordability and credit report explanation | 005/006; not underwriting or promised loan eligibility |
| Valuation Analyst | Transparent valuation assumptions and sensitivity | Optional 012 |
| Financial Modelling Analyst | Goal, debt and company scenario engines | 006/007/012 depending on evidence |
| M&A Analyst | Acquisition analysis | Outside initial product |
| Fixed Income Analyst | Bond cash-flow and rate/credit scenarios | Optional 012; require terms, price, issuer evidence |
| Private Equity Analyst | Private-company diligence | Outside initial product; data/confidentiality needs distinct scope |
| Fund Manager | Fund-level execution and mandate management | Outside product; read-only household allocation is not fund management |

## VECTOR reuse policy
The historical source assessment is in [baseline](baseline.md). Reuse ExpenseTracker/BudgetAnalyst arithmetic ideas only after exact-money/zero-budget tests; merchant keyword rules are hints, not authoritative categorization. Use Bookkeeper evidence checklist and FP&A explanation patterns with corrected expense variance. Do not import broad VECTOR memory, phone access, unrestricted routing or trading agents. FinAgent configuration/provenance and vendored license conflicts must be resolved before copying code. Missing market data cannot imply low risk. Create an adaptation record per copied file: source revision, license, changes and independent tests. No claim is made that every current VECTOR file was reread in this update.

## Agent handoff envelope
Each node receives owner context established by trusted code, resource IDs, expected revisions, allowed tool set, bounded budget and schema version. It returns typed facts/references/status, never hidden permissions. Tool services reauthorize independently. Node outputs are validated before persistence/publication. Broad shared conversational memory is prohibited; purpose-specific memory has expiry, source provenance and deletion support.
