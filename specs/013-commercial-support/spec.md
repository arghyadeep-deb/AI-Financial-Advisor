# Feature specification — Commercial readiness, subscriptions and customer support

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: Optional R4; no billing required for pilot. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Understand a paid plan.** User sees limits and price before checkout and can cancel without losing the ability to export/delete personal data.
- **US2 (P1) Handle payment uncertainty.** Repeated or out-of-order provider events do not create duplicate subscriptions or inconsistent access.
- **US3 (P2) Get help safely.** User can report a processing issue using a request ID; support sees only necessary metadata.

## Functional requirements
### F013-FR01 — Business decision
Define free/pilot/paid tiers, unit economics, supported geography, trials, grace periods, refund policy and tax/invoice obligations before checkout implementation. No affiliate ranking influence hidden inside financial outputs.

### F013-FR02 — Billing adapter
Use hosted provider checkout; no card storage. Verify signed events, event IDs, payload digest and subscription ownership. Reconcile unknown outcomes with provider state; out-of-order cancellation/payment events follow an explicit transition table.

### F013-FR03 — Entitlements
Server-enforced capability and quota checks. Downgrade preserves history and access to export, deletion and essential account controls. Paid subscription never overrides advice, consent or correctness gates.

### F013-FR04 — Support workflow
Ticket statuses, severity, response target and safe attachment consent. Internal tooling uses least privilege and audit. A support retry uses the normal job service; no ad hoc edits of financial rows.

### F013-FR05 — Transparency
Publish supported-bank matrix, known limitations, contact and incident status. Distinguish service downtime from missing or unsupported user evidence. Communicate model/provider changes that materially affect data processing.

### F013-FR06 — Product analytics
Collect minimal event names and funnel counts with documented retention/choice; never transaction descriptions, documents or financial values in analytics. Measure report completion, corrections, retention and cost, not speculative financial outcomes.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
