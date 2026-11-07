# Implementation plan — Tax preparation agent

Depends on 001 security and 002 document ownership and review components. Read the [spec](spec.md) and [agent controls](../agent-quality.md).

Use the existing private upload and worker pattern with isolated tax document types. Add source-field extraction and comparison under `backend/finance/tax/`; rules under a documented versioned `engines/tax/` interface. Add an owned tax case, document field evidence, rule-pack version, and immutable calculation snapshot. Store only required identity data. Keep a tax reviewer UI separate from bank categorization. Pause the workflow for conflicts and unsupported cases. The model may describe the completed draft and missing items from allowlisted facts. Code determines scope and all amounts.

Constitution check. Every rule cites the source and effective period. Use golden examples that exercise boundaries and unsupported cases. Remove remaining legacy income-band tax savings from all public views before releasing a calculator. Tax Draft never calls a portal, sends documents externally, or invokes a certification flow. Roll back by disabling the rule pack or draft feature and retaining existing immutable results for review.

## Shared implementation contracts
Read [architecture](../architecture.md), [financial rules](../financial-rules.md), [implementation order](../implementation-order.md), [evaluation plan](../evaluation-plan.md) and [release gates](../release-gates.md). Use shared snapshot and privacy services. Implement only the selected slice. Module paths are proposed boundaries; document any adjustment without weakening acceptance. Complete [acceptance mapping](acceptance.md) with actual test evidence.
