# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F014-FR01 | T1401, T1404 | Registry accurately distinguishes supported text/card/OCR/password layouts. |
| F014-FR02 | T1402 | Scanner timeout, decompression bomb, parse timeout and no-network isolation tested. |
| F014-FR03 | T1405 | Password not persisted in graph/logs/DB/temp outputs; unsupported default explicit. |
| F014-FR04 | T1405 | Low-confidence digit pauses; no balance-forcing repair; external OCR consent enforced. |
| F014-FR05 | T1403 | Manual cash/split/import match conserves paise without double counting. |
| F014-FR06 | T1404, T1406 | Held-out layout family and rollback/reprocess preserve original snapshot and evidence. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
