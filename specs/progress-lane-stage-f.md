# Lane F: public-sample research and 002 acceptance

Date: 2026-11-07. Integration worktree; all edits remain uncommitted for the
orchestrator. No git add/commit/push, frontend changes, live DB access, external
integrations, network ingestion, billing, filing, trading or deployment.

Read first: implementation-progress/order/handoff, previous B/modules/C/D lane
handoffs and remaining sections; 002 and 012 spec/plan/tasks/contracts/acceptance;
financial-rules, agent-quality, constitution and release-gates. User selection
supersedes the planning-only headers. Existing auth, exact money, ledger, reports,
registry, telemetry, worker queue, privacy registry and migrations runner are reused.

## Task status

| Task | Status | Implemented/verified slice | Remaining |
|---|---|---|---|
| 002 T211 | partial | Existing immutable snapshots/CSV/evidence and stale flags exercised through correction/reversal/reprocessing and tenant API tests. | PDF export, new report UI and real bank/PDF/OCR evidence absent. |
| 002 T212 | partial | Existing ledger Dashboard/Chat deficit tests rerun with D suite. | New orchestrator frontend walkthrough, live-format journey and release evidence. |
| 002 T213 | partial | Existing deterministic narration and owned merchant suggestions rerun; hostile description never becomes narration. | Broader held-out merchant/narration evaluation, UI evidence. Model narration remains disabled. |
| 002 T214 | partial | Offline parser/security/tenant/privacy tests plus expanded F matrix, source payload telemetry checks. | Independent held-out real-format evals, production privacy/restore and operational review. |
| 002 T216 | partial | Existing FIN fixtures rerun; unknown incoming movement after invalidated links remains unknown, no fabricated salary or affordability. | FIN-15 complete holdings/debt/inventory basis; real-format and complete household coverage acceptance. |
| 002 T217 | partial | Replay/conflict/stale matrix, real SQLite two-writer requests, changed-parser generations, cancellation/worker replay, shared support and link invalidation. Fixed surviving endpoint revision fencing. | Full PostgreSQL concurrency/crash/checkpointer matrix and real parser release evidence. |
| 002 T218 | partial | Full account/link vectors, historical CSV reproduction, correction/race acceptance. | Production DB concurrency and complete household inventory acceptance. |
| 002 T219 | partial | Reused D budget/confirmed-bill revision tests and explicit unsupported card scope. | Orchestrator UI and card/bank adapter release acceptance. |
| 012 T1201 | partial | Existing reviewed registry extended with public-only latest-version metadata boundary; fixed dated/hashed file-backed sample catalog; empty production catalog. | Actual public-source distribution/licence approval and ingestion review tooling. |
| 012 T1202 | partial | Authenticated public sample retrieval/citation resolution; no private evidence even for its owner; exact excerpt entailment, correction/withdrawal/expiry fail closed. | Private retrieval deliberately excluded, broader semantic retrieval/entailment unimplemented. |
| 012 T1203 | partial | Read-only generic education API; closed input contract cannot supply owner/index/action or trigger personalized advice. | Chat/report/UI integration and browser acceptance of new screens. |
| 012 T1204 | partial (inherited) | Existing exact instrument/period/basis/paise contract and disabled feed. | Licensing, feed integration, dated financial statement publication. |
| 012 T1205 | partial (inherited) | Existing ratio/DCF scenario independent fixtures rerun. | Bond-specific tools, sensitivity and full statements. No additional proposal engine created. |
| 012 T1206 | partial | Synthetic retrieval/expiry/correction/injection/numerical-grounding/abstention eval fixtures and tests. | Independent held-out study, external review and G4 research release decision. |

Primary files: `backend/finance/ledger.py`, `backend/services/statement_service.py`,
`tests/test_stage_f_statements.py`, `backend/knowledge/{registry,sample_catalog}.py`,
`backend/schemas/knowledge.py`, `backend/services/education_service.py`,
`backend/controllers/education_controller.py`, `knowledge_base/education/sample-v1.json`,
`evals/research/synthetic_cases.json`, `tests/knowledge/test_public_education.py`.
Only the permitted include_router line is added to `backend/main.py`.

Task-to-evidence mapping (F8 below reruns every listed module; all schema recovery
notes above/below apply to every row, with no new migration):

| Task(s) | Files and acceptance cases |
|---|---|
| T211/T218 | `backend/services/{monthly_report_service,statement_service}.py`; `tests/test_stage_f_statements.py` changed-bank-facts comparison, either-account report race, source tenant endpoints, immutable CSV; existing C/D report/restatement tests. |
| T212 | Existing `backend/services/{chat_service,analysis_service,finance_snapshot_service}.py` consumers; `tests/test_stage_d.py::test_dashboard_chat_ledger_deficit_even_if_profile_positive`. Consumers were reused without edits. |
| T213/T219 | Existing planning service and deterministic monthly narration; D merchant suggestion, budget/candidate/settlement/rollover/card scope tests, F hostile-description case. No second categorizer/budget service. |
| T214 | `tests/test_stage_c_security.py`, `tests/test_stage_f_statements.py`: parser limits, malicious/unsupported content, scanner/worker failures, owner/missing parity, trace marker exclusion, export/purge and existing suppression restore drill. |
| T216 | `backend/finance/ledger.py` survivor revision fix; C security/D exact FIN fixtures, F unmatched incoming credit after all four invalidated link types. |
| T217 | `backend/finance/ledger.py`, `backend/services/statement_service.py`, `tests/test_stage_f_statements.py`: 34 expanded cases incl. four operation replay/conflict/stale cases, ten two-writer cases, six parser-envelope changes, link/refund races, worker/cancel, shared reversal and owned purge. C/D reprocess/scanner/checkpoint/vector tests reused. |
| T1201 | `backend/knowledge/{registry,sample_catalog}.py`, fixed JSON catalog; `tests/knowledge/test_public_education.py` ingestion/correction/expiry/contamination/hash/production-empty cases. |
| T1202/T1203 | `backend/schemas/knowledge.py`, `backend/services/education_service.py`, `backend/controllers/education_controller.py`; public-only relevance/citation/owner boundary, source resolution, closed mutation inputs, zero-DB-change and socket-blocked API tests. |
| T1204/T1205 | Unmodified `backend/knowledge/research.py`; `tests/knowledge/test_registry.py::test_research_hand_calculated` exercises independent ratio and discounted scenario plus incompatible/missing facts and disabled adapter. |
| T1206 | `evals/research/synthetic_cases.json`; parametrized `test_research_synthetic_eval`, existing knowledge regressions plus API/catalog cases. Regression evaluation only; no held-out release claim. |

## Decisions, limitations and recovery

- No new tables or migration: 0130..0139 remain unused; Alembic head stays 0110.
  Existing store coverage/export/purge hooks are reused and tested. Public catalog
  is a versioned repository artifact with no user data; queries/answers are not
  persisted or sent to any provider. No unregistered private side store exists.
- Sample evidence is repository-authored illustrative text on example.test, never
  represented as a regulator/bank source. Server uses Asia/Kolkata current date;
  caller cannot backdate current claims. Expiry is exclusive, fixed at 2027-01-01.
  Production-like environments have an empty catalog; no live feature release.
- Retrieval uses exact supported topics and exact reviewed glossary excerpts. A
  topic tag or a URL alone cannot ground an answer. Mismatched/injected/conflicting
  current text yields unavailable. No LLM or market adapter is invoked. Private
  registry retrieval remains available only through its existing owner boundary;
  the new education service uses strictly public_catalog and never that method.
- Malformed/missing/invalid/privately contaminated catalogs fail to an empty
  catalog; no legacy corpus fallback, partial ingestion or payload logging.
- Corrections/withdrawals supersede older source versions. Resolve citations and
  request a new answer at display/publication time; do not treat a cached answer as
  authoritative. There are no persisted research reports to invalidate.
- Recovery: remove the new router line to disable API; revert the catalog only
  with its matching versioned consumers after disabling new requests. Preserve
  historical ledger evidence/reports. No downgrade or user-data rewrite required
  for either ledger fix. Use shared backup/restore/suppression procedures for any
  operator DB recovery, never a blind rollback of ledger evidence.

## Actual command log

All commands below use the requested Python, isolated temporary SQLite DBs through
real Alembic migrations and synthetic fixtures. tests/conftest.py disables model
keys and tracing before imports. No test secrets printed. Failures are recorded;
they are never counted as acceptance.

F1:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_f_statements.py -q -p no:cacheprovider -W ignore`
Result: **4 failed, 17 passed in 40.87s**. All four link types exposed the real
missing survivor revision bump on import reversal. Fixed in shared invalidate_links;
removed endpoints already advance once, each unique surviving endpoint advances once.

F2:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_f_statements.py tests/test_stage_c_security.py tests/test_stage_d.py tests/knowledge -q -p no:cacheprovider -W ignore`
Result: **85 passed in 96.00s**. Intermediate before later comparison and catalog tests.

F3:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/knowledge -q -p no:cacheprovider -W ignore`
Result: **37 passed in 8.39s**. Intermediate before catalog-failure cases.

Further/final commands and endpoint JSON handoff follow after verification.

F4 (same exact command as F1):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_f_statements.py -q -p no:cacheprovider -W ignore`
Result: **2 failed, 28 passed in 63.45s**. New financial-envelope comparison tests
exposed unchanged-row parser corrections to balances/coverage falsely returning
facts_changed=false. Shared generation_comparison now compares rows AND original
period/balance summaries, exposing both; unavailable extraction is no longer
misrepresented as a changed empty statement. Parser identity alone is not a
financial change. No historical rows/summaries were overwritten.

F5:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_f_statements.py tests/test_stage_c_statements.py tests/test_stage_c_security.py tests/test_stage_d.py tests/knowledge -q -p no:cacheprovider -W ignore`
Result: **138 passed in 137.79s**. Collected before the four final race/failed
extraction cases and final queued-comparison guard; final full-suite run covers all.

F6:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_f_statements.py -k 'report_races_correction or quarantined_reprocess_comparison or two_import_reversals' -q -p no:cacheprovider -W ignore`
Result: **4 passed, 30 deselected in 12.58s**. Corrections in either account race
with publication; simultaneous shared-support reversals cannot leave unsupported
active entries; failed extraction has no invented changed facts.

## JSON handoff for the orchestrator

All three new routes require the existing bearer session and return
`Cache-Control: no-store` on success. No user_id/owner/index/source URL/as_of/action
inputs. Render text/metadata using textContent, show sample-only + as_of +
staleness prominently. example.test is an identifier, not a working external
source site: use resolve_path for source inspection. No new UI is implemented.

`GET /education/topics` (200):
```json
{"corpus":"public_sample_only","as_of":"2026-11-07","personalized_advice_enabled":false,"topics":[{"topic":"budget","status":"complete","staleness":"current"},{"topic":"emi","status":"complete","staleness":"current"},{"topic":"risk","status":"complete","staleness":"current"},{"topic":"tax_documents","status":"complete","staleness":"current"}]}
```
Status/staleness is computed on each request; expiry or production's empty catalog
makes topics unavailable rather than advertising current evidence.

`POST /education/answers` request (only allowed field):
```json
{"topic":"emi"}
```
Topic is 1..80 lowercase letters/underscores. Unknown well-formed topic returns
200/unavailable; invalid input or extra fields return structured 422. The endpoint
does not accept a free-text personal-finance question or authorize mutations.
Current sample response (200):
```json
{
  "topic":"emi",
  "kind":"generic_education",
  "status":"complete",
  "text":"An EMI is a scheduled loan payment. It can contain principal and interest; a bank debit alone does not prove the split.",
  "reason":null,
  "as_of":"2026-11-07",
  "staleness":"current",
  "sources":[{
    "source_id":"sample-emi","version":1,
    "title":"Synthetic education sample: emi",
    "url":"https://example.test/education/emi",
    "content_hash":"85ad172949fd8cc60cb57ca6c4676da2375a576c65642d98ca0368b8e37e998b",
    "published":"2026-11-07","fetched":"2026-11-07","effective":"2026-11-07","expires":"2027-01-01",
    "licence":"Repository-authored synthetic sample; no external source licence asserted",
    "jurisdiction":"IN","staleness":"current","sample_only":true,
    "resolve_path":"/education/sources/sample-emi/versions/1"
  }],
  "corpus":"public_sample_only","rule_version":"education.v1",
  "personalized_advice_enabled":false
}
```
Unavailable answer keeps the same envelope and text
`Current reviewed evidence is unavailable for this topic.`. `status` is
`unavailable`; `reason` is `no_current_public_evidence` or
`evidence_conflict_or_unsupported_claim`. `staleness` is `expired`,
`not_yet_current`, `unavailable` or `conflicting`. Expired/future/conflicting
public evidence metadata remains in `sources` with its own freshness label; no
source claims are rendered. Missing/withdrawn/private/unapproved evidence produces
`sources:[]`. Every answer has the server's dated `as_of`, even with no sources.

`GET /education/sources/{source_id}/versions/{version}` (200):
```json
{"source":{"source_id":"sample-emi","version":1,"title":"Synthetic education sample: emi","url":"https://example.test/education/emi","content_hash":"85ad172949fd8cc60cb57ca6c4676da2375a576c65642d98ca0368b8e37e998b","published":"2026-11-07","fetched":"2026-11-07","effective":"2026-11-07","expires":"2027-01-01","licence":"Repository-authored synthetic sample; no external source licence asserted","jurisdiction":"IN","staleness":"current","sample_only":true,"resolve_path":"/education/sources/sample-emi/versions/1"},"as_of":"2026-11-07","excerpt":"An EMI is a scheduled loan payment. It can contain principal and interest; a bank debit alone does not prove the split.","corpus":"public_sample_only"}
```
After expiry it returns dated metadata with `staleness:"expired"` and
`excerpt:null`. Superseded/withdrawn/private/nonexistent versions all return the
same structured 404 (`Resource not found.`); invalid version <1 is 422.
No old version may be reused to bypass a correction or withdrawal.

Existing `GET /statement-imports/{id}/comparison` gains two nullable summaries:
```json
{
  "import_id":"new-import-uuid","revision":1,
  "previous_import_id":"old-import-uuid",
  "parser_version":"synthetic.matrix.v2","previous_parser_version":"synthetic.v1",
  "state":"review_required","facts_changed":true,
  "previous_summary":{"start_date":"2026-01-01","end_date":"2026-01-31","opening_paise":0,"closing_paise":-1000000,"difference_paise":0},
  "current_summary":{"start_date":"2026-01-01","end_date":"2026-01-31","opening_paise":100,"closing_paise":-999900,"difference_paise":0},
  "previous_rows":[{"ordinal":3,"posting_date":"2026-01-02","amount_paise":4500000,"description":"Synthetic salary","reference":"SAL-1","category":"income"}],
  "current_rows":[{"ordinal":3,"posting_date":"2026-01-02","amount_paise":4500000,"description":"Synthetic salary","reference":"SAL-1","category":"income"}],
  "authority":"comparison_only; use_revision_checked_review_and_ledger_corrections"
}
```
Rows above are abbreviated to one row for illustration. `previous_summary` is
null with no earlier generation. New unextracted summary fields are null.
`state` is `awaiting_extraction` (queued), `extraction_unavailable` (no rows after
failed/cancelled extraction), `baseline` (first extracted generation), or
`review_required` (later extracted generation). `facts_changed` is null until
later-generation extraction is available; it compares financial rows AND
period/balance summaries. Parser-version difference alone leaves it false.
This comparison never grants publication or auto-matches entries.

Existing operation shapes remain unchanged: `/resume` accepts
`{expected_revision,idempotency_key,reason,decisions:[],acknowledge_unverified:false}`;
`/cancel`, `/reverse`, `/reprocess` accept
`{expected_revision,idempotency_key,reason}`. Reprocess returns the new import
envelope `{id,account_id,document_id,work_id,generation,revision:0,state:"queued",
checkpoint:"stored",parser_version,error_code:null,start_date:null,end_date:null,
opening_paise:null,closing_paise:null,difference_paise:null,business_commit_id:null}`.
Resume/reverse retain the established envelope; reverse adds
`inactive_entry_ids`. Same key/body replays the original receipt, including its
original state/revision; refresh GET for current state. Changed key/body collision
or stale revision is 409. A new generation never resumes cancelled/reversed jobs.

After a sole-support import reversal, existing `GET /ledger` now shows advanced
revisions on surviving endpoints of invalidated links. Reload before any split,
settlement or new link; old expected revisions must conflict. Exact signed paise
and historical report export bytes remain unchanged. The Stage D handoff contains
the unchanged report/budget/planning response contracts; this lane adds no new
monthly report, budget, split, queue or privacy implementations.

## Evaluation provenance and release scope

Base revision: `2e8137803868b272fd0b4edcc67c000f9697f52d` plus this uncommitted worktree.
Runner: pytest, deterministic service/API assertions, no model/prompt/provider.
No random sampling; UUIDs only isolate synthetic resource identities.
`evals/research/synthetic_cases.json` v1 has 18 regression cases: 4 grounded, 14
abstentions (3 freshness, 2 private isolation, 3 approval/transport, 2 relevance,
4 unsupported numerical/instruction/exfiltration/product text). Hash:
`4a31397d5ea52b131213ea137311ef3928a71c50e73434e56c6fccee591f79f3`.
Catalog hash:
`32c2676abaa857767bf29509c6ce9ff52285ffb60e191ad78bf861f59236b1b2`.
Additional API/catalog/correction/conflict/recovery-contract tests accompany the
18 cases. No inference cost; no external traces or synthetic content exported.
These are development/regression fixtures authored in this lane, NOT independent
held-out release evidence. The proposed 40-question knowledge and 30-document
import release inventory is not met. No precision/production accuracy claim.

## Remaining / disabled and open owner questions

- Every feature-wide task marked partial above retains its listed missing work.
  T215/T220/G2 and T1206/G4 remain unapproved. No task box in shared specs was ticked.
- Real bank/text-PDF/card/OCR adapters, report PDF, production catalog sources,
  private evidence retrieval in education, research publication, market feeds,
  named products, personalized advice, live narration and all external actions
  remain disabled. No frontend changes or new-screen browser acceptance.
- Full PostgreSQL race/crash matrix, persistent graph checkpointer, independent
  held-out evals, CI/external review, production restore/load/retention/privacy
  approvals and household inventory/FIN-15 remain open shared-owner work.
- Owner questions: choose/approve actual public educational sources, distribution
  rights, reviewer and source-specific expiry policy (D11); decide whether to
  expand beyond the four exact sample topics; orchestrator must implement the UI
  source/freshness/unsupported-format/reprocess-comparison flows. Safest default
  is the fixed-expiry synthetic catalog and empty production catalog until review.
- Migration/recovery: no schema changes or data migrations, owned store coverage
  stays mandatory and exercised. Source/correction artifacts are retained;
  authorized purge remains through the shared registry. No live DBs touched.

## Final verification

F7 explicit existing browser regression:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore`
Result: **18 passed in 68.27s**. Existing HTML/JS tests only; no claim of browser
acceptance for unimplemented education/reprocess UI. No frontend files changed.

F8 final full backend suite (all implementation/test changes preceded this run):
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
Actual final output:
```text
.............                                                           [100%]
438 passed, 8 skipped in 380.17s (0:06:20)
```
Together with F7: **456 passed, 8 skipped** across the backend and browser suites.
The eight skips are the existing six explicitly public auth-route cases and two
opt-in PostgreSQL cases. No skip is counted as a pass. All 34 F statement cases,
43 knowledge cases (including 18 synthetic eval cases), existing C/D/migration/
privacy/restore tests and new-route authentication checks passed. Successful
public-sample backend implementation and the two reproduced/fixed defects are
done for this selected offline slice; feature-wide task statuses remain partial
for exactly the gaps above. This is no G2/G4/real-data approval.

Final read-only checks: `git diff --check` passed; AST parse of all changed/new
Python files passed; frontend/shared handoff/progress files unchanged; main.py
contains exactly one include_router addition. The baseline eval runner rewrote
only `evals/results/latest.json`'s code revision; after verifying its entire JSON
against HEAD plus that one expected change, restored the original artifact via
read-only git show and a worktree-only Python write, preserving checkout line
endings. No user changes overwritten, no git index mutations, commits or pushes.
