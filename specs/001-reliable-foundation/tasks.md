# Tasks — Reliable analysis and account safety

Prerequisites are the [spec](spec.md), [plan](plan.md), and [review checklist](../review-checklist.md).

## Setup and prerequisites

- [x] T101 Pin and verify dependencies in `backend_requirements.txt` (and `requirements-dev.txt`; `frontend/requirements.txt` was removed with Streamlit) or one reproducible lock workflow. Document fresh install and test commands in `README.md`.
- [x] T102 [P] Write synthetic baseline reproductions for deficit, stale report, ignored inputs, unknown credit, portfolio overwrite, and provider failure in `tests/`.
- [x] T103 Add migrations, test PostgreSQL wiring, and document existing SQLite backup/import in `backend/core/database.py` and `migrations/`.

## US1 Consistent finance

- [x] T104 [US1] Add exact money representation and a profile revision boundary in `backend/models/`, `backend/schemas/`, and `backend/services/profile_service.py`.
- [x] T105 [US1] Add affordability, missing-data, and observed-versus-projected rules in `engines/` and `backend/services/analysis_service.py`.
- [x] T106 [US1] Validate and version agent output and analysis status in `agents/` and `backend/services/analysis_service.py`.
- [x] T107 [US1] Wire edited values and stale states in `frontend/static/` (originally `frontend/app.py`, replaced by plain HTML/CSS/JS). Prove the three normal form paths with browser checks.

## US2 Account safety

- [x] T108 [US2] Enforce signing-secret validation, claim checks, password migration/reset, and login protections in `backend/core/` and `backend/services/auth_service.py`.
- [x] T109 [US2] Run tenant boundary tests across all protected existing routes. Add forged-token, malformed-token, and legacy-password cases in `tests/`.

## US3 Safe failure and instrumentation

- [x] T110 [US3] Add one logical turn per client request, bound retries, and a safe fallback in `backend/services/chat_service.py`, `backend/controllers/chat_controller.py`, `utils/llm_brain.py`, and `frontend/app.py`.
- [x] T111 [US3] Add metadata-only tracing and offline evaluations under `backend/core/`, `tests/`, and `evals/`. Assert no sensitive data leaves on parent, child, exception, or streaming paths.
- [ ] T112 Run CI, representative migration and restore, browser verification, and Codex review. Attach results before 002 pilot launch.

## Detailed implementation and verification

- [x] **T113** Complete claims/signing, salted-hash migration and lifecycle acceptance cases for the T108 authentication implementation. Location: `backend/core/, tests/auth/`.
  - Done when: Forged/expired/malformed claims, legacy login/reset, enumeration, logout and reset replay all pass.
  - Evidence: pending implementation and independent verification.

- [ ] **T114** Define versioned API/snapshot money and source-precedence contract. Location: `backend/schemas/, tests/contracts/`.
  - Done when: Same snapshot yields same totals in API, UI, chat and export; manual versus ledger conflict is explicit.
  - Evidence: pending implementation and independent verification.

- [x] **T115** Prove financial boundary and migration coverage. Location: `tests/finance/, tests/migrations/`.
  - Done when: NaN/overflow/rounding and corrupted legacy projected values cannot become verified facts.
  - Evidence: pending implementation and independent verification.

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.

Build order and shared task ownership are defined in [implementation order](../implementation-order.md). IDs are stable identifiers, not execution order.
