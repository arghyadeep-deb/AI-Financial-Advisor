# Agent architecture, guardrails, observability and evals

## LangGraph orchestration

Self-host the graph in the existing FastAPI service and a background worker. Keep the current analysis API and deterministic calculators. Introduce a typed LangGraph `StateGraph` for 002. Candidate path:

`validate → extract → stage → reconcile → [review or accept] → categorize → publish → explain`

Use a PostgreSQL checkpointer and an opaque server-generated thread ID associated with exactly one tenant and import job. Store IDs, revision, stage, and bounded status codes in checkpoint state. Store PDFs, transaction details, and review edits in the application data model. Use `interrupt()` for unresolved review and resume with `Command(resume=...)` carrying an approved review reference. Verify tenant, expected revision, and current job status before resuming. A node that pauses can re-enter when resumed, so perform writes in separate idempotent nodes and keep effects before an interrupt replay-safe. Publish under one transactional lock or guarded version update. Checkpointer state assists recovery. The database remains authoritative for ledger and report state.

Use the same pattern for tax or portfolio only if durable pauses add value. Route direct arithmetic and reads to normal services. No autonomous agent swarm or free-form tool routing is required for the pilot. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) · [Interrupts and resumption](https://docs.langchain.com/oss/python/langgraph/interrupts)

## Guardrails and their owners

| Boundary | Required behavior |
|---|---|
| Upload and parsing | Validate authentication, type, signature, limits, scan result, ownership, and parser support. Treat document instructions as untrusted data. Give parsers no network. Flag suspicious files and unsupported layouts. |
| Tool calls and state | Allowlist tools per node. Use typed inputs and outputs. Enforce ownership and revision server-side on every job, document, row, and resume. Report intents use read-only tools. |
| Financial calculations | Exact amounts. Rule-based arithmetic, duplicate checks, balance checks, complete versus partial coverage, unknown fields, dated prices, and an explicit eligible budget. Reject an action that exceeds available cash or assumes assets the user never supplied. |
| LLM and narrative | Category suggestions and explanations use minimal sanitized context and an output schema. The app owns all numeric display values, source links, and actionable constraints. Reject unsupported claims. On error, show the deterministic report and an unavailable narrative status. |
| External actions | The core agent cannot trade, pay, retrieve bureau data, or file taxes. Later adapters have consent, authorization, provider checks, and independent release decisions. |

## Ownership and hard boundaries
The [evaluation plan](evaluation-plan.md) and [architecture](architecture.md) define test sets, schema and recovery. LangGraph coordinates work; it does not replace the worker queue, database transactions, authorization or financial engine. Nodes must validate current owner, consent, deletion state, source revisions and remaining work budget. Checkpointer writes and business commits are not assumed atomic. Use fenced, idempotent services on replay.

Guardrails are application controls with tests, not merely system prompts or an extra guardrail model. Enforce upload isolation, read-only tool allowlists, schemas, numeric provenance, missing-data behavior, suitability constraints, source freshness, permissions and quotas in code. No guardrail vendor dependency is mandatory. Any optional library must demonstrate coverage and fail-safe behavior against the same tests.

## LangSmith payload contract
External spans allow only opaque short-lived correlation, node name, duration, outcome code, versions, aggregate token usage and retry count. Raw inputs/outputs/metadata are disabled before export; string redaction alone is insufficient. Block forbidden payloads in parent/child/error/stream callbacks, attachments, feedback, experiment datasets and SDK automatic integrations. Tenant identity is not an email, account number or PAN. A privacy violation disables tracing and alerts operations. Tracing is independently opt-in/configured; provider inference sharing is separately documented. Approved synthetic experiments may contain synthetic text, with a separate project and access policy.

## Output validation and autonomy
Schemas refer to known metric/source IDs. The renderer inserts amounts and citations; validators reject invented numerical facts, sources and products. Unsupported facts produce an unavailable or deterministic response. A single optional repair is bounded and cannot rewrite canonical values. Document or web instructions are untrusted data. Tool argument validation and server authorization run even when the model claims permission. Autonomous tasks stop at unresolved evidence, safety gates or required user action; they do not invent approval.

## Evaluation and operations references
The [evaluation plan](evaluation-plan.md) owns dataset splits, proposed thresholds, safety gates and result artifacts. [009 operations](009-production-operations/spec.md) owns throughput/queue/restore metrics, budgets and alerts. Keep traces optional and isolated from core processing. Use separate development/production projects, scoped access and recorded retention. Disable broad raw tracing in `utils/llm_brain.py` before enabling metadata-only spans.

Official references: [LangSmith sensitive data controls](https://docs.langchain.com/langsmith/mask-inputs-outputs) and [evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts). Experiments use approved synthetic/sanitized data. The application remains usable if tracing or the model is unavailable.
