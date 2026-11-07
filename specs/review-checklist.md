# Codex feature review and release checklist

## Review input

- [ ] Implementation commit range and the relevant spec, plan, tasks, and contract.
- [ ] Requirement-to-test mapping with exact commands, environment, and output. State skipped checks and explain why.
- [ ] Schema migration on a clean and representative legacy database, backup and rollback or forward recovery steps.
- [ ] Browser walkthrough on a fresh fictional account and a second isolated account.
- [ ] Evaluation dataset version, run results, and the trace privacy test.
- [ ] Feature flags, restricted rollout, operational owner, and recovery steps.

## Stop-ship checks

- [ ] Deficit profile yields ₹10,000 shortfall everywhere and no unaffordable contribution or unsupported fund switch.
- [ ] Edited inputs take effect, and prior analysis is visibly stale. Analysis success matches completion state.
- [ ] Unknown score stays unknown. Health-only runs leave holdings state alone. A projection cannot appear as a live balance.
- [ ] One chat message produces one logical turn. Provider outage produces a safe fallback and a useful status.
- [ ] Signed tokens and password migration are tested. Every account boundary including download and graph resume rejects another owner.
- [ ] Bank overlap, transfers, card repayments, refunds, missing dates, retry, restart, and concurrent import cases have independent fixtures.
- [ ] A mismatch, unsupported layout, stale snapshot, or incomplete coverage cannot silently become a complete report.
- [ ] Logs, traces, graph checkpoints and exceptions expose no forbidden fixture payloads. Trace outage leaves core jobs functional.
- [ ] Production rollout records retention, access, supported formats, restore drill, incident owner, and release approval.
- [ ] External providers, personalized securities recommendations, filing, and trading stay gated according to feature specs.

## Evidence and disposition

Document each finding with severity, source file/line, requirement, reproduction, impact, and a specific fix. Include positive verification for high-risk workflows and residual risks. Review decisions are per feature. Re-run affected tests after fixes and keep actual acceptance evidence separate from planned work.

## Cross-feature stop-ship checks
- [ ] Every requirement in the selected release maps to tasks and actual test evidence; unselected backlog is not advertised as delivered.
- [ ] FIN-01 through FIN-16 and applicable boundary cases pass independently expected totals.
- [ ] Shared-evidence reversal, cross-account link invalidation, cancel/commit races and reprocess generations pass.
- [ ] Multi-account revision vectors prevent stale publication; budgets/goals do not double-allocate cash.
- [ ] Account export/deletion reaches all stores; restore cannot resurrect a deleted account; retention is documented.
- [ ] Recovery tokens, session revocation, privilege controls and consent races pass.
- [ ] Scanner failure quarantines; parser is isolated; published format limits match tested adapters.
- [ ] Held-out evaluations, sample counts, coverage and abstention are recorded; no invented model results.
- [ ] Load/latency/queue recovery, quotas, cost budgets and restore meet ratified targets on recorded hardware.
- [ ] Core UI works on phone and keyboard; pilot usability results and remaining issues are documented.
- [ ] Allocation, research, tax, sharing and provider-specific releases pass their independent gates.
- [ ] No market-parity, guaranteed-return, CA/CFA replacement or complete-tax-service claim exceeds delivered scope.
