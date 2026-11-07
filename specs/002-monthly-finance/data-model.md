# Monthly Finance data model

| Entity | Fields and invariants |
|---|---|
| Account | owner, supported type, label, masked identifier, INR currency, active flag and ledger revision. |
| Document | owner, private encrypted storage key, size, MIME, content digest, created/retention timestamps. |
| Import identity | Unique owner/account/source_digest; repeat upload resolves to the same identity. Explicit reprocessing creates a generation, not another independent identity. |
| ImportJob | owner, account, document/import identity, generation, workflow status, opaque graph thread ID, parser version, request idempotency key, period, declared balances, revision, attempt, error code, lease fencing token, cancel_requested_at and business_commit_id. Unique identity/generation. |
| ParsedRow | owner via job, page/CSV row, ordinal, posting date, signed paise, reference, source description and optional balance. Immutable source origin. |
| LedgerTransaction | owner/account, posting date, signed paise, category/components, posted/pending state, origin type, active status and revision. Classification confidence is independent of reconciliation. Splits conserve paise. |
| LedgerEvidence | canonical transaction/source-row link, origin type, import generation, matching method/confidence, active_from_revision and inactive_from_revision. Removing one source does not remove other active support. |
| ReviewItem and Correction | owner/job, affected rows, reason, expected revision, resolution, actor/time and evidence. Preserve source values. |
| Transfer/Refund/Reimbursement Link | owner, linked transactions/components, type, confirmed amounts, remaining eligible amounts and revision. Candidates do not change totals until confirmed. |
| CoverageInterval | owner/account, source start/end, verified/declared/gap state and report scope. Transaction min/max dates alone do not prove coverage. |
| ReportSnapshot | owner, month, account scope, account/link/rule revision vector, metrics, evidence, coverage and rule versions. Exports refer to immutable snapshot IDs. Current staleness is evaluated against source revisions. |
| WorkflowEvent | owner/job, stage, time, safe result code and revision; no raw payload in external telemetry. |

## Publication and recovery
Commit ledger updates, relevant account/link revisions and processed-job marker atomically. Recheck the full report revision vector before making a snapshot current. Reversal creates compensating revisions with shared-evidence preservation. Privacy deletion controls retention of documents, rows, reports, checkpoints, exports and backups; historical inspectability is not an indefinite retention promise.

006 owns budgets, goals, obligations and funding allocations. 009 owns queue leases/outbox; 008 owns deletion suppression. Use those services rather than competing copies. Enforce owner relationships, logical operation uniqueness and split conservation in database constraints where feasible and service tests otherwise.

See [reversal contract](contracts/reversal-and-concurrency.md) and [financial rules](../financial-rules.md).
