# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| FR-001 | T501, T502, T507 | Missing limit/score unavailable; stale user-reported observation visibly dated. |
| FR-002 | T503, T506 | No credentials or live requests until per-provider readiness; revoked scope blocks fetch. |
| FR-003 | T504, T508, T509 | Duplicate/out-of-order signed events reconcile once; wrong owner denied. |
| FR-004 | T503, T505, T506, T510 | Provider eligibility and permitted action documented; portal password never reaches agent. |
| F005-FR05 | T507 | Different bureau scales stay separate; dispute handoff makes no correction promise. |
| F005-FR06 | T508 | PDF and sync corroborate same row; revocation after fetch prevents commit. |
| F005-FR07 | T509 | Timeout after submission becomes outcome_unknown then status query, not resubmission. |
| F005-FR08 | T505, T510 | Consent for reading does not authorize filing; provider outage retains manual reports. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
