# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F013-FR01 | T1301 | Pricing/tier/refund/support policy decided before live checkout; conflicts disclosed. |
| F013-FR02 | T1302, T1306 | Signed duplicate/out-of-order events and timeout reconcile provider state exactly once. |
| F013-FR03 | T1303 | Downgrade retains export/delete and history; client cannot grant entitlement. |
| F013-FR04 | T1304 | Support request lookup audited; raw evidence access separately authorized. |
| F013-FR05 | T1301, T1304 | Known formats/limitations/contact match actual scope; outage explanation accurate. |
| F013-FR06 | T1305, T1306 | Analytics capture contains events/counts only; opted-out processing and retention honored. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
