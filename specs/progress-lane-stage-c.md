# Stage B remainder / Stage C statement lane

Date: 2026-11-07. Worktree: `AI-Advisory-stage-c`, branch `codex/stage-c`.
All changes intentionally left uncommitted for the orchestrator. No git add,
commit, push, deployment, real statement, payment, filing, trade, external model,
scanner, email or push call was performed. No frontend files were changed.

Status is acceptance-level: **partial** means requirements remain; no shared task
checkboxes or shared progress/handoff files were edited. Tests use temporary
SQLite databases built by real Alembic migrations, synthetic files, and disabled
provider keys from `tests/conftest.py`.

## Decisions, conflicts and safe defaults

- User instruction selects implementation despite planning-only spec headers.
  Explicitly synthetic CSV/text scope overrides the proposed real-bank/PDF pilot.
  Format `synthetic-inr-v1`, parser `synthetic.v1`, fictional debit accounts only.
  `tests/fixtures/statements/README.md` defines the exact grammar and fixtures.
  No claim of bank compatibility, card adapter, malware AV, OCR or real-data release.
- Existing identity, exact-money, errors, quota reservations, telemetry, suppression,
  migration runner and queue/lease/outbox are reused. No competing queue, split
  store, budget engine, auth stack or notification delivery implementation.
- Sources and exports use authenticated Fernet encryption under an explicitly
  configured key ring, with atomic writes and rotation. No fallback storage key.
  Windows filesystem ACLs, managed keys, encrypted DB/backups, privileged MFA,
  transport termination and a production scanner require operational acceptance.
- Parser runs in a separate `python -I` subprocess with a stripped environment,
  fixed entrypoint, byte/row/output bounds and kill-on-timeout. The synthetic
  scanner rejects binary/control/EICAR inputs. Socket calls are disabled inside
  this fixed parser. **This is not an OS security sandbox**; hostile parser code,
  filesystem capabilities, process memory/CPU limits and real AV isolation are
  not certified. Production-like configuration refuses synthetic enablement.
- LangGraph has typed ID/status-only state. Application job/ledger markers are
  durable recovery checkpoints; authenticated review is a separate API operation.
  PostgreSQL LangGraph checkpointer and `interrupt`/`Command` replay are deferred;
  no in-memory checkpointer is represented as durable.
- Accounts are locked in stable owner scope. All owner account revisions advance
  for a ledger mutation (conservative over-invalidation); link mutations also
  advance link revisions. Reports compare the complete owned-account vector,
  selected calendar-month coverage and rule version. Household account inventory
  is not confirmed: `household_coverage=undeclared_inventory` always remains.
- Source rows, correction evidence and reports reject SQL UPDATE via migration
  triggers; privacy DELETE remains possible. Corrections retain actor (owner),
  reason, source/target, before/after and idempotency input. Splits conserve signed
  paise and never change bank cash movement. No source money is rewritten to fix
  a balance mismatch: replace the source or cancel/reprocess explicitly.
- API path deviation from the planning contract: `/statement-accounts/{id}/uploads`
  accepts a bounded raw CSV/text stream instead of multipart `/statement-imports`.
  `/resume` atomically reviews/publishes; no separate `/review` queue is required
  for this deterministic small-format slice. Exact wire shapes are below.
- Classifications supplied in this synthetic format are **user assertions**,
  surfaced as such, not inferred salary or bank-confirmed labels. Unknown credits
  never count as income. Unmatched transfers, refunds and withdrawals remain
  unresolved. Positive historical surplus never establishes affordability.
- Deletion journal is independently configured, survives DB restoration, records
  minimal state history, and blocks authentication even if the business DB write
  failed after suppression. It must remain outside all restored backup sets.
  Legal holds and backup expiry are unapproved; API reports `expiry_unapproved`.
- New retention defaults (source 30 days, private export 300 seconds, configured
  backup 30 days) are **offline test policy**, not ratified legal/production policy.
  Backup retention is configuration only, not an automatic erasure promise.
- Request quotas count attempted expensive work. Completed chat replays are free;
  incomplete retries are bounded too. Analysis has no request idempotency contract.
  Quotas reserve before model work/SSE starts and return structured 429 plus
  `Retry-After`. Paid-provider budgets and global circuit breakers remain disabled.

## Task status and files

Commands/evidence C1-C9 below apply to the corresponding tests named here.
All limitations and missing work listed here are intentional open work, not done.

| Task | Status | Files / verified behavior | Limitations, disabled features, remaining acceptance |
|---|---|---|---|
| T0801 | partial | `backend/core/owned_stores.py`, `backend/models/models.py`; statements and private export deliveries registered with export + idempotent file/DB purge hooks; coverage checked in C3-C7. | Full processor/field disclosure and retention/legal applicability review not approved. Account export contains source metadata and report/ledger data; source bytes use separately authenticated document retrieval. |
| T0802 | partial | Existing session list/revoke/password reauth reused; `backend/core/dependencies.py` additionally enforces independent suppression; C1/C3-C7. | Recovery-request abuse controls and privileged/user MFA still pending; no mail provider. |
| T0803 | partial | `platform_controller.py` adds GET consent status; append-only POST and current-consent queue publication reused; C1/C3-C7. | Existing legacy analysis/chat provider paths are not fully wired to per-user inference/tracing consent. Do not enable providers on this evidence. |
| T0804 | partial | `backend/services/privacy/exports.py`, `schemas/platform.py`, `controllers/platform_controller.py`; password reauth, private encrypted expiring artifact, owned request/status/download, no-store, expiry cleanup and export quota; C5-C7. Immediate authenticated export also supported. | Synchronous export bounded to 10 MB after serialization; large/async exports, complete binary-file bundle, processor disclosure and production delivery acceptance remain. |
| T0805 | partial | `services/privacy/lifecycle.py`, `owned_stores.py`, `dependencies.py`; suppression precedes block/purge; journal requested/access_blocked/purging/live_complete/failed_retryable events; failure resumes; source/export file purge; C1/C3-C7. | Production durable journal grants/backup exclusion, legal holds, authenticated post-block customer status journey and approved backup expiry unfinished. External providers absent. |
| T0806 | partial | `core/config.py`, `finance/storage.py`; encryption/key ring, old-key recovery, rotation, retired-key denial/tamper checks, retention configuration validation; C4-C7. Existing signing rotation reused. | Managed storage/DB/backup keys, operator audit/grants, privileged MFA and production encryption evidence remain. |
| T0807 | partial | `test_stage_c_platform.py`, `test_stage_c_security.py`; export/delete/failure-resume and pre-delete backup/object restoration suppression with synthetic identifiers; C3-C7 and timed C8. | No real providers, legal policy approval or production/PostgreSQL lifecycle drill. |
| T0901 | partial | Existing config/migrations_runner reused; parser/quota/retention bounds fail validation; reversible migrations tested C3-C7. | No clean deployment or CI; none attempted. |
| T0902 | partial | `workers/queue.py` adds optional kind filtering; `statement_service.py`, `workers/statements.py`, `workers/notifications.py`, `finance/retention.py`; same fenced outbox, cancellation fencing and orphan cleanup; C3-C7. | No installed supervisor/automatic operator scheduler, PostgreSQL race evidence, full process-crash stress or privileged retry API. Orphan sweep requires stopping uploads and >=1h age grace. |
| T0903 | partial | `core/limits.py`, `config.py`, analysis/chat controllers, upload/export services; daily per-owner requests/jobs/bytes/exports; clear 429 before SSE, completed replay exemption; C1/C3-C7. | Global breaker, token/cost accounting, monetary provider caps, cumulative live-storage quota and paid integrations remain. |
| T0904 | partial | `observability/health.py`; DB probe, queue age/state, reconciliation/partial-report/auth-lock aggregates, local span p95, actionable safe alerts and exporter outage isolation; C1/C3-C7. | Operator-only helper, no public raw metric endpoint. Worker heartbeat readiness, API latency targets, model cost and deletion-lag routing/on-call acceptance missing. |
| T0905 | partial | `test_stage_c_security.py`; real SQLite concurrent same-account publish and cancel/publication race; C6-C7. | No ratified hardware/load p95 experiment or PostgreSQL concurrency run. |
| T0906 | partial | Existing `deployment/recovery.py` reused; C8 restored DB plus encrypted objects, replayed independent suppression, purged ledger/export/source and preserved survivor access. | Small synthetic drill only. PostgreSQL, encrypted scheduled backups, production RPO/RTO and recovery ownership remain. |
| T0907 | partial | This file records limits/recovery/evidence. | Ratified caps, price assumptions, named on-call and release review remain. |
| T1005 | partial | `notification_service.py`, `workers/notifications.py`; shared-queue due scheduling, current preferences at delivery, Asia/Kolkata quiet defer, dedupe, bounded 7-day expiry, metadata-only fixed copy; C1/C3-C7. | External channels and digest cadence disabled; no installed scheduling supervisor or notification pagination UI. |
| T201 | done (selected synthetic scope) | `tests/fixtures/statements/` grammar plus supported/mismatch/unsupported/overlap/distinct fixtures. Duplicate test reuses exact supported bytes. C3-C7. | No real bank/PDF/card statement format selected or advertised. |
| T202 | done (selected synthetic scope) | `models.py`, `0100_statement_core.py`, `0101_private_exports.py`; account/document/import/immutable source/ledger/evidence/correction/link/report and export metadata. Column/unique-constraint roundtrip tests C3-C7. | No real pilot approval; production PG migration not run. |
| T203 | partial | `finance/storage.py`, parser runtime/process, statement service/controller; owned encrypted local files, bounded streaming, download reauth on each request, retention and parser caps; C3-C7. | Synthetic scanner only; no OS sandbox/AV/real bank support. No public signed URL; authenticated download with expiry used instead. |
| T204 | done (selected backend scope) | `schemas/statements.py` before `controllers/statement_controller.py` consumers; owned account/upload/status/rows/events/document and mutation endpoints; C3-C7. | UI belongs to orchestrator. Synthetic-only switch defaults off. |
| T205 | partial | `finance/importers/{registry,synthetic}.py`; deterministic exact CSV/text, strict dates, source row, version, period, balance evidence, quarantines; C3-C7. | PDF/OCR/protected/scanned/real bank adapters intentionally absent; binary/PDF inputs never publish. |
| T206 | partial | `agents/monthly_finance_graph.py`, `workers/statements.py`, statement service; typed ID-only graph, shared lease/fence, atomic stage/reconciliation marker and restart-safe DB publication; C5-C7. | PostgreSQL LangGraph checkpointer and persisted interrupt/resume integration remain. API revision-checked resume uses authoritative DB state. |
| T207 | partial | `finance/ledger.py`; zero-paise reconciliation, stable scoped references, ambiguous overlap requires explicit match/distinct, source evidence and idempotent revision checks; C3-C7. | Full PostgreSQL overlap/load acceptance and broader source correction workflows not exercised. Money mismatch blocks publication and requires replacement. |
| T209 | partial | Same ledger link service; explicit owned debit/credit transfer, settlement, refund/reimbursement links, both revisions checked, partial allocation caps, invalidation, unlinked unknown movements; C4-C7. | No released card adapter or cash/manual inventory. Full ambiguous candidate UX and all reimbursement receivable cases remain. |
| T210 | done (selected backend scope) | Ledger publication/evidence/account revisions/business marker/outbox notice/audit commit atomically; reversal keeps corroborated entries and immutable historical report data; C3-C7. | PostgreSQL acceptance deferred with T217; no external effects. |
| T216 | partial | `ledger.metrics`, `test_stage_c_{statements,security}.py`; independent FIN-01/02/03/04/05/06/07/08/11/12/13/16 evidence; exact paise and conservative unavailable affordability. | FIN-09 explicit restatement semantics, FIN-10 confirmed reimbursement receivable/own-share view, ledger-integrated FIN-14 future capacity and FIN-15 same-basis net-worth evidence remain. Existing cashflow engine is reused, not duplicated. |
| T217 | partial | Shared-evidence reversal, partial corroboration, dependent-link invalidation, fenced cancel, explicit deduped generations, restart/post-commit replay, real concurrent publish/cancel tests; C3-C7. | Full reversal contract including concurrent report compute, parser-version comparison/reprocess selection and PostgreSQL/process-kill matrix not complete. |
| T218 | partial | `monthly_report_service.py`; full owned-account + link vector/rule checks, selected monthly verified/unverified/missing-day coverage, out-of-scope link IDs, immutable historical export, stale vector refusal; C3-C7. | Explicit household inventory confirmation and full simultaneous multi-account/report-race matrix remain. Household coverage never claimed complete. |
| T211 | partial | Same report service + controller; immutable snapshot/evidence JSON and reproducible formula-safe CSV export/stale flags; C3-C7. | PDF export and UI (orchestrator) absent; no PDF artifact created. |
| T212 | partial | FIN-01 statement report verified. | Dashboard/Reports/Chat consumption of observed ledger facts is not wired; profile FinanceSnapshot remains unchanged and must not be overwritten with historical surplus. |
| T213 | partial | Deterministic factual report narration retained; no LLM transmission or invented numerical facts. | Merchant suggestion workflow and approved optional narrative adapter not implemented. |
| T214 | partial | Synthetic parser, money, source, owner, failure, retry, privacy, concurrent and restore tests in lane suites; C3-C8. | Independent held-out parser/eval corpus, optional external experiment and full adversarial/pilot acceptance remain. |
| T219 | partial | Registry/account schema explicitly accepts only synthetic debit accounts, blocks card formats. | Versioned budgets/confirmed bill inputs and UI not built. 006 owns these services; this lane does not duplicate that capability. |
| T1401 | partial | `/statement-formats` returns exact support/limits, categories, versions/scanner policy; negative fixture tests C3-C7. | Support UI owned by orchestrator; PDF/scanned/protected adapters unsupported. |
| T1402 | partial | Credential-free bounded parser subprocess, scanner unavailable/quarantine, byte/row/timeout tests C3-C7. | OS isolation and actual production scanner runtime remain mandatory real-data gates. |

T208 review UI is explicitly outside this lane. T215/T220 pilot gate is **not
completed** and real uploads remain disabled. No claim that all Stage B or Stage C
acceptance is done. No review tasks are checked on partial evidence.

## API handoff for orchestrator UI

All routes require Bearer auth and use the shared structured error body:
`{detail,code,message,request_id,retryable,field_errors}`. Foreign and absent IDs
return the same 404 `Resource not found.`; stale revision/idempotency input ->409;
quota ->429 plus Retry-After; expired bytes/export ->410. All money below is
signed **integer paise**, except the synthetic input file's exact rupee strings.

- `GET /statement-formats` -> `{enabled,synthetic_only,formats:["synthetic-inr-v1"],
  account_types:["synthetic_debit"],max_bytes,max_rows,max_pages:0,timeout_seconds,
  pdf:"unsupported",ocr:"disabled",scanner:"synthetic_text_allowlist",
  source_retention_days,categories:[...]}`.
- `POST /statement-accounts` `{label,token,account_type:"synthetic_debit"}` ->201
  `{id,label,token,account_type,revision}`. `GET /statement-accounts` -> up to100
  `{id,label,token,account_type,revision,link_revision}`. `token` is a fictional
  account token matching the file header, never an actual bank identifier.
- `GET /statement-accounts/vector` -> `{account_uuid:[ledger_revision,link_revision],...}`
  includes all owned accounts, not merely selected report accounts.
- `POST /statement-accounts/{id}/uploads`, Content-Type `text/csv` or `text/plain`,
  raw file bytes ->202 job object (below). Identical owner/account bytes return
  latest generation of the existing document. No multipart field or filename.
- `GET /statement-imports?offset=0` -> up to100 job objects; `GET /statement-imports/{id}`
  -> job: `{id,account_id,document_id,work_id,generation,revision,state,checkpoint,
  parser_version,error_code,start_date,end_date,opening_paise,closing_paise,
  difference_paise,business_commit_id}`. New job state queued -> needs_review
  (or quarantined). Difference = opening + signed movement - closing; exact zero
  reconciles, null means unverified, nonzero blocks. Worker is an operator process,
  not a public "run worker" API. Poll status, do not infer success from 202.
- `GET /statement-imports/{id}/rows?offset=0` -> up to100 `{id,source_row,
  posting_date,amount_paise,description,reference,category,classification_source:
  "synthetic_user_assertion",candidate_entry_ids:[...]}`. No-ref identical rows
  in one file remain distinct; cross-file candidates need explicit review.
- `GET /statement-documents/{id}/content` -> owned private attachment, no-store,
  nosniff; expiry enforced on every read. No permanent source URL credential.
- Operation body common to mutations: `{expected_revision:integer,
  idempotency_key:"client-stable-key-8..64",reason:"nonempty reason"}`. Reusing a
  key with changed input is409; retry the exact original body to replay result.
- `POST /statement-imports/{id}/resume` common operation plus
  `{decisions:[{row_id,category,match_entry_id:null|string,distinct:false|true}],
  acknowledge_unverified:false|true}` -> completed job. Mismatched balances or
  account token cannot resume. Confirm ambiguity with match_entry_id or distinct.
  Existing matched classification changes go through ledger split API, not a
  source rewrite. Publication of unknown classifications is explicitly incomplete.
- `POST /statement-imports/{id}/cancel`, `/reverse`, `/reprocess` common operation.
  Cancel queued/review/quarantined, reverse completed, reprocess latest reversed/
  cancelled/quarantined into a new generation (same document identity). Response
  job object; reverse adds `inactive_entry_ids`. Reprocess never bypasses digest
  dedupe. `GET /statement-imports/{id}/events?offset=0` -> up to100
  `{id,operation,created_at,result}` owner-scoped audit results.
- `GET /ledger?offset=0` -> up to100 `{id,account_id,posting_date,amount_paise,
  components:[{category,amount_paise,obligation_id:null|string}],revision,active}`.
  `POST /ledger/{id}/splits` common operation plus `{components:[...]}`; signed
  component amounts must equal original paise and have its direction. Result
  `{id,components,revision}`. Active linked entries require unlinking first.
- `POST /ledger-links` common operation plus `{left_id:debit_entry_uuid,
  right_id:credit_entry_uuid,expected_right_revision:integer,kind:"transfer"|
  "card_settlement"|"refund"|"reimbursement",amount_paise:positive_integer}` ->201
  `{id,kind,amount_paise,revision}` (revision is updated left-entry revision).
  Both entry revisions checked. `POST /ledger-links/{id}/reverse` common operation
  expected_revision is current left-entry revision -> `{id,active:false,revision}`.
- `POST /monthly-reports` `{month:"2026-01",account_ids:[...],expected_vector:{...}}`
  ->201 `{id,month,rule_version,vector,stale,snapshot,created_at}`. `GET /monthly-reports/{id}`
  returns same shape; `/export.csv` exports the immutable source snapshot.
  `snapshot={metrics,coverage,selected_scope_complete,household_coverage:
  "undeclared_inventory",account_ids,sources,links,out_of_scope_link_ids,
  narrative_status:"deterministic",narrative}`. Coverage per account has
  `{verified_days,unverified_days,required_days,complete,missing_verified_dates}`.
  Sources carry entry/account/date/paise/description/components/revision plus
  `{import_id,row_id}` evidence. Metrics include income/spending/cash movement,
  borrowing/investment/disposal/principal/unsplit-debt/refund/reimbursement,
  unclassified debit/credit, recognized surplus/shortfall, completeness, eligible
  contribution and affordability status/reason. Missing forward evidence means
  eligible contribution null, except deficit is zero. Never advertise investment
  capacity from the report's surplus. PDF/budget UI controls must remain disabled.
- `GET /privacy/consents` -> `{model_inference:false|true,tracing:false|true}`;
  append choices with existing POST `/privacy/consents` contract.
- `POST /privacy/export` `{password}` -> immediate private JSON attachment.
  `POST /privacy/exports` `{password}` ->201 `{id,kind:"export",state:"ready",
  created_at,expires_at}`; GET `/privacy/requests/{id}` same metadata (expired when
  TTL elapsed); GET `/privacy/exports/{id}/download` authenticated JSON attachment.
  No public link. Wrong owner404; expired410. Password is never returned/stored.
- `POST /privacy/deletion` `{password}` ->202 `{status:"live_complete",
  backup_status:"expiry_unapproved"}` on synchronous successful purge; immediately
  discard local session. Suppression blocks auth even if a later purge step fails.
  Failure recovery is operator-only `resume_delete` with the independent journal.
  No post-deletion customer status route is advertised.
- Existing sessions/preferences/notifications/password change APIs remain in the
  Stage B contract. New due notices are processed by `workers/notifications.py`;
  no email/push/digest integration is enabled.

## Configuration / migration / recovery

`Config` adds ANALYSIS_DAILY_LIMIT=100, CHAT_DAILY_LIMIT=200,
UPLOAD_DAILY_LIMIT=20, STORAGE_DAILY_BYTES=52428800, EXPORT_DAILY_LIMIT=10,
SOURCE_RETENTION_DAYS=30, EXPORT_TTL_SECONDS=300, BACKUP_RETENTION_DAYS=30,
STATEMENT_MAX_BYTES=1048576, STATEMENT_MAX_ROWS=10000,
STATEMENT_TIMEOUT_SECONDS=5. `/statement-formats` exposes effective parser limits.

SYNTHETIC_STATEMENTS_ENABLED defaults false, forbidden production-like. Explicit
PRIVATE_STORAGE_ROOT, STORAGE_ACTIVE_KEY and STORAGE_KEYS_JSON (map key IDs to
Fernet keys) required for stored sources/exports. Keys are not printed or committed.
SUPPRESSION_JOURNAL must be independent of business DB and all restore sets;
delete endpoint refuses unconfigured journal. Never use the real DB for drills.

Key rotation: install new key alongside old; set active new; call storage.rotate
for each source/export; verify decrypt after restart; retire old only after all
live objects/backups needing it have migrated/expired. Losing keys makes sources
unavailable, not silently plaintext. Test C4 covers recovery/retired-key denial.

Revisions: `0100` down_revision=`0051`; `0101` down_revision=`0100` (lane range).
Use existing migrations_runner with verified backups. New tables registered in
owned_stores; file purge precedes DB purge and can resume after interruption.
Downgrade refuses populated statement/export evidence; preserve/export or perform
authorized lifecycle purge first. Tests downgrade empty temp DB head ->0051->head.
No migrations were run against user/live data. Prefer forward fix; disable new
synthetic imports on parser regression. Never restore suppression journal from an
old backup. Object restore must target isolated encrypted root with the same keys,
then replay suppression and hooks before serving. No production recovery claim.

Worker entrypoints (same Python below): `-m backend.workers.statements` and
`-m backend.workers.notifications` each process one due shared-queue job. Operator
must arrange bounded scheduling; no daemon installed. `finance.retention.sweep`
removes expired synthetic objects and aged orphans after uploads stop;
`privacy.exports.expire` removes expired export bytes. Neither guesses backup expiry.

## Actual commands and results

Python is always the requested interpreter. `-X utf8` below avoids the repository's
existing emoji print crashing Windows cp1252 when pytest capture is disabled.

**C1**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/test_stage_c_platform.py tests/test_stage_b.py -q -p no:cacheprovider -W ignore`
Initial result: **2 failed, 14 passed in 11.62s**. New chat quota fixtures used
client message IDs shorter than the existing 8-character contract; fixed fixtures.

**C2**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Intermediate backend result: **266 passed, 8 skipped in 114.47s**. Later added tests
and private-export migration are covered by final run below; this is not final evidence.

**C3**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/test_stage_c_platform.py tests/test_stage_c_statements.py tests/test_stage_b.py -q -p no:cacheprovider -W ignore`
Result: **24 passed in 19.66s** (initial statement slice).

**C4**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/test_stage_c_security.py tests/test_stage_c_statements.py tests/test_stage_c_platform.py -q -p no:cacheprovider -W ignore`
Result: **33 passed in 18.18s** (expanded storage/parser/finance/concurrency).

**C5/C6** (same exact command, successive additions)
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/test_stage_c_security.py tests/test_stage_c_statements.py tests/test_stage_c_platform.py tests/test_stage_b.py -q -p no:cacheprovider -W ignore`
Results: **45 passed in 30.00s**, then **50 passed in 34.89s**.

**C8 timed drill**
First command without UTF-8:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/test_stage_c_security.py::test_restore_drill_replays_suppression_for_ledger_sources_and_exports -q -s -p no:cacheprovider -W ignore`
Result: **1 setup error**, existing utils/llm_brain.py emoji print -> cp1252
UnicodeEncodeError. Drill did not run in this invocation.

Actual successful rerun:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_c_security.py::test_restore_drill_replays_suppression_for_ledger_sources_and_exports -q -s -p no:cacheprovider -W ignore`
```text
Synthetic restore and suppression replay: 0.052s; deleted ledger/export/source absent; survivor active
1 passed in 2.55s
```
This is a tiny temporary SQLite/object fixture, not production throughput or RTO.

**C7 first full suite including browser**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests -q -p no:cacheprovider -W ignore`
Actual full-suite output (final emitted chunks):
```text
...................sss.ss..............s......... [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
...ss................................................................... [ 91%]
............................                                             [100%]
308 passed, 8 skipped in 156.02s (0:02:36)
```
The 8 skips are the existing six public-route authentication parametrizations
and two PostgreSQL opt-in tests. Chromium browser tests ran in this full suite.

**C9 explicit browser rerun**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore`
Actual result: **12 passed in 28.10s** (Chromium available).

Final review found that an invalid direction in a review classification could
raise an internal Pydantic error instead of a useful 422. Fixed the translation,
added a real API regression assertion, and reran affected statements/security
tests plus the complete backend suite (results below). No money or source facts
are changed on rejection.

**C10 final review regression**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_c_statements.py tests/test_stage_c_security.py -q -p no:cacheprovider -W ignore`
Actual result: **33 passed in 20.50s**.

**C11 final backend after review fix**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Actual result: **296 passed, 8 skipped in 132.21s (0:02:12)**.

Final review also corrected equal date/amount/description handling: differing
stable account references establish distinct transactions; they do not need a
weak-signature overlap decision. A regression test imports both referenced files
and preserves four entries. Import completion queues a safe reminder; report-ready
notification is scheduled only in the immutable report publication transaction.

**C12 authoritative final full suite after all review fixes**
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests -q -p no:cacheprovider -W ignore`
Actual final output (last emitted chunk):
```text
......                                            [100%]
309 passed, 8 skipped in 159.57s (0:02:39)
```
This supersedes C7/C11 for final code and includes all 12 Chromium browser tests.

`git diff --check` passed at handoff. Generated `evals/results/latest.json` revision
metadata restored to its initial clean content using read-only `git show` and
writing its worktree file with the required Python; no git metadata was modified.
No shared progress/handoff, frontend or user data files were edited. The only
`backend/main.py` change is the one statement router include line. New migrations
are exclusively 0100/0101. Work remains uncommitted as explicitly instructed.

## Remaining / disabled at handoff

Production keys/ACL/AV/OS isolation/DB-backup encryption and approved retention;
legacy provider consent adapters; MFA/recovery abuse controls; legal holds and
post-block deletion receipt UX; complete binary export bundle/async large exports;
global monetary/cost/token budgets and live-storage cap; installed workers/retention
scheduling and full readiness/alert operations; PostgreSQL/CI/load/security review;
durable LangGraph interrupt/checkpointer; full correction/reprocess/version/race
matrix; FIN-09/10/14/15 ledger integration; household inventory confirmation;
PDF/real bank/card/OCR adapters; report PDF; Dashboard/Chat ledger consumers;
merchant suggestions/independent held-out evals; 006 budget/bill integration and
orchestrator's frontend review/report flows. T215/T220/G2 remain unapproved.
