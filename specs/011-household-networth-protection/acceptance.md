# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F011-FR01 | T1101, T1105 | FIN-15 totals correct; same asset and ownership shares not double counted. |
| F011-FR02 | T1102, T1103 | Membership alone yields no accounts; expired/replayed invite rejected. |
| F011-FR03 | T1103, T1106 | Grant revoke blocks cached/chat/export access; tax evidence is not implicitly shared. |
| F011-FR04 | T1104 | Policy unknown fields remain unknown; reminder follows confirmed date/preferences. |
| F011-FR05 | T1104, T1105 | Checklist stores minimal flags; no automatic successor access or legal claim. |
| F011-FR06 | T1101, T1105, T1106 | Partial/different-date assets labeled; two household goals cannot use same cash. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
