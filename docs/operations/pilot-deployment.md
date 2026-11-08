# Free-pilot deployment checklist

Status: DRAFT. Tested locally on 2026-11-08 with throwaway values on one machine: the image builds, `docker compose -f docker-compose.pilot.yml up` runs PostgreSQL, a one-shot migrate step (schema 0231) and the app, `/health` and signup work, and production mode refuses to start without a real SECRET_KEY. NOT tested: a real host, TLS reverse proxy, real mail, backups and restore, load, or key rotation.

## What a production-like pilot can and cannot do today

`APP_ENV=production` (or any unknown value) refuses the synthetic sandboxes by design: statement import, monthly reports, tax drafts and the allocation sandbox are **off** until their real-data gates are passed (T215 / T220 in specs/002, owner approval pending). A production-like pilot therefore offers: sign-up and sign-in, profile, health score and what-if, dashboard, manual dated credit score, chat (rules-based unless a model provider is configured and the user consents), settings, data export and account deletion. The sample page works without any data.

## Before anyone outside your team uses it

| Item | Status |
|---|---|
| TLS in front of the app (reverse proxy), exact `CORS_ORIGINS` and `FRONTEND_URL` | owner/ops |
| `SECRET_KEY` 32+ random characters (rotate via `SECRET_KEY_PREVIOUS`) | owner/ops |
| PostgreSQL (SQLite is refused in production) and automated backups | owner/ops; restore drill on real infrastructure NOT done |
| `PRIVATE_STORAGE_ROOT`, `STORAGE_KEYS_JSON`, `STORAGE_ACTIVE_KEY` (uploads and exports are encrypted at rest) | owner/ops; key custody NOT decided |
| `SUPPRESSION_JOURNAL` on a **separate** volume from the database (deleted users must stay deleted after a restore) | owner/ops |
| Mail: leave `MAIL_LIVE_ENABLED=false` until a sending domain is verified; password reset needs working mail | owner (domain) |
| Model providers: optional; with none configured, answers are rule-based and labelled | owner |
| `BILLING_MODE=free_pilot` (the only accepted value) | set |
| Independent security review, load test, incident owner, privacy notice wording | NOT done |
| Backup retention for deleted users (the UI tells users the period is not yet approved) | owner decision D03 |

## Run locally (development)

`uvicorn backend.main:app` then open `http://127.0.0.1:8000/app/`. For the sandboxes set `SYNTHETIC_STATEMENTS_ENABLED=true` in a non-production `APP_ENV`.
