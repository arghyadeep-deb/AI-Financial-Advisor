# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| FR-001 | T401, T407 | Only chosen period/regime/person scope accepted; adjacent period never silently mixed. |
| FR-002 | T402, T403, T408 | Identity and income/withholding conflict requires evidence-backed review. |
| FR-003 | T404, T407, T408 | Boundary cases independently calculated for supported rules; unsupported income stops computation. |
| FR-004 | T405, T406 | Export says draft with source/pack; no official acknowledgment or filing action. |
| F004-FR05 | T407 | Input support matrix has explicit supported/excluded cases and form versions. |
| F004-FR06 | T407, T409 | Every statutory parameter maps to official period source and independently checked boundary. |
| F004-FR07 | T408 | Disagreement between sources is surfaced; correction preserves originals. |
| F004-FR08 | T405, T409 | New rule pack/source revision marks prior draft stale; unsupported regime comparison unavailable. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
