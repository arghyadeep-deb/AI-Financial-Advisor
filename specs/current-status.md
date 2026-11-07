# Current status (integration branch)

Written 2026-11-08 (overnight run). Supersedes the Stage A-only `implementation-handoff.md` for "where are we".

## Verified results (integration at 4f279cc)
- Full suite on the merged branch: **989 passed, 10 skipped** (about 11.5 minutes).
- GitHub CI (`ci`, `ci-smoke`) green on that commit.
- Browser tests (`tests/web`): 61 passed in the lane N run, including phone/tablet/desktop accessibility checks.

## Caveats
- `tasks.md` checkboxes are **behind reality**: only 24 of 122 are ticked (001: 13, 005: 5, 010: 1, 013: 3, plus 2 partial in 001). Several features have working code and tests recorded in `specs/progress-lane-*.md` but are not ticked, because tick-off waits for independent review or real-data gates.
- The new screens (monthly report, mapped CSV import, manual credit entry, settings data/support cards, demo, dashboard checklist, planning, reminders, household) are covered by automated browser tests. **They have not had a visual review by a person**: the Chrome screenshot tool timed out during the overnight check.
- `Dockerfile`, `docker-compose.pilot.yml`: **untested** (image never built or run).
- Production-like environments refuse the synthetic sandbox, so a production pilot has no statements, monthly report, tax or allocation until the real-data gates (T215, T220) pass.

## Needs the owner (not guessed)
Real bank CSV layouts and sanitised samples; sending domain for mail; visual reference for final styling; tax, allocation and security reviewers; real-data pilot gates; backup retention (D03); key custody; provider and legal choices; the final merge of `integration` into `main`.

## Open items recorded by lane N
Persistent dismissal of reminders; household discovery/gating ambiguity. See `specs/progress-lane-stage-n.md`.
