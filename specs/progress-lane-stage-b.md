# Stage B lane progress

Branch: codex/stage-b. Synthetic backend contracts only; no frontend changes,
external delivery, deploy, billing, trades, filing, remote push or secrets.

## Task status and files

All task-level acceptance below remains **partial**; no task checkbox is ticked.
- T0801 partial: backend/core/owned_stores.py; docs/privacy/stage-b-contracts.md.
  Registry coverage includes all current owned tables; full processor/field privacy
  review and approved retention still missing. Future owners must register hooks.
- T0802 partial: backend/services/auth_service.py, backend/schemas/platform.py,
  backend/controllers/platform_controller.py. List/revoke owner sessions,
  password change revokes all sessions and resets, throttled password reauth.
  Existing recovery reused. Recovery request rate limiting, MFA and full acceptance
  still missing; no second auth stack.
- T0803 partial: ConsentRecord + consent_service.py; append-only choices default
  false, queue checks current choice at publication. Existing model paths not wired
  to these records; provider adapters must check before fetch and publish.
- T0804 partial: backend/services/privacy/lifecycle.py exports registered stores
  after password reauth, excludes reset hashes. No persisted request/download API,
  expiring delivery or full field disclosure review.
- T0805 partial: same service, separate SQLite suppression journal, access blocked
  before purge, resume hook, anonymized user tombstones. Production durable journal,
  request state history, legal holds, backup expiry and future stores still missing.
- T0806 partial: existing signing-key rotation/config preserved; documented hooks.
  Managed encryption/key recovery, operator audit/grants and MFA unfinished.
- T0807 partial: tests/test_stage_b.py synthetic export/delete/pre-delete-backup
  restore drill. No complete production lifecycle/retention acceptance.
- T0901 partial: existing Config.validate and migrations_runner reused; operations
  notes added. No clean deployment or CI run; no deployment attempted.
- T0902 partial: backend/workers/queue.py and WorkItem transactional outbox/lease,
  heartbeat, fencing, bounded attempts, dead-letter sweep, consent publication
  checks and aggregate metadata counts. Orphan cleanup, supervisor, cancellation
  API, source revision checks, concurrency stress and adapter integration missing.
- T0903 partial: backend/core/limits.py + QuotaUsage atomic daily reservations,
  owner scope and 429. Not wired into existing analysis/upload/model paths;
  global circuit breaker, cost accounting and deterministic budget fallback missing.
- T0904 partial: aggregate queue state metrics only. Alerts, DB/worker readiness,
  latency/cost/deletion metrics and exporter incident acceptance missing.
- T0905 partial: no load experiment executed; ratified targets, hardware dataset,
  mocked cost/load harness and same-account import experiment remain.
- T0906 partial: deployment/recovery.py synthetic SQLite backup/restore helpers,
  separate suppression replay and exact paise preservation tested. No timed drill,
  production encrypted schedules or PostgreSQL restore evidence.
- T0907 partial: docs/operations/stage-b-contracts.md records limits and risks.
  Named on-call owner, ratified cost assumptions and release evidence remain open.
- T1005 partial: notification_service.py, NotificationPreference/DeliveryAttempt,
  strict schemas and authenticated APIs. In-app fixed safe copy, event deduplication,
  opt-out/categories and Asia/Kolkata quiet hours (deferred delivery retried by
  caller). Digest cadence, automatic scheduling, pagination and verified channels
  unfinished. External email/push disabled. No frontend files edited.

## Frontend APIs (Bearer token required)

- GET /sessions -> array of {id, created_at, expires_at, revoked_at, current}.
- DELETE /sessions/{id} -> 204; foreign/missing id -> same 404.
- POST /auth/password-change {password, new_password} -> 204; all tokens revoked,
  user must log in again. Password strings are SecretStr contracts.
- POST /privacy/consents {purpose: "model_inference"|"tracing", granted: boolean,
  notice_version: string(1..40)} -> 201 {id, purpose, granted, notice_version}.
- GET /preferences -> {enabled: true, categories: ["report_ready", "reminder"],
  quiet_start: null, quiet_end: null} by default.
- PUT /preferences sends the complete same shape -> 200 same shape. Hour integers
  0..23 must be paired and differ. Categories limited to those above. This uses
  PUT because the current CORS policy does not allow PATCH; main.py changed only
  to include this lane's router as instructed.
- GET /notifications -> at most 100 latest delivered owned notices:
  [{id, category, message, created_at}]. No arbitrary private content.
- Export/delete/status/download endpoints are NOT enabled; do not show working UI
  for these until the lifecycle request workflow is implemented.

## Migrations/recovery

0004 consent -> 0005 queue -> 0006 notifications -> 0007 quotas, parent 0003.
Models and migrations are synchronized. Roundtrip head -> 0003 -> head runs on a
fresh temp DB. Downgrade drops new evidence; take verified separate backups and
export evidence first. Never run downgrade on real data for this lane's tests.
Suppression journal must remain outside every restored DB/backup set. Helpers
refuse destination overwrite. See operations notes for remaining production gaps.

## Decisions/conflicts

User's explicit scope authorizes implementation despite planning-only spec headers.
Safe defaults: synthetic data only; no guessed legal retention/cost caps; no external
providers or public lifecycle route; inference/tracing consent defaults false.
Final acceptance is partial where release evidence or integrations are missing.
No shared progress/handoff files edited.

## Actual tests

Python for every run:
`C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe`

- `& '<python>' -m pytest tests/test_stage_b.py -q -p no:cacheprovider -W ignore`
  initial 4 passed; expanded run 2 failed, 4 passed (registry import order and
  reserved synthetic API email domain); both fixed. Next expanded run: 8 passed
  in 6.37s. SQLite fixtures use real Alembic migrations; external keys disabled.
- `& '<python>' -m pytest tests -q -p no:cacheprovider -W ignore`
  intermediate: 178 passed, 8 skipped in 72.46s. Final result recorded below.

Final exact command:
`& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore`

Actual final output:
```text
................sss.ss..............s........................ [ 38%]
........................................................................ [ 76%]
..................................ss.........                            [100%]
181 passed, 8 skipped in 70.46s (0:01:10)
```
The output above is the final emitted chunk (earlier progress dots omitted).
No PostgreSQL or CI run in this lane. Test-generated eval revision metadata was
restored to base; no unrelated evaluation artifact committed. `git diff --check`
passed. The remaining task-level gaps are listed individually above; do not treat
this slice as full Stage B completion or real-data release acceptance.

## Local commit blocked

Git restore/add/commit failed: permission denied creating the index.lock in the
sibling AI Advisory/.git/worktrees/AI-Advisory-stage-b directory. Sandbox allows
writes only in this worktree and forbids escalation. No commit was created and
no push attempted. This is the stopping condition: required local commit cannot
be completed safely under current filesystem permissions. All implementation
files remain in this worktree. Test-generated eval metadata restored using
read-only git show and writing only its worktree copy. Earlier unstaged diff
check passed; cached diff check did not validate these files because add failed.
All remaining feature work is enumerated above.
