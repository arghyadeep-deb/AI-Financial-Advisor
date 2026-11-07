# Offline operations contracts

Queue: `backend.workers.queue`. Enqueue with business writes, commit once. Owner
and event key unique; racing enqueue callers retry their transaction after unique
conflict. Claim returns (id, fencing token); heartbeat extends an active lease.
Complete takes a DB-only callback and commits publication with the lease update.
Callbacks must not commit or perform external side effects. Stale/expired fences
fail. Before publication, active account and current optional consent are checked.
Three expired attempts move to dead letter when the sweeper runs. No background
worker supervisor, object orphan sweeper or privileged retry API is enabled.
Consumers must call the same service; no separate queue implementation.

Quotas: `backend.core.limits.reserve` reserves integer daily units within the
business transaction. D07 limits must be supplied by the caller; there are no
approved paid-provider caps. Existing analysis paths are not yet wired to quotas.
Queue metrics aggregate state counts only; operational alert routing is unfinished.
Existing Config.validate remains the production startup check and migrations_runner
remains the migration/backup entry point; this lane adds no competing deployment.

`deployment.recovery.backup/restore` use SQLite backup into a new path only, check
integrity, replay the separate suppression journal, and purge suppressed accounts.
These helpers are for synthetic offline drills. They do not provide encrypted
scheduled production backups or PostgreSQL recovery. Stop traffic before restore;
restore into isolation; check schema, exact totals, counts, owners and journal;
reopen only after those checks and production release review. Never overwrite the
live DB. Downgrade only after a separate verified backup and explicit evidence
export: revisions 0004-0007 drop their new tables. Prefer a forward fix.

No deployment was performed. Load targets are not ratified or benchmarked; cost
assumptions, hardware p95, on-call owner, RPO/RTO and canary process remain open.
No load or cost claim is made from unit tests. All model keys are disabled in tests.
