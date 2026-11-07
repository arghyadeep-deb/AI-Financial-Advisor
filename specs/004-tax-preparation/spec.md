# Feature specification — Tax preparation agent

**Suggested branch** `004-tax-preparation` · **Status** Proposed; awaiting user selection

## User stories and independent acceptance

- **US1 (P1) See what documents support a draft.** Upload supported salary and tax records for a selected period. Review extracted income and withholding figures, their source fields and any missing or conflicting values.
- **US2 (P1) Compute a draft for a supported case.** Given a fictional salaried resident case with complete supported income and withholding, show a reproducible draft with selected period and regime, supported assumptions, and missing items. Unsupported cases stop at a checklist.
- **US3 (P2) Export a review pack.** Download the versioned draft and evidence summary. When an input or rule changes, the previous draft is clearly stale.

## Functional requirements

- **FR-001** Begin with one documented salaried resident profile and one period/rule pack. Validate the source and scope of the official rules before implementation. Treat Form 16 and other supported documents as period-specific layouts. Separate assessment years under the 1961 Act from tax years under the 2025 Act. The department describes Form 168 for the evolved Annual Information Statement from Tax Year 2026–27. [Tax transition guidance](https://www.incometax.gov.in/iec/foportal/help/all-topics/e-filing-services/tds-compliance)
- **FR-002** Track original source, taxpayer identity match, income field, withholding field, and conflicts. Accept corrected values with evidence. Bank inflows alone do not determine taxable income.
- **FR-003** Use deterministic, documented rules for the supported period and regime. Publish breakdown and applicable assumptions. Explicitly stop or flag additional income categories, multiple employers, capital gains, foreign income, business income, or unsupported deductions until covered.
- **FR-004** Keep the export a draft for user review. Direct filing and statutory certification are separate feature gates. Protect sensitive tax fields and exclude originals and identifiers from model calls and traces. [Income Tax Department CA workflow](https://www.incometax.gov.in/iec/foportal/help/MyCAFAQ)
- **F004-FR05** Build a supported-input matrix: person/residency, selected tax period, regime, income classes, form/layout versions, deductions, withholding and payment sources. Give a precise reason and useful checklist when outside scope. A bank statement is corroboration, not complete proof of taxable income.
- **F004-FR06** Each tax rule pack records official provision/source, effective period, parameters, rounding, exemptions, rebates, surcharge/cess where applicable, verification date and replacement rules. Do not fill in current statutory rates from model memory. Validate independently calculated boundary cases before enabling a pack.
- **F004-FR07** Reconcile identity, period, income and withholding across supported sources. A disagreement produces a review item; user correction retains both original and evidence. No automatic preference that silently suppresses reported income.
- **F004-FR08** Annual refresh and correction invalidate affected drafts; old exports display pack/date and draft status. Preview old/new regime only when both are explicitly supported. 005 filing requires a different contract and approval; a draft export must not resemble an official acknowledgment.

## Success criteria

- **SC-001** Golden official-reference cases for the chosen period pass exact expected checks, including unsupported or conflicting records. Mixing adjacent periods never silently produces a draft.
- **SC-002** All draft values trace to a document field or a documented computation. Replay, revision, tenant access and export tests pass.

Read [implementation order](../implementation-order.md) for build prerequisites and release gates. See [acceptance mapping](acceptance.md) for requirement-to-task evidence.
