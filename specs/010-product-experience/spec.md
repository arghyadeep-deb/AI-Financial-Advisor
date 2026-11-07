# Feature specification — Onboarding, responsive UI, accessibility and notifications

**Status: Proposed; not authorized for implementation.** Version 2.1 · 2026-11-05

Release: Core R1; richer experience R2. Build prerequisites and release subsets: [implementation order](../implementation-order.md).

## User stories and independent acceptance
- **US1 (P1) Start without finance knowledge.** A new user can try demo data, see supported formats, upload a document and explain their first report without developer assistance.
- **US2 (P1) Use a phone or keyboard.** Core journeys work at 360px width and by keyboard, with clear focus and text alternatives for charts.
- **US3 (P2) Understand incomplete work.** An upload stuck, rejected, awaiting review or partially complete shows the specific next action and preserves edits.

## Functional requirements
### F010-FR01 — Navigation and onboarding
Organize Overview, Transactions, Plan, Portfolio, Tax, Documents and Settings; hide unreleased capabilities or label preview clearly. Explain spending versus cash movement and verified versus estimated data. Demo account is isolated and unmistakably fictional.

### F010-FR02 — Core interaction states
Design empty/loading/partial/stale/error/offline/retry/success states. Persistent upload status and resumable review; no infinite spinner. Save feedback and revision conflict UI. Search/filter/paginate transactions and inspect source without losing filter state.

### F010-FR03 — Responsive and accessible
Target WCAG 2.2 AA for core flows; verify keyboard order, labels, contrast, readable tables, focus, error announcements and chart text summaries. Test phone, tablet and desktop widths. Money formatting uses Indian grouping with unambiguous dates; locale never changes stored values.

### F010-FR04 — Language and literacy
English plain-language first with a glossary for EMI, surplus, return and coverage. Hindi/Hinglish labels/explanations are a separately evaluated locale using identical canonical amounts. No untranslated mixed error fragments or model translation of legal/accounting fields without review.

### F010-FR05 — Notifications and preferences
In-app first; email/push only after channel choice and verification. Configure quiet hours, category preferences, digest cadence and unsubscribe. No private balances or account details in default external content. Transactional critical-account messages remain separately documented.

### F010-FR06 — Feedback and usability evidence
Users can report wrong categorization or unclear explanation with explicit evidence-sharing choice. No raw document attachment by default. Test five representative novice participants or documented equivalent pilot; target at least four completing upload-review-report unaided, record issues and fixes rather than inventing results.

## Acceptance and scope
Every requirement must have positive, invalid-input and wrong-owner evidence. Domain fixtures must compute expected values independently. [Tasks](tasks.md) contain concrete completion criteria; [plan](plan.md) specifies boundaries. No live feature is enabled solely because all code tasks are checked. Source/privacy/operational gates in [release gates](../release-gates.md) apply. Unavailable evidence is an explicit user-visible state. Apply [financial rules](../financial-rules.md) and [agent controls](../agent-quality.md).

See [requirement-to-task acceptance mapping](acceptance.md) for complete planned coverage and evidence requirements.
