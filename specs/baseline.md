# Baseline evidence and reuse decisions

## Scope

The browser walkthrough used one disposable account. The code review inspected AI Advisory at `818b219`, with selected offline tests against temporary data. The VECTOR source and prompt review inspected `62d118693` and isolated selected functions. Live secrets, real customer data, external providers, and production infrastructure were outside those tests. Source paths here are relative to the relevant checkout.

| Finding | Reproduction or source | Owning spec |
|---|---|---|
| Deficit user advised to save ₹27,500 twice and switch nonexistent funds | ₹45,000 income, ₹55,000 expenses, no investments. Reproduced live and with providers disabled. `engines/financial_health_engine.py:277`, `agents/summary_agent.py:153`. | 001 |
| Known default token secret, identical hashes for identical passwords | Auth accepted a forged token locally with no configured secret. `backend/core/config.py:20`, `backend/core/auth.py:9`. Deployed configuration unverified. | 001 |
| Three edit forms ignore changed values | Portfolio, Credit Cards, and Financial Health send only the analysis type. `frontend/app.py:1472`, `:1873`, `:1982`. | 001 |
| Saved changes leave a stale report | ₹65,000 income against ₹55,000 expenses still displayed the earlier ₹10,000 shortfall. Last analysis favors full results over newer quick results. `backend/services/analysis_service.py:78`. | 001 |
| Projection persisted as current value | Health-only run clears stored portfolio value. Rebalancer uses generated allocation as observed. `backend/services/analysis_service.py:47`, `agents/rebalance_agent.py:26`. | 001 and 003 |
| LLM can override facts and failure may look successful | Summary parser accepted a fabricated surplus. All seven fallbacks still returned success. Chat gave SIP instructions during outage and displayed a duplicated turn. `agents/summary_agent.py:107`, `agents/graph_executor.py:117`, `utils/llm_brain.py:377`. | 001 |
| Unknown score becomes 700, tax guesses | `backend/core/dependencies.py:68`, `agents/optimizer_agent.py:39`. Report and optimization figures lacked common context. | 001, 004, 005 |
| Prototype setup and operations | Broken local environments, unpinned dependencies, SQLite default, startup table creation, and no tracked migrations or regression suite at baseline. Browser signup waited while backend woke. | 001 |
| Customer transaction and document pipeline absent | `convert_data_sources.py` converts bundled reference files. Profile models store user-entered aggregates. | 002 and 004 |

## VECTOR pieces

- Adapt ExpenseTracker totals, BudgetAnalyst comparisons, and UPIParser merchant keywords against structured ledger rows. Fix rolling 30-day reporting, zero budgets, missed rupee symbols, and debit misclassification before adapting any existing parser logic.
- Use the Bookkeeper & Controller checklist for evidence and close status. Use FP&A-style narration with verified numbers. Fix the positive-expense-variance labeling and remove implicit 5% monthly growth from household forecasts.
- FinanceSwarm keyword routing picked a generic persona for budget and FP&A in the isolated test. Use explicit LangGraph edges. Keep VECTOR memory, phone access, Obsidian, and raw prompts out of customer workflows.
- For later research, consider read-only StockAnalyst and FundamentalsBot patterns. Reject mock, stale, mismatched-currency, and unavailable data. Missing quotes and fundamentals produced “low” risk in the isolated VECTOR check.
- TaxCalendar is a reminder pattern with fixed dates. Tax Strategist contains US corporate material. Build India-specific source-backed rules. Hold trading desks, execution engines, hedge-fund simulations, and investor personas outside the pilot. VECTOR’s FinAgent wrapper dropped persona settings, and the vendored files carry conflicting local license notices. Verify file provenance before any copying.
- Adapt usage and cost reporting ideas from LLMCostTracker for operations. These metrics stay separate from customer money.

## Product benchmarks

- Fold shows how to handle transfers, refunds, recurring bills, and coverage in a personal finance tracker. SpendSights demonstrates statement upload and category suggestions. Use these as workflow references for 002. [Fold FAQ](https://fold.money/faq) · [SpendSights](https://spendsights.in/)
- INDmoney distinguishes actual external holdings, current value, and returns. ET Money Genius illustrates explicit risk and time-horizon inputs. Use these as product references for 003. [INDmoney holdings](https://www.indmoney.com/mutual-funds/track-mutual-funds) · [ET Money Genius](https://www.etmoney.com/help/genius/about-genius/what-is-genius)
- ClearTax and TaxCloud show document intake, review, and reconciliation patterns. Use these for 004, with an autonomous draft workflow for supported cases. [ClearTax filing guide](https://cleartax.in/s/cleartax-itr-filing-guide) · [TaxCloud](https://cleartax.in/taxcloud)
- CIBIL’s dated reports, alerts, and dispute links establish how to present bureau data. Use the official routes for 005. [CIBIL alerts](https://www.cibil.com/cibil-alerts) · [CIBIL dispute FAQ](https://www.cibil.com/contact-us-faq)

## Version 2 planning update (2026-11-05)
The original evidence above remains a historical assessment, not a fresh scan of current code or live app. This update reviewed the 23 v1 planning documents and their 45 tasks and compared vendor-documented capabilities. Added feature packages close planning gaps; they do not claim any defect is fixed. See [market comparison](market-comparison.md), [financial rules](financial-rules.md) and [agent role map](agent-role-map.md). Missing v1 requirements included full budgeting/goals, constrained allocation, evidence-aware reversal, account lifecycle, operational targets, UX, household permissions, research governance and broader parser coverage.
