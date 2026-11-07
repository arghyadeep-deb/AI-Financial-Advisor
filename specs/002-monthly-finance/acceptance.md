# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| FR-001 | T201, T203, T205 | Supported text layout accepted; corrupt/scanned/protected/unsupported input gives exact state. |
| FR-002 | T202, T203, T204 | Second user cannot access rows, pages, review, job or download; expiry honored. |
| FR-003 | T205, T207, T216 | Opening 1,000 +500 -200 =1,300; 1,299 closing blocks verified status. |
| FR-004 | T207, T208 | Same bytes repeat; overlap with identical genuine transactions; review ambiguity without losing rows. |
| FR-005 | T209, T216 | Own transfers and card repayments counted once; partial refund and one-sided coverage stay explicit. |
| FR-006 | T211, T212, T216 | Calendar month and account scope stable; row drill-down reproduces every metric and export. |
| FR-007 | T206, T207, T210, T217 | Crash before/after commit and repeated resume never duplicates posting. |
| FR-008 | T213, T214 | Injected instructions and bogus category/amount rejected; model outage retains deterministic report. |
| F002-FR09 | T216 | All FIN-01..16 expected metrics and missing-data cases. |
| F002-FR10 | T207, T210, T217 | Every reversal/cancel/reprocess contract case including surviving evidence and invalid links. |
| F002-FR11 | T218 | Concurrent change to either of two accounts or a transfer link invalidates current publication. |
| F002-FR12 | T219 | Budget 5,000/spend 5,500 shows 500 overspend; confirmed recurring bill tracked. |
| F002-FR13 | T203, T206, T215, T220 | Scanner unavailable quarantines; stale worker cannot publish; private page retrieval reauthorizes. |
| F002-FR14 | T201, T219 | Debit-account-only adapter never claims card-statement support; canonical card tests remain valid. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
