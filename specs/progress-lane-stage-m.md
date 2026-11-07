# Stage M - integration safety (005) and commercial support pieces (013), no live provider

Migrations 0230 (integration tables), 0231 (support tables). Synthetic-only gate unchanged; the fake bank refuses to exist outside it.

| Task | Result |
|---|---|
| T503 provider documentation | done as a template: docs/integrations/provider-onboarding.md. Every provider/legal item is PENDING owner. |
| T504 test-only bank adapter + consent/replay tests | done: backend/integrations/{base,fake_bank,service}.py, tests/integrations (18 tests). |
| T508 sync/overlap and consent-race tests | done: revocation during fetch commits nothing; replays/overlaps/out-of-order never duplicate evidence. |
| T509 unknown-outcome state machine (mocks) | done: timeout -> unknown -> reconcile by status; never resubmitted; final states are final. |
| T510 onboarding/exit readiness doc | done as a template (same file); provider answers PENDING. |
| T505, T506 bureau/ERI contracts, live-flag approvals | not started; need provider evidence and owner approval. |
| T501, T502, T507 credit observations UI/discrepancy flow | backend manual entry exists (lane L); UI and discrepancy flow not done. |
| T1301 pricing/service policy | done as a record that NOTHING is decided: docs/product/pricing-and-service-policy.md. |
| T1302, T1306 billing event machine and acceptance | not started (no provider; deferred). |
| T1303 entitlements/downgrade | done: backend/services/entitlements.py; privacy/export/deletion in every plan; client cannot unlock. |
| T1304 support tools | PARTIAL: request-ID lookup (metadata only, audited), owner-issued time-limited document grants, owner-visible access log, API for owners. No operator UI/CLI and no appointed operator; frontend part not done. |
| T1305 privacy-safe analytics | done: allow-list sanitizer; no exporter; payload tests show no financial fields. |

Tests: `python -m pytest tests/test_stage_m_commercial.py tests/integrations tests/test_stage_l.py` -> 68 passed (full-suite result recorded in implementation-progress).
