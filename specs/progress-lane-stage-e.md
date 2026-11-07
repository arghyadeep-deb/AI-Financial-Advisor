# Lane E: offline portfolio, allocation and sample tax harness

Date: 2026-11-07. Base: integration, Alembic head 0110. Work remains uncommitted
for the orchestrator. No git add/commit/push, frontend edits, live DB operations,
external integrations, billing, filing, trades or public deployment.

Read first: implementation order/progress/handoff; modules handoff and remaining
Stage B/C/D sections; 003/004/007 specs, plans, tasks and acceptance mappings;
financial rules, constitution, agent quality, release gates and review checklist.
User-selected work supersedes planning-only spec headers. Lane-specific instruction
to leave changes uncommitted supersedes the earlier general local-commit rule.

## Task status and requirement evidence

All rows below reference **E5**, the exact focused command/result in the command
log, with final changes covered by **E8b/E9**. Final backend/browser regressions
are **E9/E7**. A task marked partial is not a
feature-completion or release claim. No shared progress/handoff/task boxes changed.

| Task | Status | Files and tested outcome | Remaining limitations / disabled features |
|---|---|---|---|
| 003 T301 | done (selected manual INR schema) | `backend/schemas/portfolio.py`, `backend/models/models.py`, `migrations/versions/0120_portfolio_revisions.py`: owner, account/folio reference, instrument, units string, dated quote/source/version/expiry, optional basis; immutable full-book and suitability revisions. E5 migration/model-sync/immutability/registry tests. | Owner-confirmed records are unverified declarations; no licensed instrument master. Migration/recovery below. |
| 003 T302 | done (bounded text CSV/manual backend) | `backend/controllers/portfolio_controller.py`, `backend/services/portfolio_service.py`: authenticated repeat-safe full-book confirmation/read/history; strict money; bounded CSV preview with exact documented header. E5 CSV, API, duplicate, retry, concurrent CAS and invalid/overflow tests. | No binary investment-document adapter. No ingestion from bank movements; no inferred holdings. Preview omits confirmation so it cannot confirm itself. |
| 003 T303 | partial | Same service/router: dated/current/partial/unavailable valuation, source and position drill-down, explicit stale and owner-confirmed-unverified coverage. Missing/future/expired quotes never become zero. Explicit complete empty/closed inventory is zero. E5 quote coverage, stale, closure and ownership tests. | Orchestrator frontend presentation and new-flow browser acceptance absent. No verified quotes, market calendars or real-data release. |
| 003 T304 | done (backend hypothetical slice) | Portfolio service, `engines/portfolio/`: selected shocks and contributions remain read-only/hypothetical; a 10,000 rupee deficit returns verified affordable contribution zero even if the chosen scenario contribution is positive. E5 API deficit/scenario separation and old portfolio goldens. | Positive verified affordability is never asserted from profile/holdings declarations. New UI remains in T303/T310. |
| 003 T305 | partial | `engines/portfolio/{__init__,rules}.py`, portfolio service: exact allocation/issuer HHI, unknown exposure, source currency/coverage and formula explanation. v2 uses largest remainders so displayed class/issuer amounts conserve aggregate paise. E5 independent fractional and concentration fixtures. | UI acceptance, licensed classifications and FX remain absent. No low-risk claim. |
| 003 T307 | done (selected explicit identity scope) | Schemas/service: one confirmed observation per exact account_ref/instrument_id, manual/CSV overlap rejected for review; full-book revision resolves source conflict explicitly; closed positions require zero units; old books stale. E5 overlap, multiple-folio, closure, retry and history tests. | No alias inference or automatic corporate-action/transaction-derived reconciliation. Unsupported performance stays unavailable. |
| 003 T308 | partial | `engines/portfolio/returns.py`: conventional dated ACT/365 XIRR with bounded Decimal bisection; exact end-flow TWR; independent 10%/21% fixtures and unsupported sign patterns/no-solution/action-support refusals. Existing absolute gain prerequisites retained. E5 return and existing metric tests. | Books contain no transaction/valuation histories, so book XIRR/TWR/benchmark remain null. Benchmark adapter/comparable history, nonconventional root isolation, general performance ingestion and UI absent. No invented terminal value. |
| 003 T309 | partial | Owned price/holding edits create new immutable book revisions; allocation invalidation checks server-resolved revision/date/source vectors and expiry. E5 corrected-price, planning/suitability/profile changes, expiry and unavailable-current-input tests. | No licensed price-version service/per-asset stale-market calendar; owner declares quote expiry. Verified 011 net-worth consumer remains unavailable rather than combining projections. |
| 003 T310 | partial | Allocation consumes same owned book/source dates/coverage; profile or scenario projections do not create holdings. E5 owned consumer, incomplete inventory, explicit scenario, gate and deficit tests. | 011 same-date verified net-worth integration and orchestrator UI/browser walkthrough absent. Existing reports still safely return unavailable net worth. |
| 007 T0705 | partial | `backend/services/allocation_service.py`, portfolio schemas/router/store: owned suitability history; immutable existing AllocationPlan table reused; authenticated sandbox, exact replay and conflict handling, server vectors and shared owner lock; profile CAS row fenced until publication. E5 real two-session retry/CAS, foreign/missing 404, source invalidation, privacy export/purge/restore-suppression and metadata tests. | Frontend assumptions/acceptance/history presentation and its browser acceptance absent. SQLite concurrency exercised; PostgreSQL execution/production isolation and large-history quota/load evidence absent. |
| 007 T0706 | partial | Existing cost/stress engine plus `engines/allocation/costs/__init__.py` rebalance; `evals/allocation/stage-e-held-out-v1.json` four additional hand-derived constraint cases. E5 checks exact targets/deltas, contribution-first additions, sale alternative, residual paise and repeatability. No product selection, net-improvement claim or fabricated tax cost. | Independent evaluator sign-off, empirical volatility model, point-in-time fee-inclusive backtests and operational/UI acceptance remain absent. These four extra synthetic fixtures are not claimed independently held-out certification. |
| 007 T0707 | partial (backend gate proven) | Existing hard-false public gate retained. Sandbox requires ALLOCATION_SANDBOX_ENABLED=true and APP_ENV=test/development. Default off; production cannot enable it. Public proposal always gated even if NAMED_PRODUCT_RECOMMENDATIONS is true. E5 service/API guards plus existing malicious-output guard tests. | D05 applicability/eligibility, production-approved sources/universe and independent release evidence unresolved; no launch permission. No execution tool. NAMED_PRODUCT_RECOMMENDATIONS was not enabled. |
| 004 T401/T404 | partial (synthetic engine portions complete) | `engines/tax/sample_packs.py`, `knowledge_base/tax/sample-v1.json`: strict versioned/dated/hash-checked sample-only loader and deterministic exact slab/supplement/rounding harness. E5 independent threshold, rounding, refund/missing-withholding and scope fixtures. | SAMPLE-2026/sample is deliberately not a statutory year/regime. No new legal rules, tax advice, current-year claims or approved tax draft. Existing archived salary sandbox remains unapproved and unexposed by this lane. |
| 004 T407 | partial | Pack metadata records invented-source label, owner, effective/expiry/review dates, parameters and arithmetic policy. Support: fictional INR resident, one employer, salary only, standard invented deduction; excludes other incomes/deductions and values above final slab. E5 loader/scope tests. | Actual D04 taxpayer/form/period matrix and official provision/rate verification require a reviewed legal scope and remain disabled. No statutory source claims added. |
| 004 T408 | partial | Identity/period/income/withholding conflicts or missing evidence -> needs_review; unsupported income/period/regime -> unsupported; both omit computed tax. Hash mismatch, invalid pack ordering and attempted production/non-synthetic packs reject. E5 conflict/integrity tests. | No document parser, original field evidence/correction workflow or professional release review. No automatic preference between conflicting sources. |
| 004 T409 | partial | Harness captures pack/input digest and revision, detects corrected pack/input or expiry, and returns clearly labelled synthetic JSON. E5 refresh/expiry tests. | No persisted tax cases/drafts or tax export/UI; statutory annual refresh and legal golden cases unavailable. |
| 003 T306 / 004 T406 | partial (final slice review) | E5 executed after implementation: authorization, source coverage, hypothetical separation, exact goldens, migrations/recovery, registry privacy and gates. Review findings and E6/E7 regression results below. | No independent external Codex review, CI, PostgreSQL matrix, tax-document acceptance or new-feature UI walkthrough; no G3/G4 approval. |

004 T402/T403/T405 remain unimplemented/disabled in this selected engine-only
slice: tax case/document stores, extraction/evidence review and official-looking
draft exports would need the unresolved statutory scope. No tax table/migration
was created. 007 T0701-T0704 existing tested implementations are reused, not
duplicated; rebalancing extends their asset-class comparison arithmetic.

## Endpoint/JSON handoff for HTML/CSS/JS owner

All endpoints use existing bearer sessions and structured shared errors. 401 for
no/revoked session; missing/foreign resources share 404; stale revisions or changed
idempotency body 409; malformed values 422. Monetary JSON is integer paise; units
are decimal **strings** with at most eight places. All dates are ISO dates.
No LLM input/output determines amounts, ownership, confirmation or eligibility.

### Holdings and suitability

POST `/portfolio/holdings` creates or replaces the owner's **whole book**. Initial
expected_revision=0, then latest revision; fresh operation key/reason for each
correction. Same key/body replays the original saved revision. Do not submit only
one edited row: submit the complete reviewed book. Every observation shares as_of.

```json
{
  "expected_revision": 0,
  "idempotency_key": "browser-generated-uuid",
  "reason": "Owner reviewed complete book",
  "data": {
    "confirmed": true,
    "source": "manual",
    "as_of": "2026-11-07",
    "inventory_complete": true,
    "observations": [{
      "account_ref": "my-folio-reference",
      "instrument_id": "owner-entered-identifier",
      "issuer_id": "owner-entered-issuer",
      "asset_class": "equity",
      "currency": "INR",
      "units": "2.5",
      "observation_date": "2026-11-07",
      "price_paise": 40000,
      "price_date": "2026-11-07",
      "price_source": "owner-entered-source-label",
      "price_version": 1,
      "price_expires": "2026-11-08",
      "cost_basis_paise": 80000,
      "corporate_actions_supported": false,
      "closed": false
    }]
  }
}
```

Response 200: `{id,kind:"holdings",revision:1,data:<complete book>,created_at}`.
GET `/portfolio/holdings?revision=N` retrieves immutable history; omit revision
for latest. References are opaque owner declarations, not linked bank accounts or
instrument-master identities. No account number/identity verification is claimed.

POST `/portfolio/csv-preview` body `{csv_text,as_of}` returns
`{status:"requires_owner_confirmation",persisted:false,preview:<book without confirmed>}`.
Limit 250000 characters, 500 rows. Exact header/order:

```text
account_ref,instrument_id,units,observation_date,asset_class,issuer_id,price_paise,price_date,price_source,price_version,price_expires,cost_basis_paise
```

Empty optional cells mean unknown, never zero. CSV has no side effects. Present
the preview and obtain explicit owner confirmation before POSTing the full book
with `confirmed:true`, `source:"csv"`; confirmations cannot be numeric/string
substitutes for JSON true. Manual/CSV overlap for the same account/instrument is
rejected; show a review error and let the owner choose the one observation.

GET `/portfolio/valuation?as_of=YYYY-MM-DD&revision=N` returns:

```json
{
  "holdings_revision": 1,
  "rule_version": "portfolio-metrics.v2",
  "status": "complete",
  "as_of": "2026-11-07",
  "observation_date": "2026-11-07",
  "stale": false,
  "verification": "owner_confirmed_unverified",
  "coverage": ["owner_confirmed_unverified"],
  "total_value_paise": 100000,
  "dated_total_value_paise": 100000,
  "known_subtotal_paise": 100000,
  "asset_class_paise": {"equity": 100000},
  "issuer_paise": {"owner-entered-issuer": 100000},
  "unknown_class_paise": 0,
  "unknown_issuer_paise": 0,
  "issuer_hhi": "1",
  "verified_net_worth_eligible": false,
  "absolute_gain_paise": null,
  "xirr": null,
  "twr": null,
  "benchmark": null
}
```

Response additionally includes priced/total position counts, missing quote IDs,
largest issuer share, concentration method/scope, source revision vector, original
observations and performance-unavailable reason. `complete` describes arithmetic
on supplied scope, **not verified holdings or household completeness**. Older book
date -> stale/partial/current total null; dated total and subtotal stay inspectable.
Expired/missing/future quote -> partial/unavailable and total null. Always show
date, coverage, unknown portions and the unverified label. Empty complete confirmed
inventory/closed positions yields zero; no missing quote is changed to zero.

POST `/portfolio/suitability` uses the same revision/key/reason envelope with
`data:<Suitability>` from the existing v1 contract. Example:

```json
{"expected_revision":0,"idempotency_key":"browser-generated-uuid","reason":"Answers confirmed","data":{"revision":1,"questionnaire_version":"suitability.v1","horizon_months":120,"essential_goals_declared":false,"dependants":0,"income_stable":true,"debt_reviewed":true,"reserves_reviewed":true,"experience":"some","loss_tolerance":"high","loss_capacity":"high"}}
```

`data.revision` must be expected_revision+1. Missing answers may be saved but block
allocation through existing suitability blockers. GET `/portfolio/suitability?revision=N`
reads history/latest with the same response envelope.

### Hypothetical scenarios and gated allocation

POST `/portfolio/scenarios` body:
`{expected_revision:1,as_of:"2026-11-07",shock_bps:-2000,contribution_paise:999999}`.
Read-only result has `status:"hypothetical",persisted:false,observed:<valuation>,
shock:{observed_value_paise:100000,scenario_value_paise:80000,status:"hypothetical",...},
chosen_contribution_paise:999999,scenario_value_with_contribution_paise:1079999,
verified_affordable_contribution_paise:0|null,declared_contribution_cap_paise,
affordability,public_eligible:false,named_products_eligible:false`.
A verified shortfall returns zero verified affordability even for a chosen positive
contribution. Chosen contributions never change holdings/cash/profile or imply affordability.

POST `/allocation-scenarios` is **off by default** (404). It is usable only in
test/development with explicit `ALLOCATION_SANDBOX_ENABLED=true`; production refuses
even that toggle. It loads only the existing dated synthetic assumption fixture.
The UI must keep 007 hidden by default. Request:

```json
{"expected_revision":0,"idempotency_key":"browser-generated-uuid","reason":"Compare hypothetical classes","expected_profile_revision":1,"expected_holdings_revision":1,"expected_suitability_revision":1,"expected_planning_vector":{},"assumptions_accepted":true,"eligible_liquid_paise":450000,"planning_capacity":null}
```

When planning resources exist, supply `planning_capacity` using the **existing
GoalPlan request shape** (report_id, expected_planning_vector, evidence_date,
income_paise, spending_paise, eligible_liquid_paise, reserve_funding_paise,
earmarks_paise, included_obligation_ids, obligations_complete, assumptions_confirmed,
as_of, reserve_months, essential_expenses_paise). Date and vector must match.
This calls shared `planning_calculations.goal_plan`; no second finance engine.
Unallocated capacity after goals caps the scenario. Missing handoff with existing
planning resources -> insufficient_data; historical deficit -> no positive amount.
All positive forward capacity remains a declared estimate, never verified advice.

Result: `{id,status:"hypothetical",stale,stale_reasons,inputs:{finance,suitability,
holdings,holdings_revision,planning_vector,assumptions,constraints,as_of,
holdings_coverage,planning_capacity,request},allocation:{status:"feasible"|
"infeasible"|"insufficient_data",budget_paise,amounts:[{asset,value_paise}],reasons,
binding_constraints,...},comparison,stress,rebalance,public_eligible:false,
named_products_eligible:false,narrative_status:"unavailable"}`.

`rebalance` is hypothetical asset-class arithmetic with current_paise, target_bps,
target_paise, contribution_first `{additions_paise,result_paise,sales_paise:0}` and
sale_alternative `{delta_paise,sales_paise}`. Targets derive from the feasible
contribution's constrained mix. No product names/actions. Tax, loads, transaction
cost and net_improvement remain null. Incomplete/stale/unknown-class book inventory
blocks this comparison rather than treating missing holdings as zero.

GET `/allocation-plans/{id}` reads owned immutable evidence even if the sandbox
toggle is now off. Profile/suitability/holdings/planning/source-vector/pack/date
changes make it stale. Missing current inputs/pack preserve historical evidence
with a stale reason. A legacy internal plan without owned provenance returns
needs_review/stale. Replay returns the same plan ID and current stale state.

POST `/allocation-proposals` always returns `{status:"gated",reasons:[...]}`;
environment/model input cannot enable public advice. No trade/order/filing endpoint.

### Tax harness contract (no HTTP endpoint)

`load_pack(Path,expected_sha256=...)` is an operator/test-only bounded local file
loader. No caller can submit an HTTP path. `SampleCase` has period, regime, resident,
employer_count, salary_paise, withholding_paise|null, other_income tuple,
deductions_claimed, evidence_complete, conflicts tuple (identity/period/income/
withholding), input_revision. `calculate(case,pack,as_of=date)` returns
`status:synthetic_sample|unsupported|needs_review`, explicit synthetic label,
production_approved:false, filing_enabled:false, period, rule_version, pack dates/
digest, input revision/digest, reasons and tax_paise|null. Successful sample results
include exact slab fractions, taxable/base/supplement/total paise, payable/refund
or null when withholding is missing. `stale(result,case,pack,as_of)` detects input/
pack corrections and expiry. No persistence/UI/export is promised.

## Migration, privacy and recovery

Only new revision **0120**, down_revision **0110**. Creates portfolio_revisions
with owner FK/index, unique owner/kind/revision and owner/operation key. SQL
UPDATE triggers on SQLite/PostgreSQL forbid mutation; authorized privacy DELETE
remains possible. Model/migration columns match. Existing allocation_plans reused;
registry already covers it. Portfolio registered in owned_stores with shared export,
purge, inventory and restore-suppression lifecycle. No private side store.

E5 uses real Alembic on isolated SQLite: upgrade 0110->0120, empty downgrade to
0110, forward recovery, populated downgrade refusal, SQL immutable update rejection,
scoped/idempotent purge and separate-journal restore suppression. No real DB migrated.
No PostgreSQL trigger execution/production restore claim. Stop new work/disable
sandbox before operator recovery, preserve/export evidence using existing privacy
controls; use migrations_runner with a verified backup. Populated downgrade refuses
silent loss; forward-fix or separately approved purge/restore instead. Production
retention/backup expiry remains the existing shared D03/G2 gap.

## Review findings, decisions and open owner questions

- Corrected aggregate rounding: independently rounded classes/issuers could lose
  paise. v2 conserves group totals with deterministic largest remainders. Date/source
  provenance remains separate from arithmetic completeness.
- Confirmed book identity is exact account_ref+instrument_id. Alias resolution,
  joint ownership and source licensing cannot be inferred; owner must resolve
  conflicting rows before confirmation. Is a reviewed canonical instrument/account
  registry desired in the next slice? Safest default remains explicit declarations.
- Default-off sandbox is the chosen D05-safe scope. Public gate stays hard-false;
  no production synthetic-source approval and no named recommendations enabled.
- Existing planning resources block profile-only capacity; optional shared GoalPlan
  handoff accounts for reserves/commitments/goals. Historical surplus never supplies
  positive verified affordability. No second finance/authorization implementation.
- D04 actual period/regime/forms/statutory parameter approval remains unresolved.
  This lane does not infer a legal rule from archived code, model memory or a nearby
  year. Which reviewed statutory scope/rule owner should a later implementation use?
  Until selected/verified, real tax computation, filings and draft exports stay disabled.
- Full-book confirmations and quote expiry are explicit owner declarations. No
  per-asset calendar/freshness/licensed-feed approval is available; current UI must
  show unverified. Verified same-date household net worth remains unavailable.
- Final review is the selected offline acceptance matrix, not independent external
  Codex/CI/legal/security approval. No new product UI, deployment, live provider,
  benchmark feed or PostgreSQL evidence. No full feature or G3/G4 completion claim.

Every remaining partial item is enumerated in the task table: 003 T303/T305/T308/
T309/T310/T306; 007 T0705/T0706/T0707; 004 T401/T404/T407/T408/T409/T406; deferred
004 T402/T403/T405. All remaining UI work belongs to the orchestrator. No blocked
question paused independent work or enabled an unsupported feature.

## Actual command log

All Python commands use the exact owner-specified interpreter. Tests/conftest.py
disables providers/tracing and creates isolated temporary databases. All new data
and rule packs are synthetic. Failed tests are recorded, not counted complete.

**E1**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_e.py tests/allocation tests/portfolio tests/tax -q -p no:cacheprovider -W ignore`
Result: **2 failed, 83 passed in 20.65s**. Two stale/future fixtures accidentally
made expiry equal price date and failed schema validation before their intended
coverage assertions. Corrected fixture dates; validation remained strict.

**E2** (same exact command as E1)
Result: **92 passed in 25.90s**. Intermediate before shared-capacity/last review.

**E3**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_e.py -q -p no:cacheprovider -W ignore`
Result: **45 passed in 25.99s**. Includes shared FIN-14 capacity and goal-funding handoff.

**E4**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_e.py tests/allocation tests/portfolio tests/tax tests/migrations/test_allocation_migration.py -q -p no:cacheprovider -W ignore`
Result: **95 passed in 30.01s**. Intermediate before final unavailable-source review.

**E5 final focused review/acceptance** (same exact command as E4)
Result: **96 passed in 29.38s**. All implementation/test changes at that point
preceded this run; the later parser/version-fencing review is covered by E8b/E9.
Includes numerical goldens, 4 extra rebalance fixtures, live two-session SQLite
CAS/replay, API authentication/ownership, deficits, shared planning/goal capacity,
staleness/history, sample tax gate/conflicts/refresh, migration/recovery and privacy.

**E6 final full backend suite**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Result: **1 failed, 422 passed, 8 skipped in 9930.47s (2:45:30)**. Failure was
the pre-existing Stage D budget API test: response lacked `revision` at its final
PUT (KeyError). Its status/body were not captured in that assertion, so no cause
is claimed. No Stage D implementation/test was changed. Focused reproduction and
the final full rerun below determine the final outcome. E6 also preceded the last
CSV/header and portfolio-rule-version review changes; it is not final evidence.

**E7 explicit existing browser suite**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore`
Result: **18 passed in 65.83s**. Existing HTML regression only, not the new backend UI.

**E8 final parser review**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_e.py -q -p no:cacheprovider -W ignore`
Result: **47 passed in 26.48s**. Final review added malformed quoted-header rejection
(422, no parser exception) and then explicit portfolio arithmetic-version fencing
for saved allocation inputs. The latter is covered by the final run below.

**E9 authoritative final full backend suite**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Result: **423 passed, 8 skipped in 392.60s (0:06:32)**. All final code/test edits
preceded this invocation. Together with E7: **441 passed, 8 skipped** across the
backend and explicit browser suites. Eight skips remain the six explicitly public
authentication-route cases and two opt-in PostgreSQL tests; they are not passes.
The earlier Stage D failure did not recur. No full-feature UI, CI, independent
external review or PostgreSQL evidence is claimed.

**E8b focused reproduction and final lane tests**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_d.py::test_resource_api_revisions_idempotency_and_wrong_owner tests/test_stage_e.py -q -p no:cacheprovider -W ignore`
Result: **49 passed in 25.05s**. Both existing budget/obligation cases and all 47
lane E cases passed after the final code edits. The E6 failure did not reproduce;
no unrelated Stage D change was made. No root cause is asserted without evidence.

Final repository checks: `git diff --check` passed. Only the permitted include_router
line changed in backend/main.py; frontend and shared progress/handoff files are
unchanged. The test-generated evals/results/latest.json metadata was restored to
the initially clean HEAD content via read-only git show and the requested Python,
preserving core.autocrlf=true checkout line endings. All lane changes remain in
the working tree for orchestrator review/commit. No git add/commit/push attempted.
