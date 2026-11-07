# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F010-FR01 | T1001, T1002 | Novice can use isolated demo and find supported formats before upload. |
| F010-FR02 | T1001, T1003 | Empty/error/stale/review screens show next action; conflicting edit preserves draft. |
| F010-FR03 | T1004 | Core flow tested at 360/768/1440px, keyboard and assistive-technology smoke. |
| F010-FR04 | T1002, T1006 | Glossary readable; any Hindi/Hinglish release has canonical amount/source parity. |
| F010-FR05 | T1005 | Quiet hours, unsubscribe, verified channels and event replay behave as chosen. |
| F010-FR06 | T1006 | Observed novice completion result and issues recorded; feedback upload requires consent. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
