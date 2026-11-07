# Implementation plan — Reliable analysis and account safety

Read [spec](spec.md), [baseline](../baseline.md), and [agent controls](../agent-quality.md).

## Technical context and constitution check

Retain Python, FastAPI, SQLAlchemy, and Streamlit. Use a reproducible Python 3.13 environment if dependencies resolve there. Record a different supported version if required. Pin dependencies and use pytest with a fast offline suite plus disposable PostgreSQL integration tests. Introduce Alembic migrations and select engine options by backend. Keep SQLite available for deliberate local use during transition if compatibility tests pass. Establish a supported legacy import path with dry-run counts and a backup. Assign initial profile revisions during migration. Exclude legacy inferred credit defaults and projected portfolio values from claims of verified data. Code owns money and identity. No external observability connection is required for correctness.

## Implementation structure

- `backend/core/{config,auth,database,dependencies}.py` configuration, claims, hashing and database wiring. Separate token signing from password hashing. If legacy hash verification needs the historical secret, scope it to rehash-on-success or choose a password reset plan. Avoid silently locking out all users.
- `backend/models/`, `backend/schemas/`, `backend/services/{profile_service,analysis_service,chat_service}.py` revisions, typed contracts, idempotency, and a canonical finance snapshot. Use nullable status fields or explicit availability states. Preserve existing endpoints where possible, with additive response fields and documented behavior changes.
- `engines/financial_health_engine.py`, `agents/{graph_executor,summary_agent,optimizer_agent,rebalance_agent}.py` deterministic results and output validation. Distinguish failed, degraded, stale, and complete. Tag rule and prompt versions.
- `frontend/app.py` wire profile/scenario edits, shared current facts, stale status, one send action, provider retry and readable errors. Split components only as needed for these paths.
- `utils/llm_brain.py` bounded calls and privacy-safe instrumentation. Use allowlisted structured telemetry with tracing disabled by default.
- `migrations/`, `tests/`, and `.github/workflows/` migration, deterministic tests, CI, and setup documentation.

## Rollout and failure recovery

Backup first. Validate migrations on synthetic legacy fixtures and compare record counts and relationships before and after. Keep a tested restore or forward recovery plan. Roll out to staging, exercise the browser paths, then review stop-ship evidence. Product advice filters, raw trace controls, and signing-secret checks must be active before exposure to customer data.

## Shared implementation contracts
Read [architecture](../architecture.md), [financial rules](../financial-rules.md), [implementation order](../implementation-order.md), [evaluation plan](../evaluation-plan.md) and [release gates](../release-gates.md). Use shared snapshot and privacy services. Implement only the selected slice. Module paths are proposed boundaries; document any adjustment without weakening acceptance. Complete [acceptance mapping](acceptance.md) with actual test evidence.
