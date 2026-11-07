# Product architecture and cross-feature contracts

## Components
Keep the existing FastAPI/Python application and PostgreSQL as the durable business store. Add private object storage and a durable background worker. The frontend is plain HTML/CSS/JS in `frontend/static`, served by the API at `/app` under a strict CSP (owner decision 2026-11-07). No microservice rewrite is required. Financial services are deterministic and reusable from API, worker and chat. LangGraph coordinates long-running steps and user review. LangSmith is optional observability/experimentation and never authoritative storage.

## Shared records
Use owner IDs and opaque resource IDs on every record. Shared records: User, Session, ProfileRevision, Account, Document, ImportJob, LedgerTransaction/Evidence, ReportSnapshot, ConsentRecord, AuditEvent, Goal, Budget, Obligation, HoldingObservation, ValuationSnapshot, TaxCase, PlanSnapshot, HouseholdGrant, Notification and DeletionJob. Individual feature contracts add details. Every schema migration defines legacy behavior, nullable unknowns and rollback/forward recovery.

## Snapshot envelope
Every derived result carries `id`, `owner_id`, `schema_version`, `source_revision_vector`, `rule_version`, `created_at`, `as_of`, `coverage`, `status`, `metric_provenance`, and `missing_inputs`. Status uses complete/partial/unavailable/stale plus independent workflow and narrative states. A degraded explanation cannot turn a correct report into a failed import; a successful explanation cannot make incomplete source evidence complete. Provenance is authorized before serving; never expose another tenant's source ID.

## Async execution
Job creation and work scheduling use a durable outbox or an equivalent atomic design. Claim with expiring leases, fencing tokens and heartbeat; a stale worker cannot commit after replacement. Default bounded retries with jitter and retryable codes; poison jobs enter a recoverable failed state. External operations have unique operation keys and unknown-outcome reconciliation rather than blind retry. Database commits may precede graph checkpoint writes; resumption reads business state and does not repeat effects. Recheck ownership, consent and deletion status immediately before write/publication.

## API conventions
Generate versioned OpenAPI; money is paise integers or documented decimal strings, never binary floats in public money fields. Cursor pagination; structured errors `{code,message,request_id,retryable,field_errors}`; uniform missing/wrong-owner denial; 409 for revision conflicts; 429 with retry guidance. Idempotency keys are owner+operation scoped and bind to payload digest; reuse with different input returns conflict. Record expiration policy; permanent logical dedupe keys outlive request-key caches. Enforce limits before expensive work. Browser uses secure session design documented in 001/008; long-lived secrets never enter browser storage.

## Financial source precedence
Account statements establish cash activity; user corrections establish interpretation; holdings observations establish positions at a date; price feeds establish dated prices; tax records establish period-specific reported fields. Profile aggregates are user-declared estimates until replaced or reconciled with evidence. Never sum manual and imported observations of the same asset by default. Conflicting sources require review, and each report identifies its chosen scope.

## Read-only conversational contract
Resolve intent into an allowlisted read or scenario request, obtain authorized facts, compute deterministic outputs, and render facts with optional narrative. No arbitrary SQL, shell, browser navigation or model-selected remote endpoint. Free text, uploaded documents and retrieved pages cannot grant permissions. A proposed mutation requires a typed user action outside model prose. Store chat separately from authoritative finance data; corrections go through domain services.

## Dependencies
008 and 009 start with 001; their real-data gates precede any 002 pilot. 010 core journeys accompany 002. 006 core budgets follow ledger definitions; goals/debt depend on confirmed obligations. 003 feeds 007 and 011. 004 uses document review and its own rule packs. 005 adapters feed existing domain contracts. 012 retrieval is separate from private evidence. 013 entitlements never override privacy, correctness or account-access rights. 014 adapters reuse 002, never create a second ledger.
