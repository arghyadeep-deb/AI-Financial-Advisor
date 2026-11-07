# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F008-FR01 | T0801 | Inventory covers each store/processor and notice; optional trace choice distinct from inference. |
| F008-FR02 | T0804, T0805 | Reauthenticated export private; deletion immediately blocks new access and progress is visible. |
| F008-FR03 | T0805, T0807 | Purge interrupted/resumed; restore suppression prevents resurrection; backup expiry truthful. |
| F008-FR04 | T0802 | Recovery replay fails; session reset revokes; auth errors do not enumerate accounts. |
| F008-FR05 | T0806 | Key rotation and least-privilege access tested; privileged access audit has no raw payload. |
| F008-FR06 | T0801, T0803, T0807 | Revocation during queued job denies work/publication; deterministic report survives optional opt-out. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
