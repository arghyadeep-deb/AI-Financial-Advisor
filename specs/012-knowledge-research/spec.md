# Feature specification — Financial education, evidence retrieval and research agents

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: R2 education; R3 research independently gated. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Ask a basic question.** User asks what an EMI means and gets a simple explanation; a personal numerical answer uses owned verified data.
- **US2 (P1) Inspect a company.** A research view shows source-dated fundamentals, assumptions and missing fields without converting absent data into low risk.
- **US3 (P2) Recognize stale guidance.** Expired tax or product information is excluded from current claims and the system explains the limitation.

## Functional requirements
### F012-FR01 — Knowledge registry
Allowlisted official/reference sources with URL, title, fetched/published/effective dates, jurisdiction, license, content hash and expiry. Separate general knowledge from private documents; tenant filters apply to any private index. New source ingestion is reviewed and versioned.

### F012-FR02 — Grounded answers
Every factual research claim maps to evidence; source relevance is checked, not just presence of a URL. Conflicts and missing current data lead to qualified/unavailable output. Retrieved text is untrusted and cannot change system instructions or invoke tools.

### F012-FR03 — Education scope
Plain-language glossary and worked examples on budgeting, debt, risk and tax document meanings. Distinguish generic education, user-selected hypothetical calculation and personalized recommendation; the policy engine gates each output consistently across chat and reports.

### F012-FR04 — Research scope
Read-only company and bond research after data licensing and release review. Exact instrument ID, exchange, currency, reporting period, units, restatement flags, source availability and price date required. No default low-risk rating on missing data. Creditworthiness of an issuer is distinct from a personal bureau score.

### F012-FR05 — Models and valuation
Financial statement ratios, DCF or bond scenario tools expose definitions, forecasts, discount assumptions and sensitivity. Validate units and fiscal periods. No target price from model prose alone. Do not mix consolidated and standalone statements without explicit choice.

### F012-FR06 — Lifecycle and evals
Track knowledge version and invalidate affected claims on correction/expiry. Evaluate retrieval, evidence entailment, numerical grounding, prompt injection and abstention on held-out questions. Research publication and named recommendations have separate release gates; no execution.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
