# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| FR-001 | T301, T302, T307 | Units x dated price matches independent value; repeated import does not duplicate position. |
| FR-002 | T303, T308, T309 | Missing/stale price is unavailable/partial; no fabricated return without basis. |
| FR-003 | T304, T305 | User scenario uses same immutable holdings and contribution capacity; hypothetical label persists. |
| FR-004 | T306, T310 | Named-security advice flag blocks API/chat/export; no execution path. |
| F003-FR05 | T307 | Manual/imported same account instrument reviewed; closure/corporate action incomplete state explicit. |
| F003-FR06 | T308 | Dated-flow return matches independent calculation; no/multiple roots not a fabricated XIRR. |
| F003-FR07 | T309 | Expired quote and currency/exchange mismatch rejected; corrected price invalidates snapshot. |
| F003-FR08 | T310 | 007/011 consume same source date/ownership, without projected value or double counting. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
