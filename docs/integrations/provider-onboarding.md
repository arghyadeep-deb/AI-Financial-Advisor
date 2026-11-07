# Provider onboarding and exit readiness (T503, T510)

Status: TEMPLATE. No provider is selected, no credentials exist and every live integration is disabled. Research
only is in `docs/research/provider-shortlists.md`. Complete one section per adapter BEFORE any credential is requested
and before a live flag exists. Each live flag also needs separate owner approval and an independent review (T506).

The code that exists today is provider-neutral: `backend/integrations/base.py` (contract), `service.py` (consent, replay-safe sync,
unknown-outcome operations) and `fake_bank.py` (test-only, refuses to run outside the synthetic sandbox).

## Checklist per adapter (all fields must be filled; "unknown" blocks go-live)

| Item | Bank/AA adapter | Bureau adapter | ERI/filing adapter |
|---|---|---|---|
| Provider and licence/registration | PENDING | PENDING | PENDING |
| Who may legally use the data (eligibility, FIU / specified-user status) | PENDING legal advice | PENDING legal advice | PENDING |
| Licensed use and use restrictions | PENDING | PENDING | PENDING |
| Scopes requested (minimum only) | transactions (code supports only this) | n/a | n/a |
| Credential owner, storage, rotation | PENDING | PENDING | PENDING |
| Consent text, purpose, duration, revocation path | Revocation implemented and race-tested; text PENDING | PENDING | PENDING |
| Retention of provider data | PENDING (D03) | PENDING | PENDING |
| Incident owner and contact | PENDING (no operator appointed) | PENDING | PENDING |
| Outage behaviour | Sync fails closed, nothing partial is committed; user can still upload files | same | same |
| Unknown-outcome handling | Implemented: timeout -> `unknown` -> status check; never resubmitted | n/a | PENDING |
| Rollback / kill switch | Disable the live flag; manual and file paths continue | same | same |
| Exit plan (data export, deleting provider-held data, switching provider) | PENDING | PENDING | PENDING |

## Behaviour already enforced by tests (tests/integrations)

* Replay and overlapping windows never duplicate evidence (de-duplicated by provider event id before the ledger).
* Arrival order does not change the evidence that is stored.
* A consent revoked or changed during a fetch commits nothing.
* A timeout after submission is reconciled by asking the provider; the action is never submitted twice.
* Provider text is neutralised against spreadsheet formulas; invalid provider records reject the whole batch.
* Everything is owner-scoped; another user gets 404.

## Not decided (owner)

Which providers, whether the product may act as an FIU / specified user, consent wording, retention, incident owner.
