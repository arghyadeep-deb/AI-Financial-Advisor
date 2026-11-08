# Current status (integration branch)

Written 2026-11-08 (overnight run). Supersedes the Stage A-only `implementation-handoff.md` for "where are we".

## Verified results (integration at 77356a5)
- Full suite on the merged branch: **1008 passed, 10 skipped** (about 12 minutes).
- GitHub CI: `ci-smoke` green on 77356a5; the `ci` run was in progress when this was written (check `gh run list`). One earlier red run was caused by a wording change that broke an older UI test, fixed in the same push.
- Browser tests (`tests/web`): 65 passed on the merged branch, including phone/tablet/desktop accessibility checks.

## Caveats
- `tasks.md` checkboxes are **behind reality**: 51 of 122 are ticked after the 2026-11-08 audit below. Several features have working code and tests recorded in `specs/progress-lane-*.md` but are not ticked, because tick-off waits for independent review or real-data gates.
- The new screens (monthly report, mapped CSV import, manual credit entry, settings data/support cards, demo, dashboard checklist, planning, reminders, household) are covered by automated browser tests. **They have not had a visual review by a person**: the Chrome screenshot tool timed out during the overnight check.
- `Dockerfile`, `docker-compose.pilot.yml`: **tested locally** (builds, runs with PostgreSQL, migrations, health, signup; a missing migrate step was found and fixed). Not tested on a real host, behind TLS, with real mail, backups or load.
- Production-like environments refuse the synthetic sandbox, so a production pilot has no statements, monthly report, tax or allocation until the real-data gates (T215, T220) pass.

## Needs the owner (not guessed)
Real bank CSV layouts and sanitised samples; sending domain for mail; visual reference for final styling; tax, allocation and security reviewers; real-data pilot gates; backup retention (D03); key custody; provider and legal choices; the final merge of `integration` into `main`.

## Open items recorded by lane N
Persistent dismissal of reminders; household discovery/gating ambiguity. See `specs/progress-lane-stage-n.md`.

## Task audit, 2026-11-08
Method: for each task a lane called "done", I read the task's "Done when" text and the tests behind it, then relied on the full-suite pass (989 passed, 10 skipped) and green CI. Mutation spot check: breaking the budget overspend calculation made `test_budget_500_overspend...` fail, and restoring it made it pass, so that test is not vacuous. Tasks were ticked only when no owner decision or real data is needed to meet the wording. Scope notes ("selected synthetic scope") are in the lane progress files.

**Ticked in this audit (21):** T112 (CI green incl. Postgres service, real-browser pass, migration/restore on a copy, Codex review rounds), T202, T204, T210, T301, T302, T304, T307, T402, T0601-T0605, T0701-T0704, T1101, T1103, T1403.
**Ticked before (22):** 001 (13 tasks), 005 (5), 013 (3), 010 T1002 (1).

**Left unticked although code exists (partial):**
- 002: T203, T205, T206, T207, T209, T211, T212, T213, T214, T216-T219. Synthetic layout only, so no real bank parser or real-data check.
- 003: T303, T305, T306, T308, T309, T310 (UI or acceptance parts missing).
- 004: T401, T403-T409 (tax scope pack is a historical, reviewer-pending slice, so release is pending).
- 006: T0606, T0607. 007: T0705-T0707 (public advice gate closed by design).
- 008 and 009: all of T0801-T0807, T0901-T0907 (no load run, no restore evidence at scale, key custody and retention decisions are the owner's).
- 010: T1001, T1003, T1004 (no screen-reader test), T1005, T1006. 011: T1102, T1104, T1105, T1106. 012: T1201-T1206. 014: T1401, T1402, T1406.
- 001: T114 (no profile-snapshot export compared yet).

**Not started or blocked on the owner:** 002 T201 (needs a confirmed pilot bank layout), T208 (restart check), T215, T220 (real-data gates); 014 T1404, T1405 (second adapter, OCR deferred); 010 T1006 (real usability results).

## Later ticks, 2026-11-08
T208, T1003, T1005, T1401 (own tests added; mutation checks on the conflict and channel tests), then T0606, T1104, T1105 (lane N and O screens plus backend tests) and T1406 (drift quarantine, rollback, restart and unchanged-snapshot tests, synthetic adapter only). Total ticked: 51 of 122.
Still partial on purpose: T303/T305 (API gives no per-position value or concentration threshold, so nothing honest to show), T0607 (needs an independent held-out evaluation), T1203, T1402.
