# Feature specification — Household net worth and protection inventory

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: Optional R2 after personal scope works. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) See total wealth.** A user adds property, savings and loans and sees assets minus liabilities with valuation dates and missing coverage.
- **US2 (P1) Share selected data.** An invited adult sees only explicitly granted accounts and loses access immediately on revocation.
- **US3 (P2) Understand insurance documents.** A user sees policy dates and coverage fields with page references, and an unknown field remains unknown.

## Functional requirements
### F011-FR01 — Net worth model
Track assets/liabilities by beneficial ownership share, date, currency, source and liquidity. Manual valuation marked user-declared. Distinguish current observation from projection. Consolidate multiple references to the same holding; no bank balance plus duplicated manual cash.

### F011-FR02 — Household consent
Adults invite/accept memberships with account-level read grants. Membership alone grants no access. No shared passwords. Joint assets require explicit shares and consolidated dedupe. Revocation invalidates cached views, exports and pending queries; recipient exports already downloaded cannot be remotely recalled and must be disclosed.

### F011-FR03 — Privacy boundaries
Private transactions remain private unless separately shared. Summaries can themselves reveal sensitive facts and need explicit grant. No implicit partner access to tax documents. Roles owner/member/viewer; no advisor or operator access through household invitations.

### F011-FR04 — Protection inventory
Store policy type, insurer, coverage, premium, renewal date, exclusions/waiting periods only when evidenced. Support manual entry first; document extraction requires 014 adapter validation. Show renewal reminders and declared dependent coverage, not an automatic promise of adequate insurance.

### F011-FR05 — Nominee and contingency checklist
Allow completion flags for nomination and emergency document location without collecting beneficiary identity documents by default. No legal succession advice or automatic access transfer on death. Unsupported estate tasks yield a checklist.

### F011-FR06 — Coverage and scenario honesty
Report partial net worth when valuation dates or account coverage differ. Household goal allocations cannot spend the same shared asset twice. Currency expansion requires dated FX evidence; INR remains initial supported valuation.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
