# Feature specification — Privacy, consent and account lifecycle

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: Required before real customer data. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Control personal data.** User can see what is stored and shared, export owned data and request deletion with a clear completion status.
- **US2 (P1) Withdraw access.** Revoking a connected provider or family grant stops future access, including jobs queued earlier.
- **US3 (P2) Recover and secure an account.** A user can recover access, revoke sessions and change credentials without exposing whether another person has an account.

## Functional requirements
### F008-FR01 — Data inventory and purpose
Maintain a field-level inventory of financial documents, profiles, prompts, checkpoints, logs, analytics and exports; record purpose, processor, location, retention and access. No customer documents for model training by default. Track notice versions and necessary versus optional choices.

### F008-FR02 — Lifecycle workflow
Export uses reauthentication, private short-lived delivery and ownership checks. Deletion moves requested -> access_blocked -> purging -> live_complete -> backup_expired, with failed_retryable and documented hold states. Immediately block reads, new jobs, sharing and provider fetches after confirmation.

### F008-FR03 — Complete erasure and restore
Delete source objects, derivatives, DB rows, caches, indexes, chat, graph state and exports according to policy; record only minimal nonfinancial completion evidence. Keep a deletion suppression journal outside backup restore so old backups cannot resurrect access. Disclose backup expiry; never claim total erasure while backups remain.

### F008-FR04 — Session and recovery controls
Single-use short-lived recovery tokens, rate-limited generic responses, session revocation on reset and suspicious activity, reauthentication for export/delete/sharing. Enable MFA for privileged operators; assess user MFA before broad launch. Never expose tokens in URLs/logs beyond an intentionally protected recovery flow.

### F008-FR05 — Encryption and operator access
Encrypt transport and private storage/backups; managed keys and rotation with recovery drill. Least-privilege service accounts. Support staff see metadata by default; any exceptional document access needs time-bounded purpose, user authorization where applicable and audit. No broad raw-data admin dashboard.

### F008-FR06 — Consent and applicability
Document processors and third-party data transmission; separate model inference from tracing. Withdraw optional processing without breaking deterministic reports. Complete the dated privacy applicability decision before live data, including age scope, retention exceptions and rights handling.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
