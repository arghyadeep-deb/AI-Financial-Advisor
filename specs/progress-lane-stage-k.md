# Lane K: product security and mail

Worktree based on integration, initial single head 0141. No staging, commits,
pushes, deployment, real mail or secrets. Common addendum overrides the earlier
commit instruction. Read foundation progress/handoff, implementation-order,
previous lane remaining sections, 006/008/009/010 spec/plan/tasks and shared
financial rules, agent quality, constitution and release gates. Selected lane
authorizes this implementation despite planning-only spec headers.

## MAIL (008 T0802, 009 T0902/T0903, 010 T1005, 006 T0606)

Status: partial at channel/release acceptance; implemented offline backend slice.
Files: `backend/services/mail_service.py`, `backend/workers/mail.py`, existing
auth/notification services, config/operations/owned_stores, encrypted storage key
ring, models/platform schemas, migration 0180, `.env.example`,
`docs/operations/stage-k-runbook.md`, `tests/test_stage_k_mail.py`.

Fixed server-side plain-text templates; strict mailbox/token validation; no
user-controlled HTML/headers. Fake default, bounded in-memory synthetic inbox.
Resend HTTPS adapter explicitly gated, missing key refuses sending, bounded
timeout/no redirects, opaque per-message idempotency keys, metadata-only logs.
Reset issuance and mail payload queue atomically (encrypted under existing ring).
Existing recovery injection seam retained for legacy tests only. Notification
events reuse 010 service, current 006 reminder evidence, quiet/preferences gates,
shared outbox/fences and deletion owner locks. Daily global quota uses existing
operations counters, conservatively charges all attempts durably before network,
defers at cap, bounded retries/dead-letter/review after ambiguous 23h window.

Actual commands (Python path used exactly as instructed):

- K1: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_k_mail.py -q -p no:cacheprovider -W ignore`
  Initial captured run: 2 failed, 12 passed in 8.13s. Fixed stale delivered
  notification bypass of updated preferences and incorrect test migration import.
- K2: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_k_mail.py tests/auth tests/test_stage_d.py tests/test_stage_g.py -q -p no:cacheprovider -W ignore`
  An earlier invocation before K1's fixes emitted two failures, but its final
  output/session handle was not retained; no completed result is claimed for
  that attempt. K1 captured both failures. The completed corrected K2 run:
  99 passed in 87.90s. This run preceded the extra mail expiry/quiet/review cases
  and final admission refactor; final mail-only and full-suite evidence follows.
- K3: same exact command as K1 after admission fixes and added quiet/expiry/
  ambiguity tests: **17 passed in 11.74s**. All Task 1 implementation edits
  preceded this run; proceeding sequentially to MFA.

Decisions/remaining: verified-channel enrollment is absent in the base. Safest
default awaiting owner approval: `NOTIFICATION_EMAIL_ENABLED=false`; new email
opt-in alone cannot verify an address. Server-owned verification digest has no
public setter. Add reviewed address-verification UX/flow before normal-user email
notifications. Resend fake/default and live-off prevent any real integration.
No DNS/provider/production/PostgreSQL/CI release acceptance, supervisor, webhook
bounce handling or independent review claimed. Missing storage configuration
fails recovery closed with generic 202 + metadata warning; operator must configure
the existing ring before enabling recovery delivery. The mail processor/channel,
sending domain, account-wide allowance sharing, UTC cap and critical-message
policy remain owner decisions (D06/D09). A delivery can expire while deferred;
state is explicitly expired. No silent deletion of queued messages.

Migration/recovery: 0180 down_revision 0141. Mail store registers metadata export
and purge before queue; encrypted payload excluded from export. Uses the existing
nonpersonal operations store for quota. Stop workers/live sending and back up DB
and key ring before downgrade; downgrade drops mail evidence and optional channel
columns, so prefer flag-off/forward-fix or archive first. Synthetic upgrade,
downgrade/re-upgrade test is in K1/K3. No dependency changes.

## MFA (008 T0802 / F008-FR04)

Status: done for selected backend slice, with release/UI limitations below. Files:
`core/totp.py`, `schemas/mfa.py`, `services/mfa_service.py`,
`controllers/mfa_controller.py`, existing auth service/controller/contracts,
dependencies, models, owned_stores, one main.py include_router line, migration
0181, `tests/test_stage_k_mfa.py`, PUBLIC test inventory, runbook.

Optional TOTP with RFC6238 SHA1/6/30; standard-library primitives, +/-1 step,
atomic replay CAS; existing encrypted storage key ring for secret, ten hashed
single-use random recovery codes. Setup reauth/TTL, URI disclosed only before
confirmation; confirmation revokes prior sessions. Password login yields a
single-use five-minute digest-only challenge, owner-shared bounded DB throttle.
Disable/regenerate reauthenticate and invalidate sessions/challenges; recovery
use revokes all old sessions, new verified session only. Password reset preserves
factor and invalidates challenges. Required policy defaults false; when true,
unenrolled login/signup sessions only authorize setup/status/logout. Existing
sessions cannot bypass enrollment or policy. Registry export omits secret/code/
challenge material; purge owns all three tables. No new dependency.

- K4: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_k_mfa.py tests/auth -q -p no:cacheprovider -W ignore`
  **40 passed in 26.73s**. Includes all RFC6238 Appendix B vectors for SHA1/256/512,
  step window/replay, real HTTP enrollment/login/recovery/reauth/mandate/purge,
  SQLite concurrent step race, schema downgrade/re-upgrade and legacy login tests.
  Added password-reset challenge invalidation, setup expiry/ownership and recovery
  race tests after this initial run; final evidence follows.
- K5: exact same command as K4 after those changes: **43 passed in 29.94s**.
  MFA backend slice done with the release/UI limitations below; receipt work
  began only after this run completed.

Decisions awaiting owner approval: optional user opt-in enabled as explicitly
requested, policy false; no privileged/operator identity, production rollout or
break-glass bypass. Missing ring fails closed. Frontend MFA journey belongs to
orchestrator and is not implemented here. Lost-factor support, factor retention,
operator IAM/security review and PostgreSQL concurrency/production key retirement
drill remain release work. Regeneration requires password plus verified session;
both code regeneration and setup revoke prior sessions as conservative defaults.
Throttle uses existing login bounds; successful verify admissions count too.

Migration/recovery: 0181 down_revision 0180. All three new tables registered for
safe export/purge. Existing sessions default unverified. Back up DB/ring and stop
auth writes before downgrade; dropping enrolled credentials removes protection,
so prefer forward-fix. Existing file rotation does not rewrite DB ciphertext;
retain old ring keys pending an explicit DB-value rotation drill.

## DELETION-RECEIPT THROTTLE (008 T0805 / F008-FR02/03)

Status: done for selected backend task. Files: shared `core/throttle.py`
(optional bounded parameters preserve all existing defaults), config,
`controllers/platform_controller.py`, external journal lifecycle and
`services/privacy/journal_migrations.py`, PUBLIC inventory comment,
`.env.example`, `tests/test_stage_k_receipts.py`, runbook.

Before token lookup or body validation, the endpoint consumes a global bucket
and a source bucket using the existing atomic DB throttle. Defaults awaiting
owner ratification: 10/source and 1000/global per 900 seconds. Source is the
actual transport client, never untrusted forwarding headers. 4096 fixed source
hash buckets bound storage; collisions share a conservative cap, global caps
also charge source-denied requests. Valid-shaped unknown tokens stay 404;
limited valid/unknown tokens return identical 429, Retry-After and no-store.
Existing valid-token receipt status/backup status is unchanged.

Decision/conflict: deletion receipts live in the separate restore-independent
SQLite suppression journal, not in SQLAlchemy models or business Alembic. A
business Alembic migration must not read an operator-configured journal or move
capabilities into backups. Therefore the lookup-column migration is the existing
journal's additive v3 migration (BEGIN IMMEDIATE, backfilled full SHA256 digest,
indexed lookup plus owner/status index), with a reversible offline downgrade
helper preserving original JSON. No business table/new store is introduced and
no fictitious Alembic revision is added. Business single head remains 0181.
This follows Stage G's in-place v2 journal migration convention; owner can choose
an explicit separate journal migration CLI later. Malformed legacy receipt
metadata never authorizes access. Exact-query EXPLAIN proves index lookup, with
constant-time digest comparison on both found and missing paths.

Recovery: back up the journal independently, stop API/operations writers for an
offline downgrade, preserve JSON digest evidence; downgrade helper removes only
new indexes/column. Upgrade on next journal open backfills legacy digests again.
Never restore the journal from an old business backup. Source buckets reflect
the immediate peer behind a proxy; trusted proxy normalization/edge protection
is deployment-owner work. Ratify caps and journal retention/D03, keep existing
release gates. No feature/release checkbox in shared files changed.

- K6: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_k_receipts.py tests/test_stage_g.py tests/api/test_tenancy.py -q -p no:cacheprovider -W ignore`
  **146 passed, 8 skipped in 113.92s**. Covers real SQLite concurrent source/
  global caps, unchanged receipt API, denied token lookup at cap, fixed source
  bucket collision, expiry/reopening, external journal concurrent migration,
  legacy backfill/downgrade/re-upgrade, index EXPLAIN and constant-time calls.
  Includes existing Stage G privacy/restore/hold/recovery and all route tenancy
  checks. Eight skips are explicit public-route inventory cases, not passes.

## Final acceptance command log

- K7: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/test_stage_k_mail.py tests/test_stage_k_mfa.py tests/test_stage_k_receipts.py -q -p no:cacheprovider -W ignore`
  Initial expanded acceptance: **4 failed, 43 passed in 32.00s**. Four new
  planning-to-mail cases used a synthetic account helper without explicitly
  enabling its test-only statement flag. Fixed fixture setup, no production
  gate change. Rerun identical command: **47 passed in 36.88s**. Includes actual
  006 bill/goal -> 010 notification -> mail outbox -> fake delivery, and stale
  opt-in/resource revision suppression before external delivery.
- K8 (run tests/web once): `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests/web -q -p no:cacheprovider -W ignore`
  **18 passed in 49.81s**. Existing browser regression only; no MFA/mail UI
  acceptance claimed. No frontend file edits.
- K9: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
  Interrupted with Ctrl-C at roughly 12% (exit 1, no result claimed) to apply
  final reset/change-password ordering improvement: invalidate challenges before
  session revocation so an already-finishing MFA verification session is also
  included in reset revocation. SQLite tests cover invalidation; full PostgreSQL
  interleaving remains unrun. Restarted the identical command as K10 after edit.
- K10 authoritative final backend: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -X utf8 -m pytest tests --ignore=tests/web -q -p no:cacheprovider -W ignore`
  All final implementation/test edits preceded this invocation. Actual output:

  ```text
  ....... [ 98%]
  ...........                                                              [100%]
  577 passed, 10 skipped in 334.23s (0:05:34)
  ```

  Ten skips = eight explicitly public routes and two opt-in PostgreSQL cases;
  none counted as passed. Together with K8: **595 passed, 10 skipped** across
  backend and browser suites. Browser tests were run once as requested; the
  final ordering-only auth change is covered by this final backend run.

## Remaining, disabled and owner questions

- MAIL is **partial** for verified-channel release: the server mail interface,
  encrypted outbox, reset wiring, Resend mock and 010/006 event wiring are tested;
  ordinary users cannot verify a notification channel yet. Orchestrator owns
  frontend; a reviewed address-verification service/journey and opt-in UX are
  required before enabling notification mail. No public verification setter or
  invented verification/owner approval was added. Confirm critical reset-channel
  policy, sender/domain, processor, domain authentication and shared-account
  budget allocation. Resend remains live-off and fake by default.
  Mailboxes are strictly ASCII single addresses; international local parts need
  separately reviewed support before mail delivery can be promised for them.
- MFA and receipt tasks are done for the requested backend slice. Existing
  feature-wide 008/009/010/006 release acceptance stays **partial**, including
  actual MFA/challenge/recovery UI, privileged-operator identity/IAM/MFA,
  lost-factor/support/break-glass policy, receipt lost-response support,
  independent security review, CI, full PostgreSQL races, production restore/key
  retirement/retention and installed supervision. No production protection,
  delivery, availability or regulatory acceptance is claimed.
- Confirm whether/when to mandate MFA after UI/support readiness; safe default
  false. Optional opt-in enrollment was explicitly requested and is available.
  Confirm five-minute challenges, ten-minute setup, ten recovery codes, password
  plus verified-session reauth for management and conservative session revocation
  on confirmation/regeneration/recovery. No email-based MFA bypass exists.
- Confirm proposed UTC mail cap (<=100 attempted sends/day), retry/dead-letter
  handling, owner/on-call and review of ambiguous deliveries before idempotency
  expiry. Old ring keys must remain available for DB ciphertext; existing file
  rotation does not rewrite the new DB fields. Back up DB and keys together;
  owner must complete DB-value rotation/retirement drill before production use.
- Confirm 10/source, 1000/global per 900s receipt limits, bounded bucket collision
  tradeoff and trusted-proxy/edge policy. Immediate-peer sources intentionally
  ignore spoofable headers. Keep suppression journal separate from all business
  restores; approve its durability/IAM and D03 retention independently.
- No new dependency, live network integration, deployment, billing, filing,
  trading, push, commit or staging. No frontend/shared progress/handoff edits.
  Financial engines, money and authoritative LLM boundaries were not changed.
  `.env.example` contains placeholders only; no `.env` values were printed.

Read-only validation before final suite completion: `git diff --check` passed;
required Python `ast.parse` passed all 86 backend/new-test/lane-migration Python
files. Restricted-path diff confirmed only one added main.py include_router
line, and no frontend or shared progress/handoff changes. Final suite and any
test-generated artifact reconciliation will be recorded below.

Final repository checks after K10: `git diff --check` passed. Eval runner changed
only `evals/results/latest.json`'s code_revision. Required Python compared the
entire current JSON against HEAD after replacing only that generated field,
verified the new revision equals this worktree's HEAD, and restored the initial
HEAD artifact with checkout CRLF endings. Restricted-path diff is empty for
evals, frontend, dependency pins and shared progress/handoff files. main.py has
exactly one added include_router line. No user data or git index was modified;
all lane work remains in the working tree for the orchestrator.
