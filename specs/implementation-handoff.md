# Review handoff — Stage A (Foundation, feature 001)

For: Codex / reviewer. Date: 2026-11-05. Base: `818b219`, **uncommitted working tree** (no commits, no pushes made).
Status per task: `specs/implementation-progress.md`.

## 1. Tasks
- Completed (tested): T101, T103, T102, T104, T105, T106, T107, T108, T109, T110, T111, T113, T115.
- Partial: T114 (no export surface yet), T112 (CI never run; Codex review not run).
- Pending: everything in features 002–014.

## 2. Files and resulting behaviour
**Money and finance rules** — `backend/core/money.py` (paise, Decimal parsing, `MAX_PAISE=10^13`, Indian grouping);
`engines/cashflow.py` (`cashflow.v1` snapshot: surplus/shortfall, reserve top-up capped at cash left, contribution =
floor(0.9·max(0,capacity)), unavailable if a debt balance has no declared payment); `engines/precedence.py`;
`engines/financial_health_engine.py` (unknown credit excluded and flagged partial, signed shortfall);
`engines/investment_engine.py` (SIP hard-capped at the affordable contribution).

**Persistence** — `backend/models/models.py` (paise columns, `revision`, `ProfileRevision`, `Analysis`, `AuthSession`,
`PasswordResetToken`, `LoginThrottle`, `Message.client_message_id` unique with thread+role); `migrations/` (Alembic 0001
legacy baseline, 0002 foundation); `backend/core/database.py`, `migrations_runner.py` (backup, counts, stamp, upgrade,
downgrade CLI). Legacy float columns are dual-written from paise for rollback.

**Services/API** — `profile_service` (CAS revisions, 409), `analysis_service` (owner/kind/status/revision/rule version,
scenario isolation, superseded runs, per-section latest), `output_guard` (runs after agents; overwrites model numbers),
`auth_service` + `backend/core/auth.py`/`throttle.py`/`config.py`/`dependencies.py`, `chat_service`,
`backend/core/errors.py` (structured errors + `X-Request-ID`), `backend/core/telemetry.py`.
Controllers return 404 (not 403) for foreign resources. `/analysis/last` now also returns the run `snapshot`.
Removed: `utils/auth.py` (unused, contained a default secret) and `backend/controllers/main.py` (unreferenced duplicate
app with wildcard CORS).

**Agents / LLM** — agents consume the snapshot; `utils/llm_brain.py` has timeouts, bounded attempts, no synthesised advice
text, failover only before the first streamed chunk; tracing env block removed.

**Frontend** — `frontend/app.py`: forms send edited values as `scenario`; unknown-credit checkbox; debt-payment field;
`expected_revision`; status/stale/what-if labels; chat sends `client_message_id`; named stock picks page explains they are off.

**Tooling** — pinned requirements, `requirements-dev.txt`, `.env.example`, README, `.github/workflows/ci.yml`; dependencies upgraded to clear `pip-audit` findings (PyJWT 2.15.1, starlette 1.10.0, streamlit 1.66.1, pillow 13, langchain 1.4.9, anthropic 2.5.0 …).

## 3. Requirement → evidence
Command (Windows, repo venv): `.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider --timeout=180`
Last run: **167 passed, 8 skipped** (155 backend + 12 browser tests in `tests/web`; the 10 Streamlit AppTest tests were removed) (6 skipped = public routes in the route-auth parametrisation, 2 = PostgreSQL opt-in).

| Requirement | Evidence |
|---|---|
| FIN-01 deficit consistent everywhere | `tests/finance/test_analysis_api.py::test_FIN01_*`, `test_cashflow_and_money.py::test_FIN01_*` |
| FIN-14 flow capacity 3,000 | `test_FIN14_flow_capacity_counts_each_commitment_once` |
| Stale report after profile edit | `test_income_edit_makes_old_result_stale_*`, `test_in_flight_analysis_*` |
| Ignored inputs / scenarios | `test_scenario_uses_submitted_values_*`; `tests/frontend/test_forms.py` (3 forms) |
| Unknown credit never defaulted | `test_unknown_credit_score_is_excluded_not_defaulted`, `test_forms.py` |
| Portfolio not overwritten by projection | `test_health_only_run_preserves_*`, `tests/contracts/` |
| Provider failure not shown as success | `test_total_provider_outage_*`, `test_model_cannot_publish_a_surplus_*`, `tests/api/test_chat.py` |
| Exact money / NaN / overflow | `test_cashflow_and_money.py`, `test_invalid_money_*`, `test_nan_and_infinity_*` |
| Auth, tenancy | `tests/auth/` (25), `tests/api/test_tenancy.py` (every route, two-user checks) |
| Chat idempotency | `tests/api/test_chat.py` |
| Telemetry metadata only | `tests/api/test_telemetry.py` |
| Migration (clean, legacy, corrupt values, downgrade) | `tests/migrations/test_migrations.py` |
| Baseline defects reproduced on `818b219` | `tests/baseline/` (see §6) |

Other commands run: AST/syntax check of `frontend/app.py`; local secret grep over tracked + intent-to-add files (no matches);
migration, downgrade and restore on a **copy** of the local `advisor.db`.
Also run: `pip-audit` (clean after dependency upgrades), real-browser pass (see below), `evals/` (20/20 after guard fixes).
PostgreSQL 16 in Docker (2026-11-07): `TEST_POSTGRES_URL=postgresql+psycopg://…:55432/advisor_test pytest tests/migrations/test_postgres.py` → 2 passed (incl. the concurrent revision race). The rest of the suite is SQLite-only.
**Not run:** CI itself, Codex review, legacy-DB migration on PostgreSQL, any live LLM provider.

**Browser pass (Chrome, local API + Streamlit, throwaway SQLite DB, model keys blank):** signup; profile save with unknown credit score; full analysis showed the degraded banner, ₹0 SIP and a Rs 10,000 gap action; Health form with income 120,000 showed what-if and degraded banners, score 37→59, and the DB confirmed a scenario run with income 12,000,000 paise while the saved profile stayed revision 1 / 4,500,000 paise / credit NULL; chat returned the degraded deterministic reply. Defect found and fixed: Health page crashed on a `None` component score (regression test added).

### Codex review round 2 (2026-11-07) - all fixed, tests in `tests/api/test_codex_review_regressions.py`, `tests/frontend/test_forms.py`
1. Simulation now uses the canonical contribution (zero/unavailable preserved). 2. NULL migrated debt/savings raises 422 `profile_incomplete` (`needs_reentry` covers all money fields). 3. Profile editor opens with null values. 4. `_update_state` is one guarded UPDATE conditional on the current revision. 5. Owner-wide partial unique index on first messages (migration `0003_first_message_idempotency`, head is now 0003; downgrade drops it). 6. Explicit `credit_score: null` in a scenario means unknown. 7. Parser fallbacks set `parse_error`, so the section is `degraded`. A duplicate of a turn still in flight (younger than `IN_FLIGHT_SECONDS`=30) now waits for and replays the original reply instead of calling the model again; an older unanswered turn is retried. The dashboard hides the allocation, projection and card pitch when nothing is investable (tested in `tests/frontend/test_forms.py`).

### Codex review round 1 (2026-11-07, `codex review --uncommitted`, via the Codex bridge)
Round 1 returned 7 findings, all confirmed and fixed, each with a regression test (`tests/api/test_codex_review_regressions.py`, `tests/frontend/test_forms.py`). Red-before-fix was not separately demonstrated; the tests pass after the fix.
- P1 Portfolio/Reports crashed on `total_tax_saved_annually: None` → renderer null-safe (also the summary tab).
- P2 What-if results were written into the saved-analysis caches and leaked onto Dashboard/Reports → separate `scenario` state, banner on its own page, discarded on navigation.
- P2 A late superseded run displaced current-revision sections in `/analysis/last` and chat → current revision sorted first.
- P2 First-message retry without `thread_id` created a second thread and a second model call → idempotency looked up by owner + `client_message_id` before thread creation.
- P2 Standalone `summary` runs overwrote health/SIP figures with defaults → dependency results now returned with the summary and passed to the guard.
- P2 `LLM_MAX_ATTEMPTS` was global, so Groq retries starved Gemini failover → per-provider attempt budget.
- P2 An HTTP-200 stream with no reply skipped the fallback → stream counts as successful only with a completed, non-empty reply.

## 4. Migration and recovery
- Fresh DB: starts with `AUTO_MIGRATE=true`, or `python -m backend.core.migrations_runner upgrade`.
- Existing SQLite (`advisor.db`): `python -m backend.core.migrations_runner dry-run` shows counts; `upgrade` copies the
  file to `backups/` first, stamps 0001, upgrades. Verified on a copy: 8 users / 8 profiles / 30 messages before and after;
  4 legacy default credit scores (700) became "unknown"; 0 monetary values were unreadable.
- Rollback: stop the app, `python -m backend.core.migrations_runner downgrade 0001` (restores the projected value that
  0002 moved aside), or restore the `backups/*.db` copy. Both were exercised on the copy.
- PostgreSQL: the runner refuses to touch a legacy unversioned PostgreSQL DB without `--i-have-a-backup` (take `pg_dump` first).
- Existing users: legacy password hashes still verify once and are re-hashed to Argon2id. If `LEGACY_PASSWORD_SECRET` is
  unset they cannot log in and must use password reset (reset tokens are not delivered anywhere yet).
- Production-like envs (`APP_ENV` anything but development/test) refuse to start with a weak `SECRET_KEY`, `*` CORS, or SQLite.

## 5. Decisions and deviations (please review)
1. API keeps legacy float fields as deprecated mirrors; `*_paise` is authoritative (architecture says "no floats" — kept for
   frontend/rollback compatibility).
2. Signup returns 409 for a duplicate email (enumeration-proofing needs email verification, which needs a mail provider).
3. Health score with unknown credit score is normalised over the 90 available points and marked `partial`.
4. A legacy credit score of exactly 700 is treated as the old default and cleared to unknown.
5. A user with a debt balance but no payment gets contribution `unavailable` until they enter the payment.
6. Chat checks only semantic contradictions (surplus during deficit, etc.), not the general unsupported-amount check.
7. Login throttle is per email: an attacker can lock a victim out (residual DoS); per-IP limiting needs proxy config.
8. Output guard (this round): summaries naming specific products, claiming investable surplus with no affordable contribution, or quoting a SIP above the affordable amount are now rejected; the allowed-amount set no longer includes simulation figures or halves. Known limit: amounts are matched to the allowed set, not to their meaning (e.g. quoting income as surplus within Rs 1 of a real figure).
9. `mcp_tools/` is not imported anywhere and was not touched.

## 6. Baseline note
B2 (default-secret forgery) and B8 (ignored form values) passed trivially against `818b219` in my harness: B2 because
`.env` supplied a key, B8 because it only checked the API. B8's real defect (UI ignoring edits) is now covered by
`tests/frontend/test_forms.py`.

## 7. Unresolved decisions for the product owner
- **Named stocks/funds** are off (`NAMED_PRODUCT_RECOMMENDATIONS=false`) pending compliance review — release-gates D05 reading.
  Confirm, or provide the approved wording/eligibility.
- **Credit-card recommendations** still name specific cards; decide whether they fall under the same gate.
- Is a 10% unallocated buffer and 12-month reserve top-up the intended `cashflow.v1` policy (taken from `financial-rules.md`)?
- Mail provider for password reset (none exists).

## 8. Disabled / not built
Named product recommendations; LangSmith export; all external integrations; billing; tax filing; trades; document upload;
ledger/statement ingestion (002). The rebalance agent reports `unavailable` because no holdings breakdown exists.

## 9. Next
Before Stage B: (a) optional: run the whole suite against PostgreSQL (the fixtures are SQLite today), (b) Codex review of this diff (owner to trigger), (c) first CI run, (d) commit/push when the owner approves, (e) browser-check the Portfolio and Credit forms. Then Stage B (feature 002
monthly finance) per `implementation-order.md`.


## Frontend replacement (2026-11-07, branch `frontend-html`)
Streamlit (`frontend/app.py`, `frontend/requirements.txt`, `tests/frontend/`) was replaced by plain HTML/CSS/JS in `frontend/static/` (ES modules, no build step), served by FastAPI at `/app/` with a scoped CSP (`script-src 'self'; style-src 'self'; frame-ancestors 'none'`), no inline script/style, no external fonts. Earlier sections of this file that mention Streamlit describe the previous UI and are kept as history.
- Token is held in module memory only (reload = log in again); logout revokes the session server-side. All user/model text is rendered with `textContent`.
- All Stage A UI rules were carried over: exact money strings, unknown credit score as explicit `null`, what-if kept apart from saved results, nothing-to-invest hides plan/projection/card, stale/degraded labels, `expected_revision` conflict message, chat `client_message_id` retry.
- Tests: `tests/web/test_ui.py` (Playwright + live uvicorn on a temp DB, providers off): signup→profile→analysis, deficit dashboard, unknown credit what-if, logout revocation and memory-only token, revoked session redirect, profile 409, XSS payload rendered as text, fragmented SSE frames, CSP headers, no inline style/script. Command: `.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider --timeout=300 -W ignore` -> 167 passed, 8 skipped. Real-browser (Chrome) pass: signup, profile, full analysis, what-if with unknown credit, chat fallback, all ten routes render without console errors. One bug found there and fixed: donut/line charts were filled blobs (CSS fill overrode `fill="none"`).
- Open: Claude Design canvas (https://claude.ai/artifact/1gJ7WD5vj8nwLuhUe248Ji) holds no screens yet (publish was blocked by a permission rule); the UI was designed directly in CSS. Password-reset has no mail provider. Mobile layout was not browser-tested at phone width.

## Orchestration update (2026-11-07, integration branch)

Branches (local only, nothing pushed): `frontend-html`; `codex/stage-b`; `codex/modules`; `codex/stage-c` (commit e9f6e40);
`integration` = all of the above merged (single Alembic head 0101); `codex/stage-d` running (migrations 0110+).

Verified on `integration`: `pytest tests -q` -> 310 passed, 8 skipped (after the Stage C merge, before the Statements UI);
`pytest tests/web -q` -> 15 passed (includes Settings page and Statements upload -> worker -> review -> confirm).

Frontend added on integration: Settings (sessions, password change, consents, notification preferences, notices) and
Statements (accounts, upload, review, confirm, cancel). Statements shows "not available yet" while
`SYNTHETIC_STATEMENTS_ENABLED` is false (default; refused in production-like environments).
Not in the UI on purpose: export/delete (not enabled by the backend), PDF reports, budgets.

Still open for the owner: accept Stage A; review/merge branches (order: frontend-html, then integration); push so CI can run (T112);
mail provider for password reset; provider/legal choices for 005, 011, 013, 014; T215/T220/G2 remain unapproved.
