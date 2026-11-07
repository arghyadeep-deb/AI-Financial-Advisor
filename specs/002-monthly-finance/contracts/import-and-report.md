# API contract — Statement import and monthly reporting

Current planning contract. Preserve existing profile, analysis and chat endpoints. Generate exact OpenAPI schemas and contract fixtures during the selected implementation.

| Operation | Contract |
|---|---|
| `POST /accounts` | Create an owned INR account with a label and supported account type. |
| `POST /statement-imports` | Authenticated multipart account ID and file. Return 202 with logical job and generation. Same owner/account/digest returns existing import identity; a reversed import is not automatically reposted. |
| `GET /statement-imports/{id}` | Owned workflow state, revision, generation, coverage, safe error and allowed actions. Paginate staged rows/review items through owned endpoints. |
| `POST /statement-imports/{id}/review` | Explicit resolutions, expected revision and idempotency key; validate status/owner before queuing resume. |
| `POST /statement-imports/{id}/retry` | Retry only failed_retryable; completed is a no-op; failed_final, cancelled and reversed do not resume. |
| `POST /statement-imports/{id}/cancel` | Request cancellation; resolve cancellation/commit race under the transaction guard. |
| `POST /statement-imports/{id}/reverse` | Evidence-aware compensating revision; return affected reports/accounts. |
| `POST /statement-imports/{id}/reprocess` | Explicit new generation under original document identity with comparison/review; never silently append duplicates. |
| `GET /statement-imports/{id}/events` | Page safe owned workflow events. |
| `GET /monthly-reports?month=YYYY-MM&scope_id=...` | Select current report for an owned account scope; disclose processing, partial, unavailable and stale states. |
| `GET /monthly-reports/{report_id}` | Retrieve one owned immutable snapshot with coverage and current staleness metadata. |
| `GET /monthly-reports/{report_id}/transactions` | Page snapshot evidence by metric/category/account. |
| `GET /monthly-reports/{report_id}/export` | CSV/PDF from the same snapshot; authorize before bytes or short-lived private link. |

## States and responses
Workflow states: queued, validating, quarantined, extracting, needs_review, publishing, completed, failed_retryable, failed_final, cancel_requested, cancelled, reversed. Quarantine blocks extraction/publication until an explicit successful scan/rescan; unavailable scanner is never treated as success. Failed_final requires corrected input or explicitly permitted reprocess, not retry. Report completeness, staleness and narrative availability are separate from job state.

Mutation requests bind authenticated owner, expected revision and idempotency key to a payload digest; changed payload under the same key returns 409. Upload creation has no prior revision and binds to owned account/current import identity. Support safe 4xx validation errors, 409 conflict, 413 size, 415 type and 429 quota responses. Wrong-owner/missing-resource responses reveal no existence or contents.

Job envelope: job_id, generation, workflow_status, revision, allowed_actions, safe_error, coverage_summary. Report envelope follows [architecture](../../architecture.md); monetary metrics use integer paise. Exact required/optional fields are frozen in OpenAPI before endpoint implementation. Limits come from the approved support matrix and 009 benchmarks.

See [reversal and concurrency](reversal-and-concurrency.md) for transactional semantics; the API does not define a second posting or undo implementation.
