# Lane G — offline privacy/operations acceptance and 006 reminders

Date: 2026-11-07. Branch: `codex/stage-g`. Base:
`2e8137803868b272fd0b4edcc67c000f9697f52d`. Changes remain uncommitted, as the
lane-specific instruction overrides the general local-commit rule. No git add,
commit, push, deployment, live provider, billing, tax filing or trades performed.
No frontend, main.py or shared handoff/progress file changes. Tests use the exact
requested Python, real Alembic-migrated temporary SQLite databases and fictional
fixtures. Existing conftest disables model keys and tracing before imports.

Read implementation-order, shared progress/handoff, B/modules/C/D handoffs,
008/009/006 spec/plan/tasks/acceptance, financial-rules, agent-quality,
constitution and release-gates before implementation. Existing shared auth,
money, owner locks, registry, migrations runner, quotas, queue/outbox, storage,
notification preferences/delivery and suppression journal are reused. No LLM
output authorizes finance, delivery or access. No task checkbox was ticked.

## Task status and evidence

`G1`–`G5` below name exact executed test commands (not release-gate IDs). Every
row remains **partial at feature acceptance level** where its original acceptance
includes unrun operational, legal or UI requirements. Implemented sub-behaviors
are identified explicitly; no partial task is claimed done.

| Task | Status / files and offline behavior | Tests / remaining limitations and disabled features |
|---|---|---|
| T0801 | partial — `core/config.py`, `core/owned_stores.py`, `finance/retention.py`, `workers/operations.py`; bounded retention interval, registered nonpersonal operations store, held-account exclusion, source/export cleanup and explicit orphan sweep. | G3/G4: retention due/idempotency/hold/export preservation, registry and config tests. Full field/processor inventory, approved source/backup/journal retention and privacy applicability remain owner/legal work. Existing source/export TTL defaults remain synthetic proposals. |
| T0802 | partial — `core/throttle.py`, `services/auth_service.py`; atomic DB increments and bounded recovery admission for known/unknown addresses; recovery tokens/delivery stop at cap with identical 202 body. | G3/G4: concurrent 12-request admission, expiry and generic responses; existing login/reset/replay/session/reauth matrix. No mail provider, edge/IP/WAF budget, verified delivery, privileged or user MFA. Account-targeted temporary denial-of-service remains possible. |
| T0803 | partial — consumes existing consent service/queue; no replacement consent implementation. | G3/G4 rerun queued-before-revocation denial. Legacy profile-analysis/chat provider consent adapters and full processor disclosure remain missing; keep all keys/providers disabled. |
| T0804 | partial — `services/privacy/exports.py`; expiring encrypted exports participate in scheduled cleanup and held-account retention; live exports protected from orphan cleanup. | G3/G4: private owner/export expiry, wrong-owner and restore/export equality. Async/large exports, complete binary bundle and new export UI remain absent. Ten-MB synchronous limit remains. |
| T0805 | partial — `services/privacy/lifecycle.py`, `schemas/platform.py`, `controllers/platform_controller.py`; existing independent journal extended with bounded legal holds, restricted basis/scope, explicit release/expiry, pending-resume states and hashed deletion receipts. Suppression blocks access even while held; restore consults current external journal. | G3/G4: held/delete/restore/release/expiry, invalid hold inputs, legacy journal upgrade, post-block receipt and unrelated-route denial. Legal/IAM/concurrent hold-vs-purge approval absent. Whole-account scope is conservative and needs approval. Lost or failed initial responses cannot recover their receipt; assistance remains necessary. Backup expiry always `expiry_unapproved`. |
| T0806 | partial — existing `finance/storage.py` and auth signing rotation exercised, no second key service. | G3/G4: local storage old+new ring rewrite, new-only read, retired-key/foreign-owner denial, existing signing rotation/tamper tests. Managed DB/backup/object keys, OS/service-account grants, operator identity/audit/MFA and production key retirement drill remain. |
| T0807 | partial — `tests/test_stage_g.py`, existing Stage C lifecycle/security tests, runbook. | G3/G4: fictional export/delete/restore, failure-resume, hold restore and exact survivor totals; timed result below. Full production/PostgreSQL/provider lifecycle, legal and user receipt UX remain unrun. |
| T0901 | partial — config, migration `0140`, operations/health CLIs and `docs/operations/stage-g-runbook.md`. | G3/G4: actual subprocess operations CLI on temp DB, migrations/registry/schema sync/downgrade/upgrade, unsafe config bounds. No CI or clean production deployment, TLS/proxy/IAM/infrastructure acceptance. |
| T0902 | partial — `workers/{notifications,statements,operations}.py`, `core/operations.py`; fixed-key worker heartbeats, due-only queue lag, retention tick with transactional interval claim; existing fences/leases retained. Orphans require explicit quiesced invocation. | G3/G4: queue cancellation/fencing/retry and reminder transaction outage/replay; CLI tick/retention. No supervisor or OS timer installed; long-running worker/proxy/PG crash matrix and privileged retry workflow remain. |
| T0903 | partial — `core/{limits,operations,config}.py`, `services/statement_service.py`; zero-default owner token/cost and global cost reservations; atomic rollback on refusal, failures remain charged; source payload storage cap counts physical expired/held objects until deletion. | G3/G4: 429, owner/global exhaustion, exact counters, deterministic export still available, deduplicated upload replay and existing source access. **Reservation helper is not wired to legacy provider calls.** Keep keys absent. Approved adapter must enforce verified attempt upper bounds before enablement. No measured cost/report, actual pricing, total-disk/export/backup/DB quota, OCR accounting or production breaker acceptance. |
| T0904 | partial — `observability/health.py`; fail-closed DB/worker readiness, due-work age (future reminders excluded), fixed-key heartbeat staleness, aggregate deletion lag and cost reservation, safe role/action alerts; exporter isolation reused. | G3/G4: injected stale worker/queue/deletion, DB failure without error text, metadata assertions and existing exporter outage. Health CLI is operator-only; no raw public metrics. No on-call transport/person, API latency instrumentation/approved SLO, production alert drill or measured paid cost. Span p95 is not claimed API p95. |
| T0905 | partial — existing SQLite publish/cancel races plus new concurrent recovery admission. | G3/G4 are correctness/concurrency evidence only. No 25-session/5-import sustained experiment, hardware dataset benchmark, ratified latency limit, PostgreSQL load/crash run or availability claim. |
| T0906 | partial — reuses `deployment/recovery.py`, existing C object restore drills, new timed fixture and runbook. | G3/G4: unused destination, integrity, exact survivor count/paise/export equality, deleted-account suppression and current-hold preservation across restore. Small synthetic SQLite timing only. Backup helper remains plaintext and offline; no encrypted scheduled backups, provider recovery, PostgreSQL, production RPO/RTO or assigned recovery owner. |
| T0907 | partial — this evidence table and runbook with units/defaults/recovery/risks. | G3/G4 verify contracts, not release approval. Named on-call, ratified price assumptions/monthly spend, hardware/load and formal release review remain owner work. Zero budget is a safe default, not a cost estimate. |
| T0606 | partial — `schemas/planning.py`, `services/{planning_service,notification_service}.py`, shared notification worker. Optional `Goal.reminder_opt_in=false` is backward compatible with stored revisions. Bill and goal deadline events use the existing outbox, owner+resource+revision metadata only, 09:00 Kolkata due scheduling, fixed generic copy. Recheck current resource/opt-in/archive/paid-or-funded state at delivery under owner lock. | G2/G3/G4: no job before opt-in, revision replay, same-transaction rollback, quiet/defer, overnight and global opt-out, eventual one delivery, archive/funded/stale/expired suppression. Domain deadline expiry is 7 days after due date, not creation (long-planned goals work). No frontend edits/undo/explanation UI or external channel. Recurring bills represent only the explicitly confirmed due-date occurrence; no guessed future recurrence or digest. |
| T0607 | partial — new acceptance cases in `tests/test_stage_g.py` complement Stage D independent FIN-01/14, goal/debt golden totals, ownership and no-provider fixtures. Existing Stage D reminder date made relative to UTC yesterday to test delivery rather than accidental expiry. | G2/G3/G4 rerun deterministic deficit/no-positive-allocation and golden schedules together with reminder/telemetry/lifecycle regression suites. Independent held-out planning evaluation, new UI full-flow walkthrough, explicit selected-release scope and final reviewer acceptance remain absent. No new financial engine or positive allocation from surplus. |

## Contracts, decisions and conflicts

- Notification owner stays 010 T1005; 006 only creates domain events. Goal reminder
  contract precedes its consumer. Due date means the stored explicit date; monthly
  or annual cadence does not authorize generating unconfirmed future occurrences.
- Schema migration 0140 has `down_revision='0110'`, creates only
  `operational_counters`, and reversibly drops it. Model/table columns match.
  Registry export is empty and purge is a no-op because counters contain fixed
  operation names, daily aggregate cost and worker timestamps only. An account
  deletion must not reset global spend. Daily operation counters expire after
  seven days; worker/retention clock rows are overwritten. No personal side store.
- The pre-existing independent SQLite journal is outside business Alembic and
  every restore set. Its additive v2 upgrade adds nullable `metadata_json` to the
  existing `deletion_events` table, preserving legacy rows (tested). It creates
  **no new journal table**. Holds use allowlisted basis codes and account scope,
  <=90-day explicit UTC expiry and opaque hold IDs. No free-text legal documents
  or financial payloads. No public operator endpoint to create/release holds.
  Production retention/grants/durable journal and lawful scope remain unapproved.
- Deletion returns a 256-bit capability once; journal stores only SHA-256 digest.
  POST `/privacy/deletion-receipt` with `{token: ...}` returns only lifecycle state,
  timestamp and truthful backup status with no-store. It intentionally works after
  login revocation. Public-route inventory explicitly allows this capability
  endpoint; dedicated tests prove invalid token denial and no broader access.
  This adds one explicit-public parametrization skip to the existing six.
- No claim of `backup_expired`; there is no provider expiry attestation. Retention
  and backup duration configuration does not itself prove physical erasure.
- Recovery admission uses the existing hashed DB throttle namespace and a single
  conditional UPDATE; concurrent requests cannot all pass a check-then-increment.
  Login failure increments are atomic too. No untrusted forwarded-IP header is
  used. Edge abuse controls require owner-approved proxy topology/identity policy.
- MFA remains disabled/partial: owner must select privileged operator identity,
  roles, enrollment/recovery/break-glass policy and user-MFA release scope. No
  privileged remote console is added. Do not imply MFA protection from this code.
- Budget reservations are integer paise/tokens; conservative positive upper
  bounds, no refunds for unknown/failed attempts, zero configured defaults. A
  reviewed live adapter is still needed; these helpers cannot be represented as
  enforcement around legacy model calls. All test/provider keys remain disabled.
- Source cap is source payload bytes physically present, not encrypted overhead,
  exports, DB or backup space. Expired bytes count until removed. Object/DB
  atomicity still relies on the existing orphan cleanup/grace contract.
- Normal retention job is safe with active uploads because it never orphan-sweeps.
  Explicit orphan cleanup requires stopped uploads. Current export keys are
  protected; an expired held owner is preserved. Holds can change concurrently
  with sweeps/purges across two databases; production serialization/IAM review is
  still required. No production hold race guarantee is claimed.

## Actual command log

All commands ran from this worktree. `-X utf8` avoids existing Windows cp1252
output issues. No live DB was migrated and no real user data was used.

**G1 initial verification**
```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_g.py tests/test_stage_c_platform.py tests/auth tests/api/test_tenancy.py -q -p no:cacheprovider -W ignore
```
Actual result: **1 failed, 136 passed, 7 skipped in 152.66s**. New test imported a
nonexistent `document_bytes` helper; removed unused import. No failed check was
counted done. Seven skips here are explicit public routes, including receipt.
Initial timed drill: **0.880s**, survivor profile count 1, income total 7654321
paise, deleted profile rows 0. Timing is not a production RTO.

**G2 expanded feature verification**
```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_g.py tests/test_stage_d.py -q -p no:cacheprovider -W ignore
```
Actual result: **56 passed in 72.51s**. Intermediate before subsequent recovery
atomic-admission, additional CLI/hold cases and final-review fixes.

**G3 broader review/acceptance**
```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_g.py tests/test_stage_d.py tests/test_stage_c_platform.py tests/test_stage_c_security.py tests/auth -q -p no:cacheprovider -W ignore
```
Actual result: **118 passed in 135.17s**. Timed fixture: **0.872s**, survivor
profile count 1 / exact total 7654321 paise, deleted profiles 0, survivor export
unchanged. Final-review changes after invocation (expiry clock/source cap/resume
states) require G4, not this intermediate result.

**G4 final full backend suite**
```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore
```
Actual result: **395 passed, 9 skipped in 353.66s (0:05:53)**. All implementation
and acceptance-test edits preceded this invocation. Nine skips are seven explicit
public-route parametrizations (including the new deletion-receipt capability)
and two PostgreSQL opt-in tests. Skips are not passes. Final embedded timed drill:
**0.798s**, survivor profile count 1 / income 7654321 paise, deleted profile rows 0.
This supersedes G1–G3 for the final backend worktree. No production RTO claim.

**G5 explicit browser regression suite**
```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore
```
Actual result: **18 passed in 66.30s**. Existing frontend regression coverage
only; new planning/privacy screens were not implemented or accepted.

Fixture identity: `tests/fixtures/statements/supported.csv` SHA-256
`c94b54b47295ce58ec5874a59b6d4344d5d69af68869ae0eb98ce60f7cf0f269`.
New acceptance fixture/test file `tests/test_stage_g.py` SHA-256
`b2f3305fa45da4f08318db10d2e8fb3488a4617fa4019728c2c12bc20f2bc164`.
Hashes computed with the required Python using `hashlib.sha256(Path(...).read_bytes())`.

Combined final suites: **413 passed, 9 skipped** (G4 backend + G5 browser, separate
invocations). All 29 new lane G cases ran, with existing planning/lifecycle/auth,
migrations, finance and module regression tests. `git diff --check` passed.
The only test-generated shared artifact diff was the `code_revision` field in
`evals/results/latest.json`; restored its initially clean HEAD content using the
required Python and read-only `git show`, preserving CRLF checkout line endings.
No frontend/main/shared handoff or another lane's progress changes remain.

## Release-gate evidence (no unrun gate passed)

| Release gate | Proven offline in this lane | Missing CI/PostgreSQL/security/legal/owner evidence | Disposition |
|---|---|---|---|
| G0 selected scope | Explicit owner instruction selects 008/009 offline acceptance and 006 reminders; scope/disabled features recorded. | Owner still selects final pilot formats/domains and approves pending decisions. | Selection recorded; no release authorized. |
| G1 foundation | Existing foundation auth/money/tenancy suites rerun in G4; browser regression G5. | Actual CI run and external review unrun. | Not claimed passed. |
| G2 real-data pilot | Migrated SQLite lifecycle/hold/export/delete/restore/key/budget/readiness/queue/reminder evidence. | PostgreSQL full concurrency/restore; scanner/OS isolation; managed encryption/scheduled backups; installed supervisor/timer; lawful retention, field/processor notice, age/applicability; complete export/receipt UX; named on-call and recovery owner; independent security and CI/load acceptance. | Partial; real-data release blocked. |
| G3 planning beta | Existing exact goal/debt/FIN-01/14 fixtures plus delivery opt-in/quiet-hour/outage/revision/funded/expiry cases. | 003 owned portfolio and verified net worth; independent held-out planning eval; selected 006 UI/undo/explanation walkthrough; PG/planning load and affordability scope review. | Partial; planning beta not approved. |
| G4 domain modules | Existing module tests are regression coverage in G4 only. | Licensed sources/suitability, tax scope/packs, professional/legal applicability and domain-specific reviews. | Unrun release review; no enablement. |
| G5 connected/public/paid | No live connection or spend; safe offline reservation contracts only. | Provider/consent/price contracts, budget wiring/enforcement, verified mail/channels, MFA/IAM, payment/provider eligibility, production capacity, incident owner/security review. | Disabled; not passed. |

## Migration and recovery notes

Use existing migrations runner and verified backups; no live upgrade ran here.
0140 downgrade removes aggregate counters only, never user evidence. Stop paid
adapters before any downgrade so counter reset cannot reopen a spend budget.
Preserve current independent journal, all holds and suppression across recovery;
never replace it with an old backup. Journal metadata upgrade is additive and
should be forward-fixed, not rolled back to erase hold/receipt records. Restore
business DB into a new isolated path, replay suppression/current holds, purge
nonheld deleted evidence, restore/clean objects, and compare integer totals,
tenant access and surviving export before reopening. Existing plaintext SQLite
helper is synthetic only; encrypted production backup/key recovery is missing.

## Remaining / disabled at handoff and owner questions

Every task row above is partial for the listed acceptance gaps. Specifically:
retention/legal/processor/age decisions; async/full binary exports and new UI;
lost-response receipt recovery and approved journal retention; narrower lawful
hold scopes and concurrent operator controls; production keys/grants/audit/MFA;
legacy inference consent and budget wiring; verified recovery channel and edge
abuse policy; all-disk/global service budgets and measured price/cost per report;
installed supervision/scheduling/encrypted backups/on-call; CI, PostgreSQL,
sustained load/latency, independent eval/security/legal and production recovery.

Open owner decisions: D02 deployment/DB/scanner/key/journal location and grants;
D03 source/backup/journal/receipt retention and lawful hold basis/scope/duration;
D07 monetary/token/storage caps, prices/hardware/load targets; D09 in-app only
versus verified channels/locale and recurrence policy; D12 age/privacy/legal
applicability; privileged identity/MFA/recovery and user-MFA scope; named on-call,
recovery owner and lost-receipt support process. Safest defaults used without
waiting: synthetic data only, zero model reservations, generic in-app copy,
explicit due-date occurrences, immediate access suppression, bounded internal
holds, unapproved backup expiry and all external/paid/public integrations off.
