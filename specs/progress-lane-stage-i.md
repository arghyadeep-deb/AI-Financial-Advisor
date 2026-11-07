# Lane I — allocation and portfolio acceptance

2026-11-07. Working tree based on integration `c61e22f`; changes intentionally uncommitted
per the common addendum (overrides the earlier local-commit instruction). No push.
Read implementation order/progress/handoff, existing lane remaining sections,
007/003 spec/plan/tasks, financial rules, agent quality, constitution and release
gates. User selection authorizes the otherwise planning-only specs.

## Sequential task evidence

### 007 T0701 — done (selected offline backend contract)

Files: `backend/finance/suitability/__init__.py`,
`backend/services/portfolio_service.py`,
`tests/allocation/test_stage_i_suitability.py`.
Reuses versioned immutable suitability answers and owner-scoped portfolio revisions.
Missing material facts, tolerance/capacity conflict, near essential goal and unstable
income produce explicit review reasons and a new-revision resolution. Responses
include a deterministic assessment; no age/income inference or LLM authority.
New revisions preserve the versioned assessment in the existing immutable request
JSON. Legacy answers are assessed on read without rewriting history. Retry
comparison excludes that derived receipt field, preserving replay compatibility.

Command (actual):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation/test_stage_i_suitability.py tests/allocation/test_allocation.py -q -p no:cacheprovider -W ignore`
Result: **31 passed in 3.10s**. Synthetic SQLite fixtures, providers disabled.
Limitations: owner declarations are unverified; frontend remains orchestrator-owned
and on hold. This contract completion is no G4/public release approval.
Migration/recovery: no schema/new store; existing PortfolioRevision privacy hooks
and immutable history reused. Reverting response assessment preserves all data.

### 007 T0702 — done (illustrative offline universe contract)

Files: `engines/allocation/contracts.py`, `backend/finance/allocation_sources.py`,
`knowledge_base/allocation/{README.md,synthetic-v2.json}`,
`tests/allocation/test_stage_i_assumptions.py`.
Added a separate versioned cash/debt/equity/gold universe, dated illustrative
annual return/volatility, fees, shocks, bounds and liquidity. Every field inherits
the pack's owner/effective/expiry/hashed source. The shared registry enforces
ownership, latest source, approval and freshness. Legacy v1 remains supported.

Actual command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation/test_stage_i_assumptions.py tests/allocation/test_allocation.py -q -p no:cacheprovider -W ignore`
First run: **1 failed, 21 passed** (test incorrectly used a nonexistent registry
withdrawal field). Corrected fixture to append an unapproved source revision, the
shared registry's existing withdrawal contract. Rerun: **22 passed in 2.50s**.
Limitations: invented parameters await owner approval; no licensed/live facts,
forecast or probabilistic risk claim. Production registry empty, public gate off.
Migration/recovery: none; retain old pack file and stored immutable input JSON.

### 007 T0703 — done (deterministic engine)

Files: `engines/allocation/{__init__.py,contracts.py}`,
`tests/allocation/test_stage_i_solver.py`.
Extended the existing transparent bounded allocator to both versioned universes.
Exact ceil minima/floor maxima, stable residual order, cash floor, exclusions,
maximum liquidity days and sourced concentration bounds. Risk caps use the lower
of declared tolerance and capacity; near-term needs/unstable income forbid equity
and gold. No expected-return optimization. Infeasible integer constraints return
no amounts; unknown inputs and wrong-owner snapshot fail closed.

Actual command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation -q -p no:cacheprovider -W ignore`
Result: **77 passed in 2.86s**, including independent four-class 20/30/40/10
golden and 36 exact-cash/exclusion cases. No external integration.
Limitations: conservative illustrative risk policy needs owner approval; no
covariance optimizer or approved personalized proposal. Migration/recovery: none;
new results report allocation.v2; stored v1 history is not mutated.

### 007 T0704 — done (offline comparisons)

Files: `engines/allocation/costs/__init__.py`,
`tests/allocation/test_stage_i_costs.py`; consumer integration in
`backend/{schemas/portfolio.py,services/allocation_service.py}`.
Reuses cost comparison/rebalance arithmetic; adds four-class contribution-first
and sale alternatives, exact resulting holdings and explicit unknown-cost block
on net improvement. No tax/saving fabricated even when basis is supplied, because
no approved disposal rule pack is available. Rejects unsupported holdings rather
than silently dropping gold; aggregate limits remain enforced. Sandbox uses v2
and accepts closed-class exclusions, cash floor and maximum liquidity days.

Actual engine command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation -q -p no:cacheprovider -W ignore`
Result: **83 passed in 2.79s**. Consumer integration acceptance runs below.
Limitations: fees are annual illustrative estimates on new contributions only;
transaction costs, exit loads and taxes unknown, net improvement always blocked.
Migration/recovery: no new table/store; existing registered AllocationPlan and
PortfolioRevision retain immutable inputs/results. Disable sandbox to stop new
work; retain files/old snapshots for inspection. No execution adapter exists.

### 003 T306 — partial (offline backend acceptance passed)

Files: `tests/portfolio/test_stage_i_acceptance.py`,
`tests/portfolio/test_stage_i_advice_gate.py`,
`tests/allocation/test_stage_i_history.py`, the shared services above, and
`tests/test_stage_e.py` (only adapts the outage mock to the versioned loader
argument). No new proposal, source, auth, privacy or portfolio implementation.

Review checklist disposition:

- Positive and wrong-owner API checks: owned holdings/suitability/valuation/plan
  queries return the same missing/foreign 404; route-wide auth regression rerun.
- Observations remain exact and unchanged after hypothetical contribution/shock
  and health analysis. Corrected price revision invalidates the old plan while
  its original inputs/result remain inspectable. No projection added to holdings.
- Missing source/version/date/expiry, expired/future prices and non-INR currency
  make total/performance unavailable, with an explicit priced-subset scope.
  Licensed source verification remains unavailable; owner declarations are not
  relabeled as verified facts or eligible verified net worth.
- Independent concentration golden aggregates two instruments from one issuer;
  issuer shares 1/4 and 3/4 produce HHI 5/8. Unknown issuer/class exposure remains
  separate; incomplete coverage never implies low risk or a complete HHI.
- Four-class sandbox request, exclusions/liquidity, gold holdings, replay, stale
  source revision, public gate/environment bypass and hostile model override
  tests pass. No new execution path; model output cannot replace canonical facts.
- Found/fixed during self-review: low tolerance previously allowed high-capacity
  equity exposure; gold could be omitted by the three-class rebalance; new default
  request fields could conflict with old idempotency receipts; empty explicit
  bounds incorrectly fell back to pack bounds. All have regression coverage.
- Additional advice-gate review found the legacy shared guard trusted the named
  product environment flag alone, and chat skipped product checks without a
  profile. `backend/services/{output_guard.py,chat_service.py}` now consume the
  shared hard-false public gate and apply the existing product guard independently
  of profile availability. Normal and final streamed replies with/without a
  profile are tested using mocked hostile provider output.
- Existing registered-store export/purge, privacy, metadata-only spans, immutable
  history, concurrent revision/idempotency and planning-capacity tests reused.

Actual commands/results in sequence:

1. `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation tests/portfolio tests/test_stage_e.py -q -p no:cacheprovider -W ignore`
   **142 passed in 16.25s** after v2 consumer integration.
2. `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/portfolio tests/allocation tests/test_stage_e.py tests/api/test_tenancy.py tests/contracts -q -p no:cacheprovider -W ignore`
   **262 passed, 7 skipped in 126.99s** (public routes only). This run preceded
   the final history/default-normalization and empty-bounds review fixes.
3. `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation tests/portfolio tests/test_stage_e.py -q -p no:cacheprovider -W ignore`
   **153 passed in 28.57s** including versioned assessment/history compatibility;
   preceded only the final explicit-empty-bounds regression (full run below).
4. `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/portfolio tests/allocation tests/api/test_chat.py tests/finance -q -p no:cacheprovider -W ignore`
   **178 passed in 50.04s**, after the shared advice gate/no-profile chat fixes.

Remaining acceptance: new portfolio/allocation UI/browser walkthrough and chat
owned-holdings context consumer (frontend on hold), licensed price/source
governance and freshness decisions, approved public universe/legal applicability,
independent reviewer/held-out evaluation and production/PostgreSQL operational
evidence. Existing named-product recognition is a finite regex denylist, not an
exhaustive securities classifier. Legacy SSE emits provisional model chunks before
the final validated replacement; broader pre-display streaming validation remains
missing. Keep providers disabled. Existing browser tests are regression evidence
only. This self-review
is not independent Codex/external acceptance or G3/G4/G5 approval. No shared task
checkbox changed. Migration/recovery: no schema/new tables, existing registered
stores retained; no migration from 0141 needed and 0160..0169 remain unused.

## API integration notes for the orchestrator

- Existing `POST /portfolio/suitability` and GET history now include `assessment`
  with rule/questionnaire versions, revision, status, blocking reasons/resolution,
  declaration basis and hard-false public eligibility. Incomplete answers may be
  saved to resolve through a later immutable revision; they block allocation.
- Existing `POST /allocation-scenarios` adds optional `excluded_assets` (closed
  class list), `liquidity_floor_bps` (default 1000), `maximum_liquidity_days`
  (default null). Existing fields, CAS and idempotency remain. Optional defaults
  are filled when comparing old receipts; stored requests/results stay unchanged.
- Sandbox defaults off; even an environment opt-in is unavailable in production.
  It consumes `allocation.illustrative.v2`, cash/debt/equity/gold, effective
  2026-11-07 and expiring 2027-01-01. Old v1 plans become stale under the new
  assumptions, while their historical values remain readable.
- `allocation.v2` risk caps: equity low/moderate/high = 10/40/60%; gold = 0/10/20%;
  lower of declared tolerance/capacity, both zero for near-term needs (<36 months)
  or unstable income. These are conservative illustrative policy, not approved
  professional advice. The pack's minimum/maximum bounds always also apply.
- `comparison.contribution_first.resulting_holdings_paise` adds the proposed new
  contribution to current owned observations, with fees explicitly scoped to the
  new contribution. Unknown holdings stay null. Net improvement stays null with
  `net_improvement_status=blocked_unknown_costs`; no supported tax pack is assumed.

## Decisions / open owner questions

- D05/D11/D12 remain unresolved: asset classes only; named products and public
  proposals remain hard-false. No card pitch, provider, filing, trading or billing.
- Four-class dated illustrative return/volatility pack and risk/liquidity bounds
  are assumptions awaiting owner approval, usable only in an opt-in synthetic
  development/test sandbox. Production source registry stays empty.
- Historical v1 assumptions/plans remain inspectable; no rewriting old snapshots.
- Owner must approve specific return/volatility/shock/fee parameters, annual
  horizon and 2027-01-01 expiry; class concentration/risk caps, 36-month near-term
  rule, default 10% cash floor and seven-day illustrative class liquidity; choose
  reviewer/source rights and any future tax/disposal cost pack. Safest default is
  the opt-in synthetic fixture, no named products, unknown sale costs and no
  public publication until those decisions and independent evidence exist.
- No shared-owner work assumed complete: real-data privacy/restore/deployment,
  source licences, provider/consent/budget wiring, CI, mail/MFA, and production
  operational approvals remain as documented by lanes B-G.

## Remaining

Only T306 is partial, for the acceptance gaps above. T0701-T0704 are completed for
the selected offline backend contracts, not a release decision. Final backend and
browser regression results are recorded below. Frontend and
backend/main.py untouched; external integrations disabled; no add/commit/push.

## Final verification

Browser regression command (run once in this lane):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore`
Result: **18 passed in 56.58s**. Existing local Chromium/fictional-account UI
only; not new portfolio/allocation UX evidence. This run preceded the final legacy
advice-guard fix; the final backend run below includes that fix and its API tests.

Backend command (run twice; second run after all final code changes):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
First run: **604 passed, 9 skipped in 339.38s (0:05:39)**. This preceded the
last shared advice-gate/no-profile chat fixes and two new parametrized cases;
it is not the final-code evidence.

**Authoritative final backend result: 606 passed, 9 skipped in 371.61s (0:06:11).**
All final code changes preceded this invocation. Together with the single explicit
browser run: **624 passed, 9 skipped** across backend/browser regression evidence.
Nine skips are seven
explicitly public-route cases and two opt-in PostgreSQL cases, never counted as
passes. No PostgreSQL/live provider/CI/public deployment run.

`git diff --check` passed. The initially clean test-generated
`evals/results/latest.json` revision metadata was restored with the required
Python using read-only `git show HEAD:evals/results/latest.json`, preserving
core.autocrlf=true checkout line endings. No user edits/data, shared progress or
handoff, frontend, main.py, database/models/migrations, or other lanes were edited
(except the one existing lane E outage-mock signature adaptation listed above).
All work remains in this worktree for orchestrator review/commit. No git
add/commit/push or external integration/deploy occurred.
