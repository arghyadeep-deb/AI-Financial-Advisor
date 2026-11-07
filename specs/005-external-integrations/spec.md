# Feature specification — Credit tracking and external integrations

**Suggested branch** `005-external-integrations` · **Status** Proposed; awaiting user selection. Live adapters gated.

## User stories and independent acceptance

- **US1 (P1) Track credit without a live bureau.** Enter a score and date if available. See unknown or dated user-reported values, credit card dues, and EMIs. The app never assigns a score from missing data.
- **US2 (P2) Refresh accounts through an authorized provider.** When an approved connection is available and consent is valid, sync into the same statement ledger. Expired or withdrawn consent blocks new fetches. Partial sync and provenance remain visible.
- **US3 (P2) Receive an authorized bureau result or hand off tax work.** Keep bureau access and filing separate. Where a live route is approved, show provider provenance and exact status. Filing requires separate user confirmation and verification steps from the chosen official workflow.

## Functional requirements

- **FR-001** Manual credit captures source, report date, and availability. Due dates and utilization require validated balances and limits. No estimated bureau score or loan eligibility claim.
- **FR-002** Each live adapter requires a named provider, eligibility check, permitted use, documented data sharing and retention, owner approval, an independent feature flag, and a test environment. Consent is versioned, scoped, revocable and enforced before every request.
- **FR-003** Treat duplicate and out-of-order webhooks as replayable inputs. Verify signatures and ownership, record provider IDs and timestamps, and handle partial coverage, expiry, outages, and data corrections. Feed bank data through the same ledger rules.
- **FR-004** Confirm the Account Aggregator and permitted FIU arrangement before bank sync. Confirm authorized CIBIL access before bureau retrieval. Confirm the Type 2 ERI path and taxpayer consent before direct filing or prefill. Keep portal credentials out of the app’s generic agent and prompts. [Account Aggregator framework](https://www.financialservices.gov.in/account-aggregator-framework) · [CIBIL partners](https://www.cibil.com/official-partners) · [Official ERI APIs](https://www.incometax.gov.in/iec/foportal/api-specifications)
- **F005-FR05** Credit observation includes bureau/source, report date, score scale where applicable, verification status and optional report evidence. Do not compare unlike bureau scales as a single trend. Unknown/utilization-with-missing-limit remains unavailable. Explain discrepancy and link to official dispute route; no promised score improvement.
- **F005-FR06** Bank sync maintains cursor/window, provider event IDs, consent revision, coverage and correction history. Reconcile provider-synced and PDF evidence through the same ledger to avoid duplicates. Revocation/deletion checked before request and commit.
- **F005-FR07** External actions require an operation state machine: prepared, confirmed, submitted, outcome_unknown, acknowledged, failed or cancelled as applicable. Unknown submission outcome queries provider status; never blind resubmit. Signed callbacks bind to owner and intended operation.
- **F005-FR08** Separate prefill/read consent, bureau fetch and filing confirmation. Persist only necessary provider tokens in managed secret storage; no portal passwords in generic agents. Provider outages show last-refresh/coverage and preserve manual workflows. Support portability/export and provider exit.

## Success criteria

- **SC-001** Manual credit works without provider keys and distinguishes unknown from user-entered and provider-sourced data.
- **SC-002** Provider contract tests cover revoked consent, retry, data isolation, signature and replay, unsupported coverage, and failure. Each live feature needs an independent review and launch decision.

Read [implementation order](../implementation-order.md) for build prerequisites and release gates. See [acceptance mapping](acceptance.md) for requirement-to-task evidence.
