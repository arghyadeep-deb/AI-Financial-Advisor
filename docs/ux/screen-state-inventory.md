# Screen and state inventory (T1001)

Source of truth for what each screen shows and how it fails. A screen is only listed as enabled if the feature is on by default in the free pilot. Anything behind a sandbox flag appears only when its backend flag is on and otherwise shows the "not available yet" notice. Updated 2026-11-08 against `frontend/static/js/main.js`.

Common states for every signed-in screen: **loading** (page renders after its first request), **session ended** (401 -> back to log in with a message), **offline / server error** (red banner with the server text or "Cannot reach the server"), **nothing yet** (an empty-state illustration with the next step), **feature unavailable** (blue notice; other tools keep working).

| Route | Purpose | Enabled by default | Specific states |
|---|---|---|---|
| `#/` landing | Explain the product | yes | signed-out only |
| `#/login`, `#/signup` | Authentication | yes | wrong credentials (generic message), throttled (429 wait message), weak password, MFA code step when MFA is on |
| `#/dashboard` | Summary of the last analysis | yes | no profile yet (go to profile), no analysis yet, **stale** (profile changed since), **degraded** (AI unavailable: fixed-rule numbers only), nothing to invest (deficit: no plan, projection or card) |
| `#/profile` | Income, expenses, debts, goals | yes | unknown stays unknown (empty field -> unknown, never 0), revision conflict (409: reload, input kept) |
| `#/health` | Health score and what-if | yes | not enough information, what-if banner (saved profile unchanged), stale |
| `#/portfolio`, `#/stocks` | Holdings and market view | yes (labelled educational) | no named products for personal recommendations, stale prices labelled |
| `#/credit` | Credit score entry and card matches | yes | no score on record (never guessed), score current / **stale (over 90 days)** / unknown, bureau lookup "not available yet", no card matches when nothing is spare |
| `#/reports` | Older analysis reports | yes | none yet |
| `#/statements` | Add account, upload, CSV column mapping, review | needs synthetic-statement gate (pilot sandbox) | unavailable notice, waiting to be read, **needs review**, balance mismatch (cannot import), balances unverified (acknowledge), unsupported scanned/PDF/photo message, preview problems listed by line, possible duplicates warned |
| `#/monthly` | Monthly report from confirmed entries | same gate | no accounts, no report yet, **stale** (accounts changed), coverage gaps warned, spending above money in (no investable amount suggested), comparison unavailable, net worth unavailable |
| `#/chat` | Ask the advisor | yes | streaming interrupted (retry), model unavailable (fixed-rule answer), thread switch while streaming blocked |
| `#/settings` | Sessions, password, consent, preferences, export/delete | yes | consent off -> model not used, other sessions revoked, export / deletion receipt |
| Planning, reminders, household | Budgets/goals/debt, in-app reminders, household and net worth | built in lane N | each shows the unavailable notice when its backend flag is off |

## Hidden or deferred (not in navigation)

Tax drafting and allocation sandboxes (flags default off; refused in production-like environments), live bank or bureau integrations (no provider), paid billing (deferred), OCR (deferred), email delivery (off), Hindi/Hinglish (not released).

## Failure handling rules

1. Never show a number the server did not provide; unknown renders as "unknown".
2. A stale or degraded result always carries a banner saying why.
3. A conflict (409) keeps what the user typed and asks them to reload; nothing is overwritten silently.
4. Text from users, files or models is shown as plain text only.
