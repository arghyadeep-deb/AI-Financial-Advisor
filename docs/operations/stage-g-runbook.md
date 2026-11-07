# Offline operations handoff

These are local synthetic procedures, not an installed service or production
approval. Never run drills against the user's DB. Full task evidence and owner
questions are in `specs/progress-lane-stage-g.md`.

Use the same application environment, migrated business DB, private storage key
ring, and independent `SUPPRESSION_JOURNAL` for workers and retention. Keep the
journal outside every business DB/object backup and restore set. Keep providers,
tracing and outbound channels disabled. Configure secrets via the existing secret
mechanism, never command arguments or logs.

| Configuration | Offline default | Meaning |
|---|---:|---|
| RETENTION_INTERVAL_SECONDS | 3600 | Successful source/export cleanup interval; 60..86400 |
| WORKER_STALE_SECONDS | 300 | Heartbeat readiness threshold; 30..3600 |
| SOURCE_STORAGE_LIMIT_BYTES | 104857600 | Per-owner source payload bytes physically present, including expired/held files |
| MODEL_DAILY_TOKEN_LIMIT | 0 | Owner attempt reservation token ceiling |
| MODEL_DAILY_COST_PAISE | 0 | Owner attempt reservation cost ceiling |
| GLOBAL_MODEL_DAILY_COST_PAISE | 0 | Aggregate attempt reservation cost ceiling |

Budget helpers do not enable providers and are not wired to legacy LLM calls.
Keep keys absent. A future approved adapter must atomically reserve each attempt's
verified upper-bound price/tokens, commit before calling, bound actual output to
the reservation and keep failed/unknown usage charged. Do not advertise measured
cost per report from reservations. Storage cap excludes exports, DB, backup and
ciphertext overhead; it is not a total-disk quota.

With configured synthetic DB/storage/journal, invoke these modules with the
required project Python (in production a reviewed supervisor would run worker
ticks frequently and the operations tick every minute):

```powershell
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m backend.workers.statements
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m backend.workers.notifications
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m backend.workers.operations
& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m backend.observability.health
```

The health CLI exits 1 for failed DB/worker readiness; output is aggregate
metadata. Restrict access at the operator boundary. A recent heartbeat establishes
liveness only, not scanner availability, throughput or correctness. Route alerts
to an owner-approved on-call system; the code's `operations` and
`privacy_operations` are responsibility roles, not assigned people.

Normal operations ticks never orphan-sweep while uploads run. Stop and drain
uploads first, then explicitly run `backend.workers.operations --quiesced-orphans`.
The default grace is 24 hours and the helper refuses less than one hour. Active
export objects and all held owners are excluded. Source metadata and immutable
ledger/report history remain after source-byte expiry. Expired exports cannot be
downloaded even before cleanup runs.

For DB outages, stop accepting work; inspect connection/migration health without
logging credentials. For queue lag, inspect worker supervision/leases, preserve
fencing and original event keys; never edit ledger evidence to retry. For model
budget exhaustion keep deterministic reports available. For failed deletion,
preserve suppression and retry with `resume_delete` or the operations tick. Hold
states never imply erasure. Legal hold creation/release is restricted internal
code, with fixed basis codes, explicit account scope and <=90-day expiry; no
public operator API is provided. Account-wide scope is deliberately conservative
and needs legal approval; narrower lawful scopes and concurrency/IAM review remain.

Deletion responses include a 256-bit receipt capability. Keep it private and POST
it in the body to `/privacy/deletion-receipt`; never put it in a URL or analytics.
It permits minimal status only after login sessions have been revoked. Backups
always say `expiry_unapproved`, never `backup_expired`. If the deletion request
fails before the response is received, receipt recovery is not implemented:
operator assistance remains necessary. An approved retention policy for receipt
digests and journal records is still required.

For recovery, use `deployment.recovery.backup/restore` only with isolated SQLite
files and unused destinations. Restore requires the current independent journal,
then replays suppression, honors current holds and purges deleted evidence before
reopening. Never restore an old journal. Compare row counts, integer totals,
survivor export equality and tenant denial. Separately restore encrypted objects
and replay suppression as in existing Stage C drills. Rotate local storage with
both keys available, verify reads, rewrite atomically, then test new-key-only
recovery and old-key denial. Do not retire managed keys until all live objects,
retained backups and rollback/recovery windows have been verified.

Revision 0140 branches from 0110 and creates only nonpersonal operational counters.
Use the existing migrations runner; downgrade removes counters/heartbeats only.
Disable paid adapters before downgrade: resetting counters must not reopen spend.
User evidence remains untouched. Journal v2 adds nullable `metadata_json` to the
existing external event table; legacy records are preserved. Do not roll back the
journal to erase holds/receipts; keep a separately protected current copy and
forward-fix. No scheduled encrypted backups, production OS grants/MFA, PostgreSQL
restore or RPO/RTO guarantee is implemented by these procedures.
