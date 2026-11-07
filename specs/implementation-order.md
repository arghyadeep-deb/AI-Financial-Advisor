# Implementation order and shared ownership

Planning only. User selection starts implementation. Feature IDs and task numbers are references, not a requirement to finish each folder before starting another. This document defines build prerequisites; [release gates](release-gates.md) define when a selected capability may accept real users/data.

## Build sequence
| Stage | Work | Prerequisite / completion |
|---|---|---|
| A Foundation | 001 setup/reproductions; T103/T104 schema/money; T108 auth with T113 acceptance; remaining 001 behavior and T114/T115 contracts | T112 runs after all 001 implementation and applicable acceptance. No real-data pilot yet. |
| B Shared platform | 008 inventory/session/consent/key controls; 009 deployment, queue, quotas, monitoring; 010 screen/state design and demo | Starts after relevant 001 identity/schema contracts, not after every 008/009 UI/integration test. Storage-specific deletion hooks added as each store appears. |
| C Statement core | T201–T207, T209/T210, T216–T218; T203 security with T1402 parser runtime; minimum T1401 format registry | Requires B identity/storage/worker contracts. No need to finish OCR or additional adapters. T208 review UI develops against these APIs. |
| D Reports and core budgets | T211–T214, T219; T0601 budget subset, T0602/T0603, budget/reminder subset T0606; 010 upload/review/report UX | Depends on C ledger contracts, not on release approval for the whole 002 feature. Budget comparisons read ledger; ledger posting does not depend on budgets. |
| E Pilot acceptance | T215/T220 plus full relevant 008 purge/export/restore, 009 recovery/load/cost and 010 accessibility/usability evidence; core subset T0607 | G2 must pass before real data. Features deferred from R1 are hidden and explicitly excluded. |
| F Optional planning expansion | 003 tracking; full 006 goals/debt; 011 selected household functions; 014 further adapters | Each needs its source service and privacy controls. Extra formats do not block the single-format pilot. |
| G Advanced modules | 004 tax; 012 sources/education/research; 007 allocation | 007 needs 012 source governance (T1201) and licensed data contract where used, not completed personalized research. 012 education/research does not require 007; only a suitability-linked proposal handoff does. |
| H Connections/commercial | Manual 005 credit can follow A/B; live 005 and selected 013 require their provider/domain contracts | Separate release decisions; no automatic enablement from earlier task completion. |

## Pilot subsets
R1 core 006: versioned budget lines, exact category splits, confirmed bill candidates, comparisons and optional opted-in reminders. Goal/debt schemas may be introduced compatibly in T0601 but full goal solver, debt scenarios and their screens are R2. T0607 records which subset was tested; it is not checked fully complete until all selected 006 requirements pass.

Core 010: onboarding/demo, supported-format messaging, upload/review/report states, responsive/accessibility checks and relevant preferences. Unselected tax/portfolio/household screens are not prerequisites to the monthly pilot. New domains later repeat UX acceptance for their own flows.

Privacy and operations are integrated incrementally. Final 008 deletion tests need actual stores from C/D; building those stores needs the B privacy contract, not a prematurely completed deletion test. 009 restore validates whatever stores are included in the selected release. No circular whole-feature prerequisite is intended.

## One implementation per shared capability
| Capability | Implementation owner | Other tasks consume or verify |
|---|---|---|
| Authentication/session service | 001 T108/T113 with 008 T0802 lifecycle extensions | Reuse service; no separate auth stack |
| Exact-money/source definitions | 001 T104/T105 and financial-rules.md | 002 T216 adds ledger fixtures; all later engines consume |
| Upload ownership/storage policy | 002 T203/T204 | 014 T1401 registry/T1402 isolated scanner/parser runtime deliver the same path, including before R1 |
| Ledger splits/corrections | 002 ledger service | 006 T0602 budget API and 014 T1403 manual/split API call this service; no competing split tables |
| Queue, lease and outbox | 009 T0902 | 002 T206 supplies graph integration; no second queue implementation |
| Cancellation/reversal/reprocess | 002 T217 and reversal contract | 014 T1406 evaluates adapter reprocessing on this service |
| Notifications | 010 T1005 shared preference/delivery service | 006 T0606 and 011 T1104 emit domain events, not independent senders |
| Privacy purge/export | 008 T0804/T0805 | Every new data owner registers hooks and tests; 009 restore reapplies deletion suppression |
| Suitability/plan generation | 007 | 003 observations and 012 sourced research supply inputs, never duplicate proposal engines |

## Task execution rule
Within a feature, implement schemas/contracts before their consumers and run final review tasks after all selected behavior. Original review IDs T112, T215/T220, T306, T406 and T506 are end-of-slice gates even when their numeric position is earlier. Stable IDs are preserved for traceability. Overlapping acceptance tasks may reuse one evidence artifact but must identify the shared implementation; they are not instructions to build it twice.
