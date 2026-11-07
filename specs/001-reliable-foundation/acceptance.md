# Acceptance and requirement traceability

**Planned tests, not executed results.** Use independent expected values and the actual API/browser/service entry points. Every row additionally requires ownership, invalid-input, source-revision and retry checks where applicable; document justified N/A.

| Requirement | Task(s) | Acceptance scenario |
|---|---|---|
| FR-001 | T102, T104, T105 | Deficit 45,000/55,000 agrees in dashboard/chat/export; unknown inputs stay unknown. |
| FR-002 | T104, T106, T107, T114 | Income edit during running analysis makes old revision stale; latest-by-purpose is correct. |
| FR-003 | T107 | Each of the three forms sends edited values; scenario does not overwrite profile. |
| FR-004 | T105, T106 | Health-only request preserves holdings; projected balance never appears as observed. |
| FR-005 | T105, T106 | Missing score remains unknown; guessed tax savings absent; debt balance differs from payment. |
| FR-006 | T108, T109, T113 | Two users, forged/expired tokens and legacy password migration/reset exercise actual endpoints. |
| FR-007 | T106, T110 | One logical turn on retry; malformed model and total provider outage retain safe facts. |
| FR-008 | T101, T103, T111, T112 | Fresh and legacy PostgreSQL migration plus backup restore and privacy trace capture. |
| F001-FR09 | T108, T113 | Logout/reset revoke applicable sessions; replayed recovery token and login abuse rejected. |
| F001-FR10 | T104, T114 | Profile versus ledger conflict is labeled, not silently summed; source snapshot stable. |
| F001-FR11 | T104, T115 | Paise round trip through DB/API/CSV/PDF; NaN, overflow and inconsistent rounding rejected. |
| F001-FR12 | T101, T103, T108, T112, T115 | Missing/default key refuses production; rotation preserves intended access and revokes old credentials. |

## Handoff evidence

For every row record test names and command, fixture version/hash, code revision, actual result, skipped checks and residual risks. UI rows include browser evidence. Release decisions also require [shared gates](../release-gates.md), [evaluation rules](../evaluation-plan.md) and [review checks](../review-checklist.md). Requirements with pending evidence remain pending regardless of a checked task box.
