# Lane N — frontend screens

2026-11-08. Worktree only; no staging, commits, pushes, live integrations, real credentials or migrations. Backend unchanged. Tests use the owner's Python and isolated synthetic databases.

## Decisions and contract conflicts

- Use concrete controllers/schemas over older plan examples: planning writes use PUT; preferences use PUT.
- Planning has no feature flag in its service/controller. Respect real 404/503 responses without introducing a separate frontend gate. Goals/debts explicitly labelled experimental previews.
- Notifications exposes GET/PUT preferences and GET notifications, but no dismissal endpoint. Session-only dismiss is the safe frontend fallback; persistent dismissal is PENDING backend owner work. Email stays off in UI writes.
- Household has no list/discovery or feature-capability endpoint. GET networth uses the same 404 for no book and disabled. Show an unavailable/no-inventory notice plus an explicit "Start synthetic personal inventory" action whose existing write endpoint still enforces the gate. A failed initialization leaves a plain unavailable notice and no editing forms. Never infer feature availability from a missing book or enable a backend flag. PENDING backend capability endpoint would allow a fully plain notice before any initialization attempt.
- Household membership grants no access. Keep account grants explicit, permissions separate, declaration UNVERIFIED, and shared inventories separate from personal inventories. No shared asset becomes planning capacity.

## Chunk 1 — T0606 planning screen

Status: partial — assigned list/create/edit slice implemented and tested; full spec T0606 undo/explanation acceptance remains pending below.
Files: `frontend/static/js/views/planning.js`, `frontend/static/js/main.js`, `tests/web/test_ui_planning.py`.
Implemented lists, create/edit forms, reason/revision/idempotency, archived/paused controls, exact paise, declared source/date labels, 409 draft preservation and unavailable/error states.
Tests: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore` — first run 48 passed, 1 failed (test raced logout); after waiting for login before second signup, 49 passed in 135.19s. Diagnostic `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_planning.py -x -q -p no:cacheprovider -W ignore` before fix: 2 passed, 1 failed, same logout race.
PENDING: full T0606 budget undo/explanation acceptance, advanced capacity/scenario and settlement UI (outside assigned CRUD slice); backend delivery acceptance remains with shared notification owner.
Recovery: remove frontend route/modules to withdraw UI; immutable backend revisions retained; no schema changes.

## Chunk 2 — T1005 preferences/reminders

Status: partial (frontend verified, persistent dismissal/digest deferred). Files: `frontend/static/js/views/notifications.js`, `frontend/static/js/main.js`, `tests/web/test_ui_notifications.py`.
Uses shared preferences/notifications endpoints; category opt-outs, master switch, quiet hours, in-app notices, session-only dismiss. Handles unavailable/409/offline/401 through shared API. Tests: same exact full web command above — 51 passed, 1 failed in 144.78s (test expected specific quiet-hours validation but shared API returns generic invalid-fields copy). Added local paired/different-boundary validation to give the user the specific fix. Diagnostic `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_notifications.py tests/web/test_ui_household.py -q -x -p no:cacheprovider -W ignore` — 1 passed, 1 failed, same error copy; household tests not reached. Full web rerun after fix and household implementation: **55 passed in 149.99s**.
PENDING: persistent dismissal unavailable in current API; digest/channel delivery remains deferred/shared backend ownership. No new store; withdrawal via removing route/module preserves all backend data.

## Chunk 3 — T1105 household/net worth

Status: partial — assigned synthetic household/net-worth screen implemented and tested; capability/discovery limitation and broader FR05 work remain pending below. Files: `frontend/static/js/views/household.js`, `frontend/static/js/main.js`, `tests/web/test_ui_household.py`.
Create, invite/accept, UNVERIFIED adult confirmation, separate read permissions on each reference, grant/revoke, precise percentage entry, append-only personal observations/editing, and fresh shared snapshots. Every observation displays date/source/share, full/owned/unallocated amounts; totals describe included observations' dates/shares and unknown totals remain unknown. Personal inventory and household consolidated sections are distinct. Shared inventory never becomes capacity. No backend changes.
Tests: same exact full web command above after chunk 3 — **55 passed in 149.99s**. Targeted `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_household.py tests/web/test_ui_accessibility.py -x -q -p no:cacheprovider -W ignore` — **24 passed in 80.94s**, including expanded new forms at all three widths.
Limitations/PENDING: no household discovery, no general capability read; enter owner-supplied IDs/revisions, shared views refresh explicitly; persistent invitation recovery/listing requires backend support. Protection-policy/nominee checklist editing is outside this lane's assigned screen subset, so broader spec T1105/FR05 remains partial. Export/document/transaction viewers not added; permissions remain separately configurable and server enforced. Revoke via unchecking grant enabled; no membership-delete UI. Recovery: withdraw route/module; preserve backend revisions and grants. No tables/migrations.

## Chunk 4 — T1004 accessibility/responsive acceptance

Status: done for assigned responsive/accessibility smoke (not full WCAG certification). Files: `frontend/static/css/app.css`, `tests/web/test_ui_accessibility.py`; all three routes added to SIGNED_IN, PUBLIC unchanged (all new routes require auth). Expanded-form/long-reference smoke at 360/768/1440 passed in the targeted 24-test run above. Added scoped `finance-evidence` wrapping for exact fractions, invitation tokens and long holding references; field min-width avoids grid overflow; scoped [hidden] display rule prevents the button theme from exposing hidden pagination controls. Existing theme variables unchanged. No emptyState added, so no heading-level exception needed. No migrations/recovery changes.

Final review fixes: successful planning/observation saves replace only the saved editor and summary, preserving other unsaved drafts; retained observation editors keep their original revision so stale submissions conflict. Planning lists offer API offset pagination and deduplicate IDs while retaining drafts. Exact lost-response retries reuse operation keys. Blank amounts/revisions remain unknown/invalid rather than becoming zero. HTTP 404/503 gets unavailable/missing/permission-safe text.

Additional verification:
- `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore` — **60 passed in 168.40s** after expanded acceptance/CRUD tests.
- `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_planning.py tests/web/test_ui_household.py -x -q -p no:cacheprovider -W ignore` — **9 passed in 25.75s** after cross-form draft preservation changes; includes real backend commit followed by a deliberately lost response and idempotent retry (one obligation only).
- `git diff --check` initially found one extra EOF blank line in `main.js`; removed it. Static search of new modules found no innerHTML/outerHTML/insertAdjacentHTML, inline style/script or on-attribute insertion.
- Final chunk-4 command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore` — **61 passed in 176.21s**.
- `git diff --check` — passed after removing the extra blank line.
- Full repository command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore` — **989 passed, 10 skipped in 733.36s (12:13)**. Skipped checks are not counted as passes. All 61 browser tests also passed in this full run.
- Full tests updated only `code_revision` in generated `evals/results/latest.json`. The worktree was initially clean; verified the one-field generated diff and restored its original tracked content after the run. No other non-lane files changed.

Final state: frontend implementation and assigned browser smoke verified, with the explicit PENDING feature limitations above. Backend, migration history and existing data unchanged. No staging, commits or remote actions. These tests use browser automation, not an independent usability study or formal WCAG audit.
