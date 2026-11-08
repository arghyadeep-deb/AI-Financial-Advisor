# Lane O — remaining frontend gaps

2026-11-08. Working tree only; no staging, commits, push, external services, database changes or migrations. Backend unchanged. Synthetic isolated tests only.

## Decisions
- Concrete controllers/schemas override older plan route examples. Reuse shared API/DOM/money helpers.
- Budget actuals exist only in frozen monthly reports. Explanation takes an owned report ID, checks budget identity and labels its revision, scope and stale state. Never synthesizes current actuals.
- Undo reads revision N-1 and saves its data with expected revision N and a user reason. No history deletion.
- Portfolio API has aggregate valuations and raw position observations, but no per-position computed market-value/status fields or concentration warning threshold. Display the returned coverage/missing-price IDs and concentration scope/formula; do not invent prices, values or risk thresholds.
- Protection GET 404 conflates disabled and absent inventory, as net worth does. Use an explicit synthetic initialization action subject to the real server gate; failed initialization leaves an unavailable notice. No separate capability implementation.

## Chunk 1 — T0606 remainder
Status: partial; implementation and browser test added, full web command running.
Files: frontend/static/js/views/planning.js, tests/web/test_ui_planning.py.
Command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore`.
Result: pending completion. No unrun work counted done.
Recovery: withdraw frontend controls; all immutable revisions and reports retained. No migrations.

## PENDING
- Chunk 2 T303/T305 portfolio cards and tests.
- Chunk 3 T1104/T1105 protection editor and tests.
- Chunk 4 responsive/accessibility acceptance, final full repository suite.
- Existing lane N broader feature limitations remain with their owners; no launch approval, live quotes, named picks, public advice, email or external reminders.

## Chunk 1 verification update
The initial full web command finished: **62 passed, 3 failed in 188.31s**. Failures: new fixture used nonexistent `account_token` constructor field (corrected to `token` plus explicit ID); new portfolio read's expected absent-inventory 404 was counted as unexpected by tracker in two accessibility widths (narrow tracker exception added, as for missing profile). Files were edited while that run was active, so it is diagnostic only; a fresh full web run is in progress.
Targeted command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_planning.py -k undo -q -p no:cacheprovider -W ignore` — **1 passed, 6 deselected in 7.20s**. Undo/restoration, three real immutable revisions, exact overspend, and two-user resource/report isolation passed.

## Chunk 2 — T303/T305 frontend slice
Status: partial pending full web result; cards and tests implemented in frontend/static/js/views/portfolio.js, tests/web/test_ui_portfolio.py; tracker expected 404 handling in tests/web/test_ui.py.
Full web command repeated as above; running. Existing planner behavior preserved. New observations display API aggregate status/dated values, quote source/date/version/expiry, currency, missing quote state, concentrations/exposures and exact API formula/scope/performance explanation. Public advice/named picks remain disabled.
Limitation/PENDING: API supplies no individual computed position market value/status and no concentration warning threshold/text. No frontend engine or invented warning rating added; quote availability follows the API's missing-price IDs. T303/T305 whole-feature completion remains partial for backend/real-data limitations already recorded by lane E.
Recovery: withdraw new observed card; stored holdings unchanged; no migrations.

## Chunk 2 verification update
Full web repeat: **68 passed, 1 failed in 192.40s**. Failure was an ambiguous test locator: Playwright substring matching found both aggregate valuation status and the drill-down's portfolio status. Scoped to the first aggregate status; no financial code changed.
Targeted command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_portfolio.py -q -p no:cacheprovider -W ignore` — **3 passed, 1 failed in 11.54s**, same locator (before fix). Fresh full web now running.

## Chunk 3 — T1104/T1105 protection frontend slice
Status: partial pending full web result. Files: frontend/static/js/views/protection.js, frontend/static/js/main.js, tests/web/test_ui_household.py, tests/web/test_ui.py.
Uses existing GET/POST /policies, optimistic revisions/reason/idempotency, personal policy inventory, all evidenced policy fact fields, nominee/emergency-location checklists, opt-in in-app renewal reminder, archive and shared preference link. Unknown stays unknown. Failed validation preserves draft; unsaved other forms keep original revision for conflict safety. No backend edits.
Targeted command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web/test_ui_household.py -k policy -q -p no:cacheprovider -W ignore` — **1 passed, 5 deselected in 6.98s**. Real evidence rejection, exact amount, unknown facts, flags, immutable revision read, no reminder before opt-in / one after, second-user isolation passed.
Full web repeated after this chunk, result running.
Limitations: API does not return recorded date for protection, so recorded date explicitly unknown; renewal dates show entered evidence. No document extraction, adequacy/legal advice, identity collection, automatic succession/access, email, installed scheduler or external delivery. Feature-wide T1104/T1105 remains partial for existing backend/operational/shared-view limitations. Recovery: withdraw route/module; stored immutable policy history and backend reminder preference checks remain; no migrations.

## Chunk 4 — accessibility acceptance
Status: partial pending tests. New signed-in route `protection` added to SIGNED_IN; PUBLIC unchanged. Existing portfolio/planning routes already listed. Expanded forms now cover protection and portfolio at 360/768/1440, seeded with synthetic policy/holdings. Shared tracker only exempts expected absent personal inventory GET 404s; 503/error tests assert notices directly.
Static inspection found no innerHTML/outerHTML/insertAdjacentHTML or inline styles in new controls. `git diff --check` passed (line-ending warnings only). New full web command running; full repository suite still PENDING.

## Verified frontend results (supersedes running/PENDING implementation statuses above)
Full web command after protection and accessibility changes: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests/web -q -p no:cacheprovider -W ignore` — **72 passed in 207.58s**. Includes all new planning, portfolio, policy, 404/503 and responsive cases. No skipped browser tests.
- T0606 assigned undo/explain remainder: **done**, including exact ₹500 overspend and new-revision undo plus two-user isolation. Broader reminder delivery/operational acceptance stays with shared backend owner.
- T303/T305: **partial**. API-backed portfolio presentation is implemented and browser-tested, but the API limitations recorded above remain PENDING. No computed per-position value or invented risk threshold.
- T1104/T1105 assigned protection editing/checklist remainder: **done for exposed synthetic/manual contract**, feature-wide **partial** for document extraction/installed scheduling/shared views and production gates owned elsewhere.
- Route/accessibility smoke: **done** at 360/768/1440 for the added protection route and expanded existing screens. No formal WCAG certification or independent usability study claimed.
Full repository command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore` — running; result PENDING. No further implementation planned unless regression evidence requires a correction.

Final review: implementation is frontend-only. No backend defect was found/proved or changed. No schema/migration/recovery work is required. No external integrations enabled. All work remains unstaged/uncommitted per the common addendum; orchestrator owns commits and merged-branch verification.

## Final regression and handoff
- Full repository command: `& 'C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe' -m pytest tests -q -p no:cacheprovider -W ignore` — **1007 passed, 10 skipped in 808.71s (13:28)**. Includes all 72 browser tests. Skips are not passes; no live-provider or production acceptance is claimed.
- Standalone full browser command above — **72 passed in 207.58s**. This verifies the final implementation; no code changes followed it.
- The full suite generated only a `code_revision` change in `evals/results/latest.json`. Compared every JSON field against the initially clean tracked baseline and restored that revision-only generated artifact. No user changes discarded.
- Final file inventory: `frontend/static/js/views/planning.js`, `frontend/static/js/views/portfolio.js`, new `frontend/static/js/views/protection.js`, `frontend/static/js/main.js`; `tests/web/test_ui.py`, `tests/web/test_ui_planning.py`, new `tests/web/test_ui_portfolio.py`, `tests/web/test_ui_household.py`, `tests/web/test_ui_accessibility.py`; this lane file only.
- No backend changes, tables, Alembic revisions, owned-store registrations, new services, new dependencies or external actions. No staging/commits/push. Recovery is withdrawal of the new UI controls/route; preserve stored revisions and backend preference/gate enforcement.

## Final statuses and exactly what remains PENDING
- **T0606 assigned undo/explain remainder: done.** Edit then undo restores prior values in a new immutable revision; exact API overspend and frozen report revision/scope/staleness shown; two-user isolation tested. Broader feature T0606 delivery/operations remains partial under its existing owner; no reminder sender added here.
- **T303/T305: partial.** Observed holdings/quote drill-down, aggregate current/partial/unavailable state, source dates/versions, currency, coverage and API concentration explanations are implemented and tested. **PENDING:** backend exposes no computed per-position market value/status or concentration warning threshold/text. No second valuation engine or invented threshold added. API formula and priced-subset/no-low-risk warning are shown. Independent data validation/licensing, returns and public-advice release remain outside this frontend lane.
- **T1104/T1105 assigned protection editing/checklist remainder: done.** Manual evidenced policy facts, unknowns, checklist completion, archive, immutable edits, opt-in in-app reminders and owner isolation tested. Feature-wide status remains partial under existing lane J/N limits. **PENDING:** general feature-capability/discovery API (GET 404 still conflates absent/disabled), document extraction, policy recorded timestamp not returned by API, installed scheduling/operational acceptance, and shared policy viewers. Backend owner work; safely displayed unknown/unavailable here.
- **Task 4 route/responsive/accessibility smoke: done.** New route `protection` is SIGNED_IN; no new public route. Expanded portfolio/protection forms and all routes passed at 360/768/1440. Formal WCAG certification and independent usability study remain outside the smoke test scope.
- **Disabled throughout:** live quotes/providers, named stock/fund picks, public personalized advice, trading, billing, filing, email/push reminders, automatic legal succession/access transfer. No launch gates or broader tasks are ticked complete.
