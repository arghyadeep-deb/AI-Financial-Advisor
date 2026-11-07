# Feature specification — Reliable analysis and account safety

**Suggested branch** `001-reliable-foundation` · **Status** Proposed; awaiting user selection · **Date** 2026-11-05

## User stories and independent acceptance

- **US1 (P1) A profile produces consistent financial facts.** Given ₹45,000 monthly income, ₹55,000 expenses, and no holdings, Dashboard, Reports, and Chat agree on the ₹10,000 deficit. No affordable contribution or fund-switch instruction is shown. Given the income changes to ₹65,000, the old result is marked outdated and a fresh run uses the ₹10,000 surplus. Exercise each edit form from the browser and confirm its submitted values take effect.
- **US2 (P1) A user can sign in and see only their data.** Given two test users, each can access their own profile, analysis, and chat only. A guessed ID, invalid token, or signed token with malformed claims fails safely. A startup with a missing or placeholder signing key refuses production mode.
- **US3 (P2) Failure is clear and recoverable.** Given all model providers fail, verified calculations remain available, missing sections are visibly unavailable, and Chat accepts one logical turn. Retrying a failed operation cannot duplicate the turn. A cold or unavailable backend gives a bounded wait and recoverable UI state.

## Functional requirements

- **FR-001** Centralize cash flow, affordability, unknown inputs, and recommendation eligibility in tested application rules. Available monthly contribution is never negative and cannot exceed verified discretionary cash after configured reserves and commitments. Suppress named-product advice where inputs, product data, or release permissions are absent.
- **FR-002** Every analysis records owner, kind, status, input profile revision, timestamps, and per-section provenance. Latest queries select current results by purpose and recency. Stale reports remain explicitly labeled. An in-flight result for an old revision cannot become current.
- **FR-003** Decide and label each edit form as profile save or a one-off scenario. Validate and use the submitted values. Scenario requests leave the profile revision unchanged. Keep the supported saved-profile API contract.
- **FR-004** Separate actual holdings value, estimated or scenario values, and projections. Preserve state owned by another analysis type. Legacy projected values stored under portfolio value cannot be promoted to observed holdings.
- **FR-005** Unknown credit stays unknown throughout all screens and scoring. Remove public tax-savings figures backed only by income bands. Document which health metrics are unavailable. Debt balance and monthly payment are distinct inputs. Keep signed shortfall visible.
- **FR-006** Require secure auth settings. Use a salted password hash with a versioned legacy migration or reset flow, short-lived validated tokens with required claims, login protections, and object-level authorization. Deny unsafe production startup. Avoid emitting authentication details in error messages and logs.
- **FR-007** Provide typed section outputs, safe error responses, bounded calls and one logical chat message per submission. A model response cannot change canonical values. Fallback provenance reaches UI and storage.
- **FR-008** Introduce repeatable setup, migrations, PostgreSQL configuration, structured privacy-safe logs, and tests for auth, finance, UI submissions, and tracing. Validate backup and restore before real uploads. Establish a local metadata-only telemetry path with optional LangSmith.
- **F001-FR09** Define authentication lifecycle: token claims/expiry, logout/session revocation, reset token reuse protection, browser token handling, CSRF where applicable, rate-limited login and generic enumeration-safe errors. 008 owns export/delete reauthentication and privileged MFA.
- **F001-FR10** Define profile aggregate versus ledger precedence, schema versions and conflict behavior under the shared snapshot envelope. Existing frontend and APIs must use the same metric definitions.
- **F001-FR11** Required exact-money boundaries include serialization, DB persistence and CSV/PDF exports, not only internal calculation. Reject nonfinite values and unbounded amounts.
- **F001-FR12** Production secrets cannot use fallback defaults; key rotation and legacy account recovery need explicit migration fixtures. CI includes secret/dependency checks and representative legacy migration. Do not expose sample secrets in production documentation.

## Success criteria

- **SC-001** All deficit, zero balance, unknown score, health-only, stale/concurrent analysis, malformed model output, and outage golden tests pass.
- **SC-002** All two-user checks for profile, chat, report, and bad tokens pass. Legacy accounts follow a tested login or reset path.
- **SC-003** Browser form edits affect only their documented target. Re-running a failed chat stream cannot create a second user turn.
- **SC-004** A clean environment can install locked dependencies and run the suite without real provider keys. Both fresh and representative legacy migrations pass.

Read [implementation order](../implementation-order.md) for build prerequisites and release gates. See [acceptance mapping](acceptance.md) for requirement-to-task evidence.
