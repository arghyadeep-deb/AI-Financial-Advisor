# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F006-FR01 | T0601, T0602 | Budget edits versioned; zero budget and overspend work; splits total exactly. |
| F006-FR02 | T0603 | Three occurrences yield candidate only; annual/variable false positive not auto-confirmed. |
| F006-FR03 | T0601, T0604 | Past deadline and inflation assumptions visible; two goals cannot spend same reserve. |
| F006-FR04 | T0605 | Independent payoff schedule with fees; missing/floating rate and negative amortization labeled. |
| F006-FR05 | T0604, T0605, T0607 | FIN-01 cap zero; reserve/debt obligations counted once; impossible goals show shortfall. |
| F006-FR06 | T0606, T0607 | Opt-out suppresses reminders; recurring payment replay produces one settlement/notification. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
