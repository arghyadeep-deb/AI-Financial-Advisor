# Release gates and decision log

All work is planning-only until the user chooses a feature. This file defines acceptance, not permission to start work. Proposed numeric limits must be benchmarked and ratified before use. No current performance/compliance claim is made.

| Gate | Required evidence | Blocking conditions |
|---|---|---|
| G0 select scope | User chooses release/features; implementation owner resolves applicable decisions below | Unselected features stay backlog; do not implement all directories automatically |
| G1 foundation | 001 acceptance; auth/legacy migration; independent money fixtures; form/browser checks; CI | Wrong totals, cross-user access, unsafe production auth, silent fallback success |
| G2 real-data pilot | G1 + 002; 008 deletion/export; 009 deployment/restore/limits; 010 core journeys; chosen 006 budget scope | No tested privacy lifecycle, no parser support matrix, unresolved scanner/storage policy, no recovery owner |
| G3 planning beta | 003/006/014 acceptance; factual source dates; goals/capacity constraints; UX pilot evidence | Unsupported return metrics, duplicated assets, unbounded resource use |
| G4 domain module | Independent 004, 007, 011 or 012 requirement tests and applicability decisions | Unsupported tax cases, unjustified allocation, unsafe sharing, stale unsupported research |
| G5 connected/public/paid | Provider contracts and consent; operating capacity; applicable 013 billing; security review; incident/support owner | Provider eligibility missing, live flag bypass, duplicate external action, unresolved critical findings |

Build prerequisites and the exact R1 budget/UX/parser subsets are defined in [implementation order](implementation-order.md). Release gates require completed evidence; they do not make whole feature folders circular build prerequisites.

## Decision register
| ID | Decision | Proposed default | Must resolve by |
|---|---|---|---|
| D01 | First bank, account type and PDF version | One bank text-PDF plus exact CSV schema; select using synthetic/authorized fixture | Start T201 |
| D02 | Deployment region, object store, DB, scanner | Private encrypted storage and PostgreSQL; no silent scanner bypass | G2 |
| D03 | Retention and deletion periods | Expire derived exports quickly; final source/backup durations require owner decision | G2 |
| D04 | Supported tax period/regime/case | One explicit salaried resident scope; no guessing tax tables | Start T401 |
| D05 | Allocation scope and permission | Hypothetical asset-class scenarios first; public personalization disabled | G4 for 007 |
| D06 | Provider eligibility, licensed market data and consent | Mock adapters; manual/import paths remain usable | Each live adapter |
| D07 | Monetary AI/storage budget and capacity | Proposed 009 load limits; actual price caps chosen after benchmark | G2 |
| D08 | UI framework | Retain Streamlit until measured acceptance gaps justify change | Start 010 |
| D09 | Notifications and languages | In-app English first; optional verified channels and evaluated Hindi/Hinglish | Each channel/locale |
| D10 | Paid tiers and support model | No payments in pilot | Start 013 billing |
| D11 | Research/knowledge distribution and licenses | Official educational sources first; research features gated | G4 for 012 |
| D12 | Public release legal/privacy applicability | Dated scope review with exact sources and unresolved items | Before relevant public feature |

## Evidence record template
For each gate record date, build/commit, selected feature IDs, requirement IDs, fixture/eval versions, actual commands and outputs, browser walkthrough, load hardware/data, restore result, processor/provider configuration, known limitations, blocked features, responsible owner and review disposition. No fabricated pass rate. A passed small suite is evidence of those cases only, not proof of zero real-world error. Re-run affected gates for material parser, model, schema, permissions or rule changes.

## Definition of done for tasks
A task is done only when its behavior is implemented, negative/authorization cases pass, user-visible errors are useful, source/privacy semantics remain consistent, migrations are exercised where relevant and evidence is attached. Documentation-only tasks finish with reviewed contracts/examples, not code. Every release includes a requirement-to-test matrix. Deferred requirements need explicit removal from that release's advertised scope; they cannot be silently counted as complete.
