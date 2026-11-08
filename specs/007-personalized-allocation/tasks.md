# Tasks — Personalized allocation and portfolio optimization

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [x] **T0701** Implement suitability and contradictions. Location: `backend/finance/suitability/`. Requirements: F007-FR01.
  - Done when: Missing horizon or a capacity conflict blocks personalized proposal with a useful explanation.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T0702** Define universe and assumption pack. Location: `knowledge_base/allocation/`. Requirements: F007-FR02.
  - Done when: Each assumption has date, source, owner and expiry; stale or unavailable facts fail closed.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T0703** Implement feasible allocation solver. Location: `engines/allocation/`. Requirements: F007-FR03.
  - Done when: Weights/cash conserve exact amounts; deficit, exclusions and impossible bounds return no feasible plan.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [x] **T0704** Implement cost-aware comparisons. Location: `engines/allocation/costs/`. Requirements: F007-FR04.
  - Done when: Missing cost basis never yields a fabricated tax saving; contribution-first alternative is included.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0705** Create plan snapshots and UI. Location: `backend/models/, backend/controllers/, frontend/`. Requirements: F007-FR05, F007-FR06.
  - Done when: Plan is immutable and stale after any material source revision; users see assumptions before accepting a draft.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0706** Add stress, baseline and held-out evaluations. Location: `tests/allocation/ and evals/allocation/`. Requirements: F007-FR05.
  - Done when: Unseen constraint cases pass; no look-ahead data in backtests; deterministic repeatability documented.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T0707** Prove public recommendation gate. Location: `backend/core/feature_flags and tests/`. Requirements: F007-FR02, F007-FR06.
  - Done when: API and chat cannot bypass gate; no execution tool exists; record eligibility evidence before launch.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

## D05 additional acceptance (lane I2)

No feature-wide checkbox is completed by this addendum. Record executed evidence
and remaining acceptance in specs/progress-lane-stage-i2.md only.

- T0702: every scalar has versioned provenance, methodology, uncertainty, status
  and exclusive expiry; missing, altered or expired register/source fails closed.
  Synthetic assumptions cannot be loaded for development/production recommendations.
- T0701/T0703: configurable cash floor and near-term boundary have positive/invalid
  tests and unvalidated_prototype labels; no hidden fixed policy overrides them.
- T0703/T0705: missing liquidity remains unknown, cannot satisfy a deadline, and
  only dated instrument/restriction/settlement evidence supplies a duration.
- T0704/T0706: exact conservation, costs, scenarios, deterministic repeatability,
  immutable receipts, expiry/staleness and hostile explanations remain covered.
- T0707: default real calls refuse "assumptions not validated"; public eligibility
  is hard-false independently. Parameter validation and the separate public-advice
  decision remain PENDING, no reviewer appointed. Execution/named products absent.
