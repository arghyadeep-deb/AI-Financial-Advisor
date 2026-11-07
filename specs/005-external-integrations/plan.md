# Implementation plan — Credit tracking and external integrations

Read the [spec](spec.md). Implement manual credit after 001. Bank sync requires 002. Tax prefill/filing requires 004 and the documented authorized path. A product owner records evidence before any live connection is enabled.

Store dated credit observations and source under `backend/models/` and display due dates and unknown status in `frontend/`. If authorized, add separate provider interfaces under `backend/integrations/` for bank data, bureau results and ERI actions. Choose contracts after reviewing each provider’s official scope. Use mocks for development. Keep consent and external operation logs scoped to the user. Validate provider signature, state, event IDs, and retries. Queue updates and call deterministic ledger or tax services. No generic model tool may activate consent, access secrets, or submit a return.

Constitution check. Each provider has separate scopes, flags, least-privilege credentials, dry-run fixtures and recovery steps. Revocation prevents new sync immediately and retention follows the recorded policy. Define how filing handles duplicate submission, unknown outcomes, acknowledgement, e-verification and manual recovery before any live filing release.

## Shared implementation contracts
Read [architecture](../architecture.md), [financial rules](../financial-rules.md), [implementation order](../implementation-order.md), [evaluation plan](../evaluation-plan.md) and [release gates](../release-gates.md). Use shared snapshot and privacy services. Implement only the selected slice. Module paths are proposed boundaries; document any adjustment without weakening acceptance. Complete [acceptance mapping](acceptance.md) with actual test evidence.
