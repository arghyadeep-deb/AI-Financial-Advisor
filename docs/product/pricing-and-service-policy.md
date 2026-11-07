# Pricing and service policy (T1301)

Status: NO PRICING DECIDED. Nothing here is a commitment and no price has been invented.

* The product is a free controlled pilot. `BILLING_MODE=free_pilot` is the only accepted value; paid billing is deferred.
* No payment is requested or taken; there are no billing-provider credentials or code. `GET /billing/entitlement` reports plan `free_pilot`.
* Privacy export, account deletion, consent and session controls are available on every plan, including a downgraded one
  (`backend/services/entitlements.py`, tested). Entitlements come from server state only.

## Decisions the owner must make before any paid plan

| Decision | Status |
|---|---|
| Tiers and which features are paid | PENDING owner |
| Prices, currency, GST treatment | PENDING owner |
| Refund, cancellation and dispute policy | PENDING owner |
| Billing provider (shortlist in docs/research/provider-shortlists.md) | PENDING owner; none selected |
| Support hours, channels, response targets and who staffs them | PENDING owner (no support capacity decided) |
| Support access to user documents | Implemented as owner-issued, time-limited, audited grants; policy wording PENDING |

## Support service model in code today

Support staff use request IDs (metadata only: method, route template, status, duration) and cannot read a source document unless
the owner grants access to that one document for at most 72 hours. Every lookup and read attempt is audited and shown to the owner at
`GET /support/access-log`. There is no operator UI and no appointed operator.
