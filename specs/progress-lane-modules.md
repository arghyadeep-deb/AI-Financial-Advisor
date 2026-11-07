# Independent modules lane

Branch: codex/modules. No remote pushes or external integrations.

## Knowledge slice

- T1201 partial (reviewed file-backed registry contract tested): `backend/knowledge/registry.py`,
  `knowledge_base/SOURCE_POLICY.md`. Immutable versions, licence/reviewer/dates/hash,
  host allowlist, expiry, stable ownership and correction invalidation. No production
  sources approved. Legacy production-index integration and ingestion review tooling
  remain missing; this is not a claim that all existing retrieval is governed.
- T1202 partial: exact-topic authorized retrieval and citation revalidation implemented;
  semantic entailment is a human review prerequisite, not automated or claimed.
- T1203 partial: curated education service, no tools or mutations; chat/report/UI integration missing.
- T1204 partial: exact instrument/period/basis contract and disabled adapter; licensing,
  dated source validation at research publication and live feed absent.
- T1205 partial: ratio and discounted-cashflow assumption arithmetic; bond-specific
  scenarios, sensitivities and full statement definitions missing.
- T1206 partial: negative expiry/correction/injection fixtures run; independent held-out
  release evaluation and operational/browser review absent. Research release disabled.
- Files: `backend/knowledge/{registry,education,research}.py`,
  `tests/knowledge/test_registry.py`, policy above.
- Actual command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/knowledge -q -p no:cacheprovider -W ignore`
  Result: **8 passed in 1.51s**.
- Decision: empty production catalog; synthetic example.test is test-only. Existing
  legacy RAG/JSON corpus is not approved by this implementation and is not migrated.
  New registry consumers must use this boundary; legacy RAG integration remains open.
- Telemetry reuses metadata-only tracer. No source payload logging added.
- Migration/recovery: no tables or migrations; reviewed catalog resides in code/artifacts.
  Disable consumers before reverting catalog; retained citations require revalidation.

## Local commit blocker and remaining work

Attempted `git add backend/knowledge/registry.py backend/knowledge/education.py backend/knowledge/research.py knowledge_base/SOURCE_POLICY.md tests/knowledge/test_registry.py specs/progress-lane-modules.md`
and `git commit -m "Add reviewed evidence registry and offline education research contracts" -m "Co-Authored-By: Codex <noreply@openai.com>"`.
Both failed: Git cannot create
`C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.git/worktrees/AI-Advisory-modules/index.lock`
(Permission denied). This metadata path is outside the authorized writable worktree.
No commit created; no permission bypass attempted. Stopping at the coherent knowledge
slice under the product owner's rule to stop when a step cannot be completed safely.

- Feature 012 remains partial for the missing work itemized above.
- Feature 007 T0701–T0707 unstarted: suitability contracts, sourced assumption pack,
  allocator, cost comparisons, immutable plans, output_guard integration and goldens,
  public/named-product gate acceptance all remain. No proposal endpoint was added.
- Conditional feature 004/003 engines unstarted because 012 and 007 are unfinished.
- Frontend and backend/main.py untouched. No migrations needed or created.

## Full regression verification

Actual command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore`

Output: `173 passed, 8 skipped in 61.79s (0:01:01)`.
The original suite stays green; eight new offline fixture tests pass. Skipped
checks remain skipped, not counted as successful validation. No browser, live
provider, CI or PostgreSQL run performed in this lane.

## Continuation: allocation and deterministic engines (2026-11-07)

User explicitly authorized this continuation despite planning-only headings in
the specs. The earlier Git metadata blocker is superseded: **no git add, commit
or push attempted in this continuation**. Orchestrator owns commits. Initial
working tree already had `evals/results/latest.json` modified; left untouched.
No frontend, backend/main.py, shared progress/handoff, local DB or secrets edited.

### Feature 007 task results

Commands actually executed from this worktree, using the owner's Python:

- A: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/allocation tests/migrations/test_allocation_migration.py -q -p no:cacheprovider -W ignore`
  Result: **16 passed in 1.97s**.
- B: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore`
  Intermediate result before tax/portfolio additions: **189 passed, 8 skipped in 57.01s**.
  Final result after additions and flag-reader reuse fix: **222 passed, 8 skipped in 55.91s**.

Each task below was verified by command A, then by final command B. These are
backend synthetic-slice completion statements, not permission to release 007.

- **T0701 done (backend suitability acceptance)**. Files:
  `backend/finance/suitability/__init__.py`, `tests/allocation/test_allocation.py`.
  Strict frozen questionnaire v1, answer revision, explicit missing fields,
  essential-goal contradictions, tolerance/capacity conflict, unstable-income
  conflict. Missing horizon and short essential/high tolerance block with reasons.
  Tests: `test_suitability_conflicts`, `test_low_capacity_and_short_horizon_constrain_equity`.
  Limitation: answers live within immutable plan inputs; no standalone questionnaire
  editing/history API or UI. No migration needed for this embedded contract.
- **T0702 done (synthetic-only pack acceptance)**. Files:
  `engines/allocation/contracts.py`, `backend/finance/allocation_sources.py`,
  `knowledge_base/allocation/{synthetic-v1.json,README.md}`.
  Each class bound, liquidity assumption, fee and return shock inherits pack
  effective date, expiry, owner and exact hashed source; source payload must equal
  the supplied pack. Reuses `backend/knowledge/registry.py`; no second registry.
  Test: `test_expiry_correction_unapproved_and_tamper` includes expiry, unavailable
  production catalog, private evidence and withdrawn/corrected versions.
  Limitation/disabled: invented asset-class test parameters only; no licensed or
  production-approved evidence, named security universe, market quotes or live feed.
  Recovery: stop consumers before removing fixture; old citations revalidate.
- **T0703 done (deterministic sandbox allocator acceptance)**. Files:
  `engines/allocation/{__init__.py,contracts.py,README.md}`, allocation tests.
  Consumes FinanceSnapshot, caps contribution by separately declared eligible cash,
  refuses unavailable/zero/deficit cases, enforces exclusions, bounds, capacity and
  liquidity, and conserves integer paise. Stable rounding and priority documented.
  Tests: `test_independent_cash_cost_stress_goldens`,
  `test_zero_deficit_unknown_refuse`, `test_liquidity_exclusions_integer_rounding`,
  `test_invalid_contracts_and_wrong_snapshot_owner`.
  Limitation: transparent synthetic policy, not a return optimizer; declared profile
  cash is not ledger-verified coverage. Public use disabled. No tables for engine.
- **T0704 done (unknown-cost acceptance)**. Files:
  `engines/allocation/costs/__init__.py`, allocation golden test above.
  Contribution-first alternative has no sales; current allocation and all-cash
  contribution baseline included. Synthetic annual fee comparison uses aggregate
  exact numerators and one conservative rounding. Sale taxes, exit loads and
  transaction costs explicitly unknown/excluded; no net-improvement or tax-saving
  claim, even with supplied unverified basis. Limitation: disposal/tax adapter and
  supported disposal pack absent. No migration or external integration.
- **T0705 partial**. Files: `backend/models/models.py`,
  `migrations/versions/0050_allocation_plans.py`,
  `backend/services/allocation_service.py`, `backend/services/output_guard.py`,
  `tests/migrations/test_allocation_migration.py`, allocation tests.
  Immutable append-only input/result evidence, owner-filtered reads with identical
  wrong-owner/missing 404, expected-profile-revision rejection, separate stale flag
  for profile/suitability/holdings/assumption/source-expiry changes. Guard discards
  every model field, including amounts, products and eligibility. Tests:
  `test_owned_immutable_stale_history`, `test_guard_gate_and_no_http_surface`,
  `test_allocation_upgrade_downgrade_recovery`.
  Missing: orchestrator UI (assumptions/acceptance/stale presentation), authenticated
  scenario router, standalone owned holdings/suitability revision stores, complete
  vector fencing under concurrent changes, idempotent request replay, privacy
  export/deletion hooks and browser evidence. No public proposal is shown.
- **T0706 partial**. Files: allocation cost/stress engine and golden tests.
  Independently hand-calculated contribution, allocation, fee, baseline and bounded
  adverse/upside fixture results; deterministic repeatability; delayed-income
  contribution zero. No backtest is claimed. Missing: independent held-out release
  family/evaluation artifact, volatility model, dated fee-inclusive backtests and
  operational/browser acceptance. No model/provider or external evaluation run.
- **T0707 partial (fail-closed gate implemented and tested)**. Files:
  `backend/core/feature_flags.py`, existing `output_guard` extension, allocation
  service and `test_guard_gate_and_no_http_surface`.
  Public proposal gate hard-false regardless of environment/model arguments.
  Reuses the existing NAMED_PRODUCT_RECOMMENDATIONS reader (default off); even
  enabling it cannot enable allocation publication. There is no allocation API,
  chat tool, export, or execution tool to bypass this service gate.
  Missing: D05 applicability/eligibility artifacts, independent release evaluation,
  production-approved source/universe, full cross-surface acceptance when adapters
  exist. This is not a claim about every legacy advice surface's eligibility.

### Allocation migration and recovery

- Revision **0050**, `down_revision = "0003"` (exact existing head read from 0003
  migration). One table `allocation_plans`, owner FK/index, input profile and
  suitability revisions, immutable JSON snapshots and creation time. ORM columns
  match migration, verified by migration test.
- Real isolated SQLite upgrade 0003 -> 0050, empty downgrade -> 0003, forward
  recovery -> 0050 and nonempty downgrade refusal executed. SQL UPDATE trigger
  rejects mutation; existing evidence survives refused downgrade. PostgreSQL
  trigger SQL supplied but **not executed**; PostgreSQL verification remains open.
- No real database migrated. New tables are empty for legacy users. Before rollback,
  disable new allocation work and retain/export history or restore a pre-upgrade
  backup using the shared migration/recovery workflow. Nonempty downgrade deliberately
  refuses silent destruction. Authorized privacy deletion remains a separate owner.

### Decisions, conflicts and disabled features

- Safest D05 default is internal hypothetical asset-class scenarios only. No router
  was necessary for this slice; `backend/main.py` remains untouched. UI acceptance
  remains partial because frontend is explicitly owned by the orchestrator.
- Eligible liquid cash must be supplied explicitly after commitments/reserves;
  shared profile cashflow alone cannot establish verified ledger liquidity. Missing
  cash blocks; no alternate affordability implementation was introduced.
- Source governance remains the existing registry. Synthetic example.test approval
  is test-only; production registry is empty. Assumptions never come from LLM prose.
- No free-text model explanation is published for allocation; deterministic amounts
  remain inspectable even when malicious output is supplied. No external calls,
  market data, billing, filings, orders, deploy, telemetry export or remote pushes.
- Suitability/holdings revision arguments are trusted internal adapter inputs for
  now, not public user authorization. No API exposes arbitrary owner/revision inputs.
  Full privacy lifecycle and concurrent source-vector fencing remain open under T0705.

### Feature 004 deterministic tax engine — partial

- Task IDs: **T401/T404/T407/T408/T409 partial** (engine-only portions);
  T402/T403/T405/T406 remain outside this slice. Files:
  `engines/tax/{__init__.py,rules.py,README.md}`, `tests/tax/test_salary_rules.py`.
- Exact selected archived scope: FY2024-25 / AY2025-26 new regime, one resident
  salary employer, gross salary <= INR50 lakh, standard deduction only. Explicit
  evidence/conflict flags; unsupported periods/categories/deductions refuse.
  Versioned immutable pack includes official TRACES, PIB and 288A/B references,
  checked 2026-11-07. No statutory rates filled from model prose or adjacent period.
- Pure integer paise computation with slab breakdown, rebate, marginal relief,
  cess, statutory rounding and optional withholding settlement. Synthetic expected
  boundary values independently calculated in test comments; missing withholding
  keeps payable/refund unavailable.
- Actual command C (tax and portfolio together):
  `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/tax tests/portfolio -q -p no:cacheprovider -W ignore`
  Result: **33 passed in 1.65s**. Also passed final command B.
- Limitations/disabled: no production-approved pack, current-year claim, tax records,
  parser, Form16/AIS/26AS identity reconciliation, API, UI/export, interest/late-fee
  calculation, professional certification or filing. No tables or migration.
  Recovery: retain archived pack; replace with a new version rather than mutation.

### Feature 003 deterministic portfolio metrics — partial

- Task IDs: **T304/T305/T308 partial** (pure metric portions). T301-T303,
  T306/T307/T309/T310 remain outside this slice. Files:
  `engines/portfolio/{__init__.py,rules.py,README.md}`,
  `tests/portfolio/test_metrics.py`.
- Exact units (8 places), paise quotes, dates/source revisions/expiry; aggregate
  rational valuation then half-even money rounding; class/issuer exposures, exact
  issuer HHI and largest share on priced scope. Missing/stale/future/foreign quotes
  never become zero: priced subtotal shown, complete total unavailable. Duplicate
  instrument observations refuse. Unknown issuer never becomes a low-risk claim.
  Gain requires cost basis and explicit corporate-action support; shocks remain
  hypothetical. Versioned arithmetic conventions in immutable rules data.
- Actual command C above: **33 passed in 1.65s**, including portfolio tests with
  hand-derived 100000 paise total, 5/8 HHI, 3/4 largest share, 20000 paise gain,
  partial quote coverage, exact aggregate half-paise rounding and refusal cases.
  Also passed final command B.
- Limitations/disabled: no owned holdings/ingestion/source licensing service, DB,
  API, market feed, UI, XIRR/TWR/benchmark/volatility solver or execution. All return
  methods needing missing histories stay explicitly unavailable. No migration;
  engine rollback is code-only. Caller must supply owned, reviewed observations.

### Final verification and remaining handoff

- `git diff --check` ran successfully (exit 0). No git metadata writes attempted.
- Full tests use isolated SQLite databases and synthetic fixtures; model keys and
  tracing disabled by existing conftest. **8 skipped** are the existing six public
  route authentication exemptions and two opt-in PostgreSQL checks. No CI,
  browser, live provider, public deploy, tax filing or trade was performed.
- Remaining 007 work is exactly the partial-task gaps above: UI/owned upstream
  revision lifecycle, full fencing/retry/privacy integration, independent held-out
  and operational evaluation, and release eligibility. Tax and portfolio remain
  explicitly partial; no additional feature work was started.

Final actual command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore`

Final full-suite output: **222 passed, 8 skipped in 55.91s**.
