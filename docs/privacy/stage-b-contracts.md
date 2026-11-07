# Stage B synthetic storage policy

No real-data release is authorized by these contracts. D02/D03/D07/D12 remain
open: region, encrypted stores, retention and backup expiry, paid-provider caps,
privacy applicability and operator ownership need product decisions.

`backend/core/owned_stores.py` is the shared registry. Every new table/store owner
must register a field-safe exporter and idempotent purge function, purpose,
retention, and test coverage. Callbacks use the caller transaction and never
commit. Coverage validation fails closed on unknown tables. Users remain as
inactive anonymized tombstones to prevent identifier reuse. Login throttle is a
hashed-email security counter not included in user exports; its expiry policy is
still pending. Export excludes password/reset token hashes. DB columns are the
field inventory for registered tables; production processor/field review remains
incomplete. No model training is authorized; inference/tracing choices default off.

Synthetic lifecycle service has no public route. Caller supplies an independently
persisted suppression journal outside restored backup sets. Replay before serving
any restored database; never claim backup erasure before approved expiry. It is
not safe to use a database-local journal that rolls back with a backup. Account
access is committed blocked before purging; retry through `resume_delete` after
failure. New external stores must supply their own tested idempotent hooks.

Existing auth configuration supplies current and previous signing keys. Rotation:
issue with new current key, retain previous keys for the token TTL, revoke affected
sessions in an incident, remove retired keys. Managed storage key rotation,
privileged MFA and operator grants are not implemented. External integrations,
email/push delivery, public export URLs, and live personal data remain disabled.
