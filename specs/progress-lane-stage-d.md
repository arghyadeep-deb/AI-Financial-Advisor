# Stage D continuation — offline backend

Worktree/branch: `AI-Advisory-stage-d` / `codex/stage-d`. Date: 2026-11-07.
Changes remain in the working tree. No git add, commit, push, deployment, live
provider, billing, tax filing or trade action. Initial working tree was clean.
Frontend and shared progress/handoff files are untouched. The only main.py change
is the planning router include. All DB tests use migrated temporary SQLite DBs.

## Decisions and conflicts

- The explicit implementation request supersedes planning-only headings in 006.
  The more specific lane instruction overrides the generic local-commit rule:
  **no git add or commit**. Only revision **0110**, parent **0101**, is introduced.
- Reuse `FinanceSnapshot`, ledger splits/links/owner locking, shared errors/money,
  queue and notification service, migrations runner and owned-store registry.
  No second authorization, split, payment, notification or proposal engine.
- `PlanningRevision` stores typed budget, obligation, settlement, receivable,
  goal, debt and immutable scenario documents in one append-only revision store.
  Each API has its own Pydantic contract. Unique owner/operation and
  owner/resource/revision constraints plus the shared owner lock fence writers.
  SQLite ignores FOR UPDATE, so the shared lock now also makes a no-op owned-user
  UPDATE, including when the owner has no statement accounts.
- Report rule becomes `ledger.v2`; older report bytes remain unchanged and are
  labelled stale. A report freezes the current planning vector and budget version.
  Planning edits conservatively stale reports even when another month was edited.
- A ledger month never establishes future investable capacity. Dashboard snapshot,
  analysis and Chat use observed facts with period, historical/stale/unverified
  labels. Ledger Chat is deterministic, skips provider and legacy RAG calls, and
  uses the existing `degraded` wire status (no new client status introduced).
- Positive planning capacity is a **declared estimate**, requiring today's
  Asia/Kolkata confirmation, a non-stale report with verified selected coverage
  and complete classification, an exact planning vector, explicit completeness
  and forward assumptions. It is never copied into the monthly report's
  investment-capacity field. Household completeness remains unverified.
- Zero future investment return only. Inflation is a separate user assumption.
  Debt supports fixed-rate monthly reducing balances, interest rounded half-up
  each month to paise, explicit fees/term and at most 600 months. Missing/floating
  rates or missing terms are incomplete; no promised saving or approval.
- Confirmed obligations represent an explicit due occurrence. Updating due date
  is an audited revision; no silent creation of a new confirmed bill from a
  candidate. Monthly future flow includes the next recurring payment even when
  today's occurrence is paid. Stale recurring dates/payment evidence block a
  positive estimate. Annual amounts have explicit ceil(amount/12) flow earmarks.
- PUT with the full resource data replaces PATCH for edits. Existing CORS permits
  PUT; the lane forbids editing main.py's middleware. Archive/undo are new PUT
  revisions, never deletion of historical business evidence.
- FIN-15 cannot produce a verified net worth without 003 owned dated holdings,
  dated debt balances and confirmed household inventory. Reports explicitly
  return unavailable; do not build a competing holdings/011 net-worth service.
- No release claim: G2/G3, PostgreSQL concurrency, CI, real-data/privacy/operations
  readiness and new UI acceptance remain outside this synthetic backend evidence.

## Task status and requirement evidence

The command log below is authoritative about what ran. No shared task boxes are
ticked. Final verification results are appended after execution.

| Task | Status | Files and implemented evidence | Remaining / disabled |
|---|---|---|---|
| 002 T211 | partial | `monthly_report_service.py`, `statement_controller.py`, `statements.py`: immutable report history, scoped source drill-down, CSV with explicit restatement adjustment rows, live stale flags, frozen budget revisions. FIN-09 test retains original January 1,000 spending, explicit restated 600, February +400 cash/-400 spending. | PDF disabled; frontend owned by orchestrator. |
| 002 T212 | partial | `finance_snapshot_service.py`, `analysis_service.py`, `analysis_controller.py`, `chat_service.py`, `schemas.py`: canonical backend Dashboard/analysis/Chat ledger consumer, deficit cap 0, dated partial/stale provenance, source-vector invalidation, scenario isolation. | Frontend must consume/display the additive snapshot; no new ledger browser flow claimed. |
| 002 T213 | partial | `planning_service.py`: deterministic owner-confirmed merchant/category suggestions; never post/split automatically. `monthly_report_service.py`: deterministic narrative and verified prior-month comparison with immutable report ID. | No model category service, independent suggestion-quality corpus or model narrative; deterministic mode only. |
| 002 T214 | partial | `tests/test_stage_d.py` plus existing Stage C parser/tenant/failure/privacy tests: offline acceptance and adversarial inputs, no model calls for ledger Chat. | Independent held-out evaluation and operational release review remain unrun. No external tracing experiment. |
| 002 T219 | partial | `planning.py`, `planning_service.py`, report/controller: real revisioned budget inputs, bill candidates/explicit confirmation, report comparisons, unsupported card-adapter status. 5,000/5,500 gives exactly 500 overspend. | Orchestrator's budget/report/review UI remains. |
| 002 T216 FIN-09/10/14 | partial (selected backend cases implemented) | Explicit immutable restatement; confirmed 1,200 purchase/600 due/200 received => own share 600, receivable 400, recognized spending 1,200, reimbursement not salary; confirmed 65,000−55,000−4,000−3,000 => capacity 3,000, liquid minimum tested. Ledger and planning service integration tests. | FIN-15 verified aggregate remains unavailable; task-wide FIN-01..16 release acceptance not claimed. |
| 002 T217/T218 | partial | Ledger correction replay/conflict/stale tests; reverse/cancel/quarantine reprocess generations, parser-version pinning and comparison; shared-support/link invalidation, worker recovery, concurrent publish/cancel/reverse/report and account/link vectors reuse Stage C tests. | Full PostgreSQL/isolation/worker-crash matrix and durable LangGraph checkpointer remain unrun/unimplemented as at Stage C handoff. |
| 006 T0601 | done (offline backend) | `models.py`, migration `0110_planning_revisions.py`, `planning.py`, `owned_stores.py`: immutable typed revisions; frozen report budgets; archives/history; migration model/unique-constraint sync, downgrade refusal and inventory/export/purge tests. D9: 31 passed; tests `test_planning_migration_*`, `test_budget_500_*`. | UI/operational release acceptance not included. |
| 006 T0602 | done (offline backend) | `planning_controller.py`, `planning_service.py`, shared `ledger.split`: create/edit/archive/copy preview, explicit positive rollover from current verified report, exact signed paise splits with optional budget label; race/tenant/overspend tests. D9: 31 passed; tests `test_budget_500_*`, `test_resource_api_*`, `test_budget_writers_*`, `test_positive_rollover_*`. | Frontend acceptance remains in T0606; no automatic rollover from partial/unverified data. |
| 006 T0603 | done (offline backend) | At least 3 dated normalized occurrences with monthly/annual cadence and 20% amount-spread tolerance create suggestions only. Explicit confirmed obligations, variable amounts, pause/archive, revision-bound partial settlements; one transaction cannot settle two bills. D9: 31 passed; tests `test_recurring_candidates_*`, `test_settlement_partial_*`, `test_settlement_race_*`. | No automatic due-date roll-forward; variable bill amount must be confirmed before overpayment matching. |
| 006 T0604 | done (supported offline backend) | `engines/planning.py`, `planning_calculations.py`: exact zero-return goal solver, separate inflation assumptions, past deadline, competing priorities, funding account ownership, allocated cash cannot be reused, user-set reserve months/essential expenses. D9: 31 passed; tests `test_goals_independent_*`, `test_FIN14_*`, `test_goal_debt_*`. | Nonzero return scenarios and planning UI disabled; complete household liquidity is an explicit user assumption, not independently proven. |
| 006 T0605 | done (supported offline backend) | Fixed monthly-reducing debt schedules, fees/prepayment assumptions, snowball/avalanche ranking, term cap, negative amortization and incomplete terms; owner-scoped immutable scenarios bind report/planning vectors. Extra payment cannot exceed capacity. D9: 31 passed; tests `test_debt_independent_*`, `test_FIN14_*`, `test_goal_debt_*`. | Floating/daily compounding and actual lender schedules unsupported; no external loan action. |
| 006 T0606 | partial | Existing notification queue emits only metadata for opted-in bill revisions; worker rechecks revision/opt-in/pause/archive/payment and shared preferences. Retry deduplication tested. | Frontend undo/explain/reminder controls and installed worker scheduling remain orchestrator/operations work. No push/email. |
| 006 T0607 | partial | Synthetic exact golden calculations, deficit no positive allocation, stale inputs, tenant/idempotency/race, migration and registry/privacy tests. | Full planning UI, independent eval corpus, PostgreSQL/operations/G3 acceptance remain. |
| Optional 003 | unstarted in this lane | Existing portfolio arithmetic retained; no competing owned holdings implementation. | All partial items in modules handoff remain; FIN-15 depends on these source contracts. |

Completed 006 backend tasks meet the explicit numerical/schema/API acceptance in
the supported offline scope, with limits listed per row. Feature-wide planning
acceptance (T0607), UI (T0606) and release gates remain **partial**. No unrun gate is
claimed passed. The exact D9 command below verifies all five completed backend tasks.

## API handoff for the HTML/JS owner

All endpoints require the existing bearer session. Wrong-owner resource access
returns the same structured 404 as missing; input errors 422; stale revision,
source-vector and idempotency conflicts 409. JSON contains integer paise only.
Use OpenAPI for exact bounds/defaults. No LLM amount is authoritative.

### Shared revision envelope

`POST /budgets`, `/obligations`, `/obligation-settlements`, `/receivables`, `/goals`,
`/debts` create with expected_revision **0**. `PUT /{collection}/{id}` supplies
the current revision and full data. Repeating the same key/body returns its original
result; a changed body/key collision returns 409. GET collection returns the latest
revision per resource (including archives), sorted by ID, 100/page with `offset`.
GET `/{collection}/{id}?revision=N` reads immutable history; omit revision for latest.

```json
{
  "expected_revision": 0,
  "idempotency_key": "browser-generated-uuid",
  "reason": "User confirmed January plan",
  "data": {"month":"2026-01","currency":"INR","lines":{"grocery":500000},"rollover":"none","archived":false}
}
```

Response:
```json
{"id":"resource-uuid","kind":"budget","revision":1,"data":{"month":"2026-01","currency":"INR","lines":{"grocery":500000},"rollover":"none","archived":false},"created_at":"ISO datetime"}
```

`GET /planning/vector` -> `{ "resource-uuid": 1, ... }`, excluding derived debt
scenarios. Fetch before capacity/planning calculations. All planning edits stale
affected source-dependent reports/scenarios conservatively.

### Budgets and ledger classification

- `data` budget: `{month,currency:"INR",lines:{category_slug:paise},rollover:
  "none"|"positive",archived:false}`. Zero budgets valid. One active budget/month.
- Existing `POST /ledger/{id}/splits` retains operation envelope and components.
  Component adds `budget_category:"grocery"|null`; financial category remains
  `purchase|interest|loan_principal|...` from the ledger registry. Optional
  `obligation_id` must be owned and active. Components conserve original signed
  paise/direction. This is the only split service; linked rows require unlinking.
- Refund category allocation follows original component proportions, floors each
  share, assigns residual paise to last component. Reimbursement is separate from
  recognized spending. Uncategorized expense remains explicit.
- `GET /budgets/{id}/copy-preview?month=2026-02&report_id=...` ->
  `{source_id,source_revision,preview:{...budget data...},persisted:false,basis}`.
  Positive rollover needs a current verified source-month report with that budget
  revision. It adds only max(0,allocation−actual); overspending remains visible.
  Save preview explicitly with POST; preview never changes source or creates money.

### Confirmed bills, settlements and receivables

- `GET /obligation-candidates` -> array `{merchant,account_id,cadence:"monthly"|
  "annual",variable,suggested_amount_paise,entry_ids,status:
  "candidate_requires_confirmation"}`. No obligation is created automatically.
- Obligation data: `{label,amount_paise,due_date:"YYYY-MM-DD",cadence:"once"|
  "monthly"|"annual",variable:false,paused:false,archived:false,
  reminder_opt_in:false,candidate_entry_ids:[]}`. Creating this resource is explicit
  user confirmation; candidate IDs are optional owned active debit evidence.
- Settlement data: `{obligation_id,expected_obligation_revision,entry_id,
  expected_entry_revision,reversed:false}`. PUT `reversed:true` is audited undo.
  Payment must be in that confirmed occurrence's period. Partial payments supported;
  excess requires correcting a variable bill amount. Changed bill/payment revision
  invalidates the match; reverse/reconfirm instead of silently reusing it.
- `GET /obligations/{id}/status` -> resource plus `{paid_paise,remaining_paise,
  state:"unpaid"|"partial"|"paid"|"paused"|"archived",
  needs_review_settlement_ids:[]}`. Notice copy stays generic. UI must not show
  any bill reminder as enabled until the user explicitly opts in.
- Receivable data: `{purchase_entry_id,expected_entry_revision,due_paise,
  archived:false}`. `GET /receivables/status` -> resources plus `{status:
  "confirmed"|"needs_review",received_paise,remaining_paise,own_share_paise}`.
  Existing ledger reimbursement links are the received evidence; never a second
  settlement table or automatic salary classification. Confirmed due cannot exceed
  purchase; linked receipts cannot exceed due. Reports freeze this view at creation.
- `GET /ledger-category-suggestions` -> `{entry_id,expected_revision,category,
  budget_category,status:"suggestion_requires_confirmation",source_entry_ids}`.
  Requires three earlier dated corrections with a unanimous label for this owner,
  account and normalized merchant. Accept only via existing split endpoint.

### Goals, capacity and debt

Goal data: `{label,target_paise,allocated_paise:0,target_date,priority:1,
funding_account_id,value_basis:"present"|"future",inflation_bps:0,
annual_return_bps:0,archived:false}`. Nonzero return is rejected. `allocated_paise`
is explicitly declared previously funded cash, separate from new monthly funding.

Debt data: `{label,obligation_id,principal_paise,annual_rate_bps:null|integer,
rate_type:"fixed"|"floating",convention:"monthly_reducing",
minimum_payment_paise,monthly_fee_paise:0,prepayment_fee_paise:0,
term_months:null|1..600,evidence_date,archived:false}`. Minimum must match the
confirmed obligation. One active debt per obligation. Missing rates/term or floating
terms return incomplete schedules; evidence older than 31 days is stale/incomplete.

`POST /planning/capacity` body (values below illustrate FIN-14, not released advice):
```json
{"report_id":"current-report-uuid","expected_planning_vector":{"principal-obligation-uuid":1},"evidence_date":"TODAY-IN-ASIA-KOLKATA","income_paise":6500000,"spending_paise":5500000,"eligible_liquid_paise":2000000,"reserve_funding_paise":300000,"earmarks_paise":0,"included_obligation_ids":[],"obligations_complete":true,"assumptions_confirmed":true}
```
With a confirmed unfunded 400000 principal obligation due within 31 days, result
includes `{available_paise:300000,flow_capacity_paise:300000,
liquid_capacity_paise:1300000,unfunded_flow_paise:400000,
unfunded_cash_paise:400000,status:"declared_estimate",report_id,planning_vector,
obligations_needing_review:[],rule_version:"planning.v1",...}`.
Missing assumptions/coverage -> available null/status unavailable. Deficit -> 0.
Included IDs assert that forward spending already includes those payments; IDs are
distinct, owned and counted once. Current cash subtracts only unfunded upcoming
commitments, reserve funding and earmarks, never historical spending again.

`POST /goal-plans` adds `{as_of:"YYYY-MM-DD",reserve_months:6,
essential_expenses_paise:0}` to capacity body. Returns `{capacity,goals:[{id,
future_target_paise,remaining_paise,months,required_monthly_paise,
suggested_monthly_paise,monthly_shortfall_paise,status,inflation_bps,
annual_return_bps:0}],unallocated_capacity_paise,reserve:{months,
essential_expenses_paise,target_paise,basis},assumptions}`. Priority is ascending
number, ties use stable goal ID. No double allocation of already funded cash.

`POST /debt-scenarios` adds `{idempotency_key,strategy:"avalanche"|"snowball",
extra_payment_paise:0,max_months:360}` to capacity body. Returns an immutable
`kind:"debt_scenario"` revision with data `{capacity,assumptions,debts,result}`.
Result includes bounded monthly schedule, exact interest/fees and status
`paid_off|negative_amortization|contractual_term_exceeded|term_limit|incomplete`.
GET `/debt-scenarios/{id}` adds current `stale`. This compares hypothetical terms;
it does not edit debt, recommend a loan or make a payment.

### Reports and Dashboard/Chat

- Existing `POST /monthly-reports` retains `{month,account_ids,expected_vector}`.
  Optional explicit restatement: `{restates_report_id,restatement_reason,
  restatement_refund_ids:[confirmed-later-refund-link-id]}`. Same original month and
  scope required; original retained. No automatic backdating of refunds or cash.
- GET `/monthly-reports?month=YYYY-MM&offset=0` lists owned immutable reports.
  GET `/monthly-reports/{id}/transactions?offset=0&category=purchase&budget_category=grocery`
  returns `{report_id,stale,sources,restatement}` from snapshot, even after correction.
  Source document bytes still require the existing authenticated document endpoint
  and may expire; immutable totals do not promise permanent file retention.
- Snapshot adds `planning_vector`, `budget:{status,budget:<revision>|null,
  actual_paise:{category:paise},lines:{category:{allocated_paise,actual_paise,
  overspend_paise}}}`, `confirmed_obligations`, `receivables`, `restatement`,
  `comparison:{status,previous_report_id,reason,changes_paise}`, `card_support`,
  `net_worth:{status:"unavailable",value_paise:null,reason}`. Comparison needs both
  months' verified current report scope; otherwise unavailable, no invented trend.
- For ledger.v2, CSV adds `row_type` and `spending_adjustment_paise` columns. Existing
  ledger.v1 snapshots retain the original CSV header/bytes (regression tested).
  Source cash amount
  stays unchanged; explicit later-refund rows have blank cash and negative spending
  adjustment. CSV formula prefixes in original descriptions remain escaped.
- `GET /finance-snapshot` -> `{found,snapshot:<FinanceSnapshot>|null}`. The existing
  `/analysis/state` also adds `snapshot` for Dashboard. Observed flows replace
  profile-era flow amounts in non-scenario analysis. What-if profiles remain isolated.
  `coverage` includes `observed_ledger`, `historical_month`, `stale_sources` and/or
  `partial_or_unverified`, plus `household_inventory_unconfirmed`; show these labels
  and `as_of` prominently. Profile savings/investments are still declared values.
- Ledger-backed Chat/stream returns only deterministic dated facts, no source text
  sent to a model. Reports never advertise investment capacity from surplus.
- GET `/statement-imports/{id}/comparison` shows owned old/current staged facts,
  parser versions and `facts_changed`. It never authorizes automatic matches.
  New jobs pin parser version. A worker running a different parser quarantines
  `parser_version_changed`; explicit reprocess pins the new version and returns to
  revision-checked review. Source rows/old reports remain immutable.

## Migration, privacy and recovery

0110 down_revision=0101 creates only `planning_revisions`; model columns and unique
constraints are tested against Alembic output. SQLite/PostgreSQL immutable UPDATE
triggers preserve revisions; authorized privacy DELETE remains possible. The table
is registered in `owned_stores.py` for inventory, export, idempotent purge and restore
suppression replay through the existing registry. No private side store or secret.

Use existing migrations_runner and a verified backup for real migrations; none ran
on user/live DBs here. Empty temporary DB downgrade 0110→0101→head is tested.
Populated downgrade refuses rather than erasing planning history. Prefer forward
fix; disable planning endpoints/stop workers before operator recovery. Preserve or
authorized-purge planning evidence before downgrade. Restore business DB with the
independent suppression journal as already specified in Stage C; do not restore an
old suppression journal. No production restore/RTO claim is made by these tests.

## Actual command log

All invocations use the exact requested Python. UTF-8 avoids existing repository
emoji output issues on Windows. External provider keys/tracing are disabled by
tests/conftest.py before imports; scanner/storage fixtures are synthetic only.

**D1**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py -q -p no:cacheprovider -W ignore`
Result: **4 failed, 7 passed in 11.75s**. A positive synthetic fixture failed exact
balance reconciliation; corrected its closing balance. Two ownership assertions
included random request IDs, and a snapshot assertion included construction time;
corrected assertions to compare stable business facts. No failed test counted done.

**D2**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py tests/test_stage_c_statements.py tests/test_stage_c_security.py -q -p no:cacheprovider -W ignore`
Result: **45 passed in 33.60s** (initial corrected slice).

**D3**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py tests/test_stage_c_statements.py tests/test_stage_c_security.py tests/finance -q -p no:cacheprovider -W ignore`
Result: **123 passed in 68.38s** (expanded matrix; intermediate before final review).

**D4**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Result: **360 passed, 8 skipped in 185.89s**. Intermediate suite started before
later final-review edits; superseded by the final run recorded below.

**D5**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py -q -p no:cacheprovider -W ignore`
Result: **28 passed in 26.40s** (intermediate before added overflow/race tests).

**D6** (same exact command as D5)
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py -q -p no:cacheprovider -W ignore`
Result: **29 passed in 26.65s** (intermediate expanded review).

**D7**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Result: **365 passed, 8 skipped in 190.55s**. Intermediate: legacy CSV compatibility
and final active-owner fencing were added after this invocation started. Final
full-suite result below supersedes this evidence for the completed worktree.

**D8 explicit browser suite**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore`
Result: **13 passed in 33.65s**. Existing HTML/JS browser regression only; no new
ledger/planning UI was implemented or browser-accepted in this lane.

**D9 final focused review/acceptance**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py -q -p no:cacheprovider -W ignore`
Result: **31 passed in 31.77s**. Includes original legacy CSV exact bytes,
confirmed source-version comparison/reprocess, positive goal/debt service paths,
deficit provider-free Chat/stream/analysis, independent schedules and category
goldens, migrations/registry hooks, invalid numeric/opt-in inputs and races.

**Final review findings corrected before D9/D10**: stale worker parser version
quarantines instead of silently changing parser identity; monthly payment already
paid does not erase next month's recurring flow; corrected payment/obligation
evidence blocks positive capacity until reviewed; notifications recheck confirmed
bill state under shared owner lock; aggregate MoneyError uses shared structured 422;
existing v1 CSV remains byte-reproducible; active-owner update must actually match.

**D10 authoritative final full suite, including browser**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests -q -p no:cacheprovider -W ignore`
Actual final output:
```text
....                                              [100%]
379 passed, 8 skipped in 207.69s (0:03:27)
```
All implementation and acceptance-test changes preceded this run. The eight
skips remain six explicitly public authentication-route cases and two PostgreSQL
opt-in tests; they are not claimed passes. This includes all 13 browser tests and
the 31 Stage D tests. It supersedes intermediate suite results D2–D9 for the final
worktree. No live provider, production DB, CI or external review was exercised.

`git diff --check` passed. The test-generated `evals/results/latest.json` revision
metadata was restored from the initially clean HEAD using read-only `git show`
via the required Python, with the repository's core.autocrlf=true checkout line
endings preserved. No user edits were overwritten. Final checks
confirm no changes under frontend or to shared progress/handoff files, and only
the single permitted app.include_router line in main.py. Work stays uncommitted.

## Remaining / disabled and owner questions

- Frontend owner must wire the documented endpoints, show source/coverage/date,
  correction/reprocess comparison, report history/restatements, budget edits/undo,
  candidate confirmation, bill paid states and explicit reminder controls. Existing
  browser suite only establishes that this backend did not regress existing UI.
- FIN-15 verified net worth remains unavailable pending owned same-date holdings,
  dated debt balances and household inventory. Do not add profile investment
  projections to ledger cash or report surplus. Optional 003 was not expanded.
- PDF export, real bank/card/PDF/OCR adapters, live providers, model financial
  narration, nonzero goal-return scenarios and unsupported debt conventions remain
  disabled. Named products/public advice retain existing gates.
- Independent held-out evals, PostgreSQL full concurrency/crash matrix, CI, external
  Codex acceptance review, G2/G3 operations/restore/load/privacy approvals and new UI
  walkthrough remain unrun; no pilot/public enablement from this lane.
- Confirm conservative defaults: 20% candidate amount-spread tolerance; monthly
  25–35-day / annual 350–380-day detection; 31-day debt freshness; annual flow
  earmark rounding up; default illustrative six reserve months. All remain explicit
  synthetic planning policy choices, not lender/provider/market guarantees.
- Confirm whether to add nonzero return assumptions or more lender conventions in
  a separate reviewed slice. Until then unsupported inputs fail or stay incomplete.
- Planning quotas/large-history performance, installed scheduling, retention and
  independent OS/DB/storage recovery approvals remain shared release work from C.
