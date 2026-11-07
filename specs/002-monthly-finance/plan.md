# Implementation plan — Monthly Finance Agent

Read [spec](spec.md), [data model](data-model.md), [API contract](contracts/import-and-report.md), [quickstart](quickstart.md), and [agent controls](../agent-quality.md). Depends on 001 tenancy, exact money, versioning, migrations, and CI.

## Technical context

FastAPI, the HTML/CSS/JS web app, PostgreSQL, private object storage, one background worker, and a pinned compatible LangGraph/checkpointer stack. Reuse the SQLAlchemy project boundaries. Use a PostgreSQL-backed job queue or another documented durable worker strategy with an atomic claim, bounded retries, and idempotency. For the pilot use a deterministic text parser plus synthetic fixtures. Keep the request handler responsive by returning a job reference after storage succeeds. Set file/page/row/timeout limits based on fixture benchmarking and expose these limits in UI.

## Design and constitution check

- `backend/controllers/statement_controller.py` owns API authorization and request validation. `backend/services/statement_service.py` owns document and job transitions. Place versioned adapters under `backend/finance/importers/`.
- `backend/finance/ledger.py` owns exact-money balance checks, fingerprints, overlap handling, and transactional publication. A single immutable origin row can map to a canonical ledger entry with multiple pieces of evidence. Serialize overlapping commits per account and guard report revisions against stale computation.
- `agents/monthly_finance_graph.py` builds a typed StateGraph. Nodes call deterministic services. Place the review interrupt in a replay-safe node. Configure persistent checkpoints in the worker. Treat application DB job state as authoritative if a checkpoint replay follows a committed transaction.
- `backend/services/monthly_report_service.py` computes report snapshots and exports. Pass only an allowlisted summary to the explanation node. If explanations fail, publish the canonical report with a degraded narrative status. Keep raw customer files and rows out of LangSmith and model calls.
- `frontend/` adds Upload, Review Transactions, Monthly Report. Preserve current navigation. Show partial or unverified coverage, blocked balances, and import history. UI stores no long-lived object credentials.
- `tests/fixtures/statements/`, `tests/integration/`, and `evals/` contain synthetic cases for parser correctness, retry and tenancy, and prompt attacks. Required tests run offline.

## Phases and launch checks

First prove an upload with a single known layout. Then add review/resume, cross-account match candidates, report/export, and undo. Feature-flag the pilot. Record staging timing, report accuracy, restore recovery, and trace payload tests. If a parser change regresses, stop new jobs for that parser version and retain existing source/evidence revisions for a controlled reprocess.

## Shared implementation contracts
Read [architecture](../architecture.md), [financial rules](../financial-rules.md), [implementation order](../implementation-order.md), [evaluation plan](../evaluation-plan.md) and [release gates](../release-gates.md). Use shared snapshot and privacy services. Implement only the selected slice. Module paths are proposed boundaries; document any adjustment without weakening acceptance. Complete [acceptance mapping](acceptance.md) with actual test evidence.
