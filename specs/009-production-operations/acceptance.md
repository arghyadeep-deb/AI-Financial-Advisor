# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F009-FR01 | T0901 | Reproduce clean deploy/upgrade/rollback; unsafe production config denied. |
| F009-FR02 | T0902 | Lease expiry, stale worker, atomic outbox and active-upload cleanup races exercised. |
| F009-FR03 | T0905, T0907 | Record actual load hardware/fixtures against approved p95/concurrency limits; no invented pass. |
| F009-FR04 | T0903, T0907 | Quota exhaustion bounds retries/cost and preserves existing report access. |
| F009-FR05 | T0904 | Inject queue lag/exporter failure; alert has owner/action and no financial payload. |
| F009-FR06 | T0906, T0907 | Timed restore reconciles rows/balances/deletions; parser flag rollback preserves history. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
