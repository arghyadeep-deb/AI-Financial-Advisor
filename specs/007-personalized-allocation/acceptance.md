# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| F007-FR01 | T0701 | High tolerance/short essential horizon creates conflict; missing answers block proposal. |
| F007-FR02 | T0702, T0707 | Out-of-universe/stale price excluded; public proposal denied while feature gate off. |
| F007-FR03 | T0703 | Infeasible bounds return reason; rounded allocation preserves money and no-leverage limits. |
| F007-FR04 | T0704 | No cost basis means unknown tax cost, not tax-saving claim; contribution-first alternative shown. |
| F007-FR05 | T0705, T0706 | Same assumptions produce same plan; adverse/held-out scenarios and baseline comparison recorded. |
| F007-FR06 | T0705, T0707 | Source revision change marks plan stale; API/chat/export cannot trade or bypass release gate. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.

## D05 evidence mapping

| D05 contract | Regression evidence |
|---|---|
| Register metadata/status/source integrity/individual expiry | tests/allocation/test_d05_register.py; test_stage_i_assumptions.py |
| Real recommendation refusal; test-only synthetic loader | test_d05_register.py; portfolio/test_stage_i_advice_gate.py |
| Configurable, labelled prototype floor/horizon | test_d05_register.py; test_stage_i_suitability.py; test_stage_i_solver.py |
| Unknown liquidity; dated evidence and exclusive expiry | test_d05_register.py; portfolio/test_stage_i_acceptance.py |
| Conservation/costs/scenarios/history and no model authority | tests/allocation/; tests/portfolio/; tests/test_stage_e.py |

Actual commands/results and limitations belong to progress-lane-stage-i2.md.
Parameter validation and public-advice eligibility are separate PENDING decisions;
no reviewer appointed. Regression evidence is not independent release acceptance.
