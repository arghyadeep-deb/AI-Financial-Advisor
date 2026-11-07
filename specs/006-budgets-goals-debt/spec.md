# Feature specification — Budgets, recurring bills, goals and debt planning

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: R1 core budgets; R2 full planning. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Budget a month.** Given a 5,000 grocery budget and 5,500 recognized grocery spending, show 500 overspend. Editing next month does not rewrite the prior month.
- **US2 (P1) Plan irregular commitments.** Given an annual premium and irregular salary, show explicit monthly earmarks and assumptions without claiming a future deposit is guaranteed.
- **US3 (P2) Compare debt and savings goals.** Given two goals and debt minimum payments, distribute only available capacity; an impossible deadline is shown as a shortfall, not solved by invented returns.

## Functional requirements
### F006-FR01 — Versioned budgets
Store owner, calendar month, category, allocation, rollover policy, revision and currency. Support create/edit/archive, copy-forward preview and split categories. Default no rollover; opt-in positive rollover is explicit; overspending is not silently hidden.

### F006-FR02 — Recurring bills
Detect candidates from at least three dated occurrences with merchant normalization, cadence and amount tolerance. A candidate never creates a confirmed obligation until user acceptance. Support variable amounts, annual bills, pause, paid matching and deletion; one transaction cannot settle two obligations.

### F006-FR03 — Goals and emergency reserve
Store target amount in present/future value terms, target date, priority, funding account and allocated amount. Show inflation and return assumptions separately. Reserve months and eligible essential expenses are user-set with an explained default; do not mandate one universal number.

### F006-FR04 — Debt calculator
Store outstanding principal, rate type, compounding/payment convention, minimum payment, fees, term and evidence date. Compare user-selected avalanche/snowball/extra-payment scenarios including prepayment assumptions. Missing terms produce an incomplete estimate; no loan approval or promised interest saving.

### F006-FR05 — Capacity and priorities
Use the shared affordability service and unique obligation IDs. Total earmarks and goal contributions cannot exceed available capacity. Suggest adjusting date, target or spending when infeasible; no borrowing recommendation generated to fill the gap.

### F006-FR06 — Explain and alert
Show planned versus actual, source coverage and why changes occurred. Confirm reminder preferences; dedupe reminders and avoid sensitive lock-screen content. Use 009 scheduler and 010 notification states.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
