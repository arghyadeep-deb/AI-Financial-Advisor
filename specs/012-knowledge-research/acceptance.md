# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F012-FR01 | T1201 | Unlicensed/unapproved/expired source excluded; source hash/effective date recorded. |
| F012-FR02 | T1202, T1206 | Irrelevant citation cannot support claim; tenant retrieval cannot cross owner. |
| F012-FR03 | T1203 | Education request cannot mutate data or unlock personal recommendations. |
| F012-FR04 | T1204 | Instrument/period/currency mismatch and missing fundamentals never generate low risk. |
| F012-FR05 | T1205 | DCF/bond/ratios match independent fixture; assumptions and statement basis visible. |
| F012-FR06 | T1201, T1206 | Held-out injection, source expiry and corrections invalidate affected claims; release gate enforced. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
