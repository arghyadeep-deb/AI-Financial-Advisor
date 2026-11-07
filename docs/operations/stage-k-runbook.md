# Lane K: mail and account security

All release gates still apply. Defaults are synthetic fake mail and no external
sending. No live provider, domain, credential or external delivery was exercised.

## Mail configuration and domain verification

Mail uses `MAIL_PROVIDER=fake` by default. Its bounded process-local inbox is for
synthetic tests only. Durable work lives in the existing WorkItem queue; addresses
and reset codes are encrypted with the existing `STORAGE_KEYS_JSON` key ring and
`STORAGE_ACTIVE_KEY`. Configure private storage through the existing runbook;
there is no implicit persistent key. Missing keys fail closed with a generic
recovery response and metadata warning. Existing tests retain their injected
delivery seam; production defaults always enqueue. Tokens are never in work keys,
URLs, traces, error text or exports. Start a delivery tick with the project's
Python: `-m backend.workers.mail`; install supervision separately before release.

Before enabling Resend, the owner must approve the processor/channel (D06/D09),
choose a dedicated sending subdomain and verify control in Resend. Publish the
exact DKIM and SPF records provided for that domain in its authoritative DNS;
merge SPF mechanisms into the existing SPF policy rather than publishing multiple
SPF records. Publish an aligned DMARC policy under `_dmarc`, review aggregate
reports privately, and tighten policy only after verifying legitimate senders.
Wait for the provider's domain verification and inspect authentication results in
an owner-authorized synthetic delivery before enabling real recipients. No DNS
changes are made by this implementation. Use a send-only scoped key in the secret
manager, `MAIL_FROM` as a single mailbox on the verified domain,
`MAIL_PROVIDER=resend`, and explicitly opt into `MAIL_LIVE_ENABLED=true`.
Absent credentials or the live flag, the adapter refuses to send.

Reference: [Resend send API](https://resend.com/docs/api-reference/emails/send-email)
and [idempotency](https://resend.com/docs/dashboard/emails/idempotency-keys).
HTTPS calls use a bounded timeout, no redirects, server-owned subject/text and an
opaque WorkItem ID as the idempotency key. Retry through the same queue only;
never clone messages after an ambiguous response. Provider response bodies and
exception details are intentionally discarded.

The global existing quota service caps attempted messages at `MAIL_DAILY_LIMIT`
(0..100, default 100) per UTC day. Retries are conservatively charged, including
unknown outcomes. Daily exhaustion defers the same work to the next UTC day;
expired reset instructions are explicitly marked expired rather than sent late.
Provider failures retry up to the existing queue limit, then remain dead-lettered
for operator review. Attempts older than 23 hours require review because provider
idempotency lasts 24 hours. Check aggregate queue metrics and mail state counts;
never dump payloads or use addresses as monitoring labels. Other applications
sharing the same Resend account consume its allowance outside this counter: set
a smaller application cap and coordinate that account's budget before release.

Notification mail is additionally gated by `NOTIFICATION_EMAIL_ENABLED=false`.
The existing preference contract accepts `email_enabled=false` by default. A
server-owned `verified_email_hash` must match the current account address; no API
can set verification. Until a reviewed email-verification journey is implemented,
the channel remains unavailable to normal users. Reset messages are a separate
critical transactional channel. Report/bill/goal events use the shared 010/006
notification service and outbox, fixed generic copy, and recheck preference,
quiet hours, owner status and current reminder evidence immediately before send.

## Mail migration and recovery

0180 follows 0141, adds encrypted mail payloads and optional notification-channel
fields. Its store exports metadata and purges before WorkItem rows. Stop mail
workers and live sending before schema changes; back up the business DB and key
ring. Upgrade with the existing migrations runner. Downgrade removes the new
mail table and preferences: archive needed metadata first, never silently discard
queued work. Prefer disabling live mail and forward-fixing. Retain old keys until
pending mail and all other encrypted objects are rotated/expired. No pins changed.

## User MFA (0181)

Optional enrollment is available without a separate feature flag; `MFA_REQUIRED`
defaults to false. When true, unenrolled password/signup sessions can access only
MFA enrollment/status and logout. The backend enforces this on protected routes;
it is not a frontend hint. The orchestrator must implement enrollment/challenge/
recovery UI before mandating the policy. No privileged operator identity or
break-glass console is introduced; those remain a separate release decision.

Authenticated `POST /auth/mfa/enroll/start` reauthenticates the password and
returns only a single setup `otpauth://` URI (SHA1, six digits, 30s, opaque account
label). Do not log, copy to public QR services or persist the URI in browser
history. Setup expires after ten minutes. Confirm via `/enroll/confirm`; the
secret cannot be obtained again after confirmation. Confirmation revokes old
sessions and returns a verified replacement plus ten recovery codes exactly
once. Save codes privately. The database stores the secret encrypted with the
existing key ring, and random 128-bit recovery codes only as SHA256 hashes.

Password login for enrolled users returns a five-minute opaque challenge rather
than an access token. `POST /auth/mfa/verify` consumes a challenge with a TOTP or
unused recovery code. The +/-1 step window has a monotonic last-used step; a code
accepted ahead of time cannot be reused in the next step. Verification admission
uses the existing DB throttle (owner cap shared across challenges). Successful
admissions count too, conservatively, so rapid legitimate logins may throttle.
Recovery use revokes all prior sessions and invalidates other challenges; the
caller receives a verified replacement. Password reset does not remove MFA and
invalidates outstanding challenges. No email-based MFA bypass is provided.

Disable and recovery-code regeneration require an MFA-verified bearer session
and the existing password reauthentication. Both revoke prior sessions and
challenges. Regeneration returns new codes and a replacement session. Disable
requires signing in again; it is denied while `MFA_REQUIRED=true`. Loss of all
factors/codes has no automated bypass: owner must approve a separately audited
support/recovery process before broad release. No operator may read MFA secrets
through account export. Registry purge removes all three new MFA tables.

0181 follows 0180 and adds MFA tables plus `auth_sessions.mfa_verified` (old
sessions default false). Preserve keys and take a backup before upgrading. Do not
downgrade with enrolled accounts: it destroys the factor and replay evidence.
Disable the policy only with an approved account migration/recovery procedure;
prefer forward fixes. Retained old storage keys must decrypt pending mail and
enrolled credentials. A storage-key retirement drill must include these DB values;
the existing file rotation CLI does not automatically rotate encrypted DB fields.

## Deletion receipt admission and journal v3

`POST /privacy/deletion-receipt` remains public because account deletion revoked
all sessions; its only authority is the high-entropy receipt in the request body.
It never grants account data access. Admission now uses existing DB throttle
counters before lookup (including valid/invalid tokens). Proposed defaults are
10 per source, 1000 globally per 900 seconds; `.env.example` exposes the three
bounded settings. Saturation returns uniform 429 with Retry-After and no-store;
unknown valid-shaped tokens return uniform 404 with no-store. Never log tokens.

Source identity uses the actual connection peer and ignores forwarding headers.
4096 hashed source buckets bound persistent counter cardinality; collisions
conservatively share admission, and blocked sources still spend global allowance.
Behind a proxy, configure trusted peer normalization at deployment before release,
or that proxy's users share a source cap. Owner must ratify the limits and edge
abuse policy. No distributed proxy/IP trust is assumed by this backend change.

The independent suppression journal upgrades in place under BEGIN IMMEDIATE to
v3: `receipt_digest` is backfilled from preserved JSON and indexed. Status lookup
also has an owner/state index. No per-request scan of receipt rows remains.
This schema belongs to the journal, outside the business Alembic database and
backup set. Take an independent journal backup before deployment. If rollback
is needed, stop all journal writers and call
`journal_migrations.downgrade_receipt_lookup(connection)` in a transaction. That
removes only the lookup column/indexes; original digest JSON remains available
to old code. Current code upgrades it again on the next open. No older business
backup may overwrite the current journal. Production durability/IAM/retention,
lost receipt support and full restore acceptance still need owner approval.
