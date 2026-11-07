# Feature specification — Document coverage, OCR and transaction corrections

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: R2 adapters individually enabled. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Know what can be uploaded.** User sees supported bank/card/layout versions and limits before trying a file; an unsupported document receives a useful explanation.
- **US2 (P1) Review scanned data.** Low-confidence OCR digits require evidence review and reconciliation before verified publication.
- **US3 (P2) Track cash and corrected rows.** User adds a cash expense or splits a transaction without corrupting the original bank evidence or counting it twice.

## Functional requirements
### F014-FR01 — Format registry
List bank/institution, account type, text/scanned/protected status, layout fingerprint, adapter version, dates tested, limits and support state. One tested pilot bank first. Each bank/card/holdings/tax/policy format is a separate release; no universal PDF support claim.

### F014-FR02 — Parser isolation
Validate signature/MIME, malware result, page/row/decompression/time/memory limits; isolate parser with no network and temporary-file cleanup. Scanner unavailable or inconclusive quarantines the document; a scanner interface alone is not a production scan.

### F014-FR03 — Password handling
Protected files initially return unsupported with guidance. If later enabled, password is supplied through an ephemeral protected channel, never saved in DB/graph/logs/analytics or reused. Do not guess passwords from PAN/date of birth. Clear memory/temp artifacts as feasible and test no persistence.

### F014-FR04 — OCR confidence
Optional local or separately consented licensed OCR, with page/field coordinates and confidence. Critical amounts/dates/balances require calibrated validation plus reconciliation; confidence alone cannot certify accuracy. Keep OCR artifacts private under document retention; never silently repair a digit to force balance.

### F014-FR05 — Manual and split transactions
Separate manual cash entries from imported bank-origin rows. Category splits conserve original amount and source links. Matching a later imported transaction to a manual entry requires evidence/review and preserves both origins without duplicate totals. Edits to source financial fields trigger reconciliation and revision.

### F014-FR06 — Adapter quality and rollout
Held-out layout fixtures, wrapped lines, locale/date formats, refunds, negative/overdraft balances, page headers, repeated amounts and large files. Track field exact-match and reconciled coverage by adapter. Stop affected version on drift; reprocessing is explicit and preserves original published snapshots.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
