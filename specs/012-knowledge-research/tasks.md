# Tasks — Financial education, evidence retrieval and research agents

**Planning backlog only.** Build prerequisites and pilot subsets follow [implementation order](../implementation-order.md). Read [spec](spec.md) and [plan](plan.md). Use dependency stages, not numerical task order. A task may cover several requirements; the implementation handoff must complete the requirement-to-test matrix for all requirements.

- [ ] **T1201** Create source registry and ingestion policy. Location: `knowledge_base/ and backend/knowledge/`. Requirements: F012-FR01, F012-FR06.
  - Done when: License/effective-date/expiry required; unapproved source cannot enter production index.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1202** Implement scoped retrieval and citations. Location: `rag/ and backend/services/`. Requirements: F012-FR02.
  - Done when: Wrong-tenant and stale-source tests fail closed; citations resolve to relevant authorized evidence.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1203** Implement education and intent boundaries. Location: `agents/ and frontend/`. Requirements: F012-FR03.
  - Done when: Generic question cannot trigger mutations or bypass personalized-advice gate.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1204** Implement instrument/financial data contract. Location: `backend/integrations/market_data/`. Requirements: F012-FR04.
  - Done when: Exchange/currency/period mismatches and missing values are rejected or shown unavailable.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1205** Implement optional research calculations. Location: `engines/research/`. Requirements: F012-FR05.
  - Done when: Independent ratio/DCF/bond fixtures pass; all forecasts labeled assumptions.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

- [ ] **T1206** Run held-out research evaluations. Location: `evals/research/`. Requirements: F012-FR02, F012-FR06.
  - Done when: No unsupported numerical claims in release suite; expiry and document injection tested; record research release decision.
  - Evidence: implementation revision, automated results and applicable browser/operational record; currently pending.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
