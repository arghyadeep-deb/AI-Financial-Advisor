# Lane J2 ? D06 household privacy (2026-11-07)

Authoritative decision: specs/decision-register.md D06. Read foundation progress/handoff,
implementation order, prior lane remaining sections, feature 011 spec/plan/tasks,
financial rules, agent quality, constitution and release gates. No release authorized.
No git add/commit/push; frontend and backend/main.py untouched.

## Sequential task disposition

1. **PARTIAL ? T1102/T1103 resource sharing.** Contracts first in
   backend/schemas/household.py; backend/models/models.py and migration
   0200_resource_grants.py persist a resource reference and explicit permission set.
   backend/services/household_service.py and household_controller.py restrict reads,
   consolidation and export request/fetch to one owned declared observation/policy.
   Requests without a resource cannot read a whole book. Membership grants nothing.
   Summary and export permissions are independent; queued references bind grant
   revision and reauthorize at fetch. Legacy grants have empty permissions and no
   resource, so remain preserved but inert. Foreign/missing resources return 404.
   Transactions/documents are separate accepted permission names but their shared
   consumers are unsupported and deny access. Chat receives no household context;
   no LLM authority or shared financial cache introduced.
   **PENDING:** imported ledger/bank/portfolio account grant adapters and shared
   transaction/document consumers; permitted shared chat context (currently denied);
   UI, PostgreSQL concurrency/security/release review. Existing owner-only consumers
   remain owner-only. Do not describe this as completed imported-account sharing.

2. **DONE ? J2 adult declaration (controlled synthetic backend).** Household creation
   records the creator's declaration; invitation acceptance records the accepting
   adult's own declaration, never the inviter's assertion about someone else.
   Timestamp, adult-self-declaration.v1 and unverified persist on existing registered
   households/memberships. Statement: "I declare that I am at least 18 years old."
   Existing records remain null (no fabricated historical declaration).
   Files: models.py, household_service.py, 0201_adult_declaration.py,
   tests/test_stage_j2.py. Extra identity-document fields rejected by strict contracts.
   **PENDING launch decision:** production age assurance and legal/privacy review.
   No identity documents collected. No claim of verified age.

3. **DONE ? J2 exact ownership/allocation (offline backend).** Existing integer
   basis points retained; alternatively accept a decimal percentage as a string
   (never a float), exactly one representation. Immutable book JSON retains exact
   strings. Whole-paise divisibility restriction removed. Consolidation rejects
   conflicting facts or combined shares above 100%. allocate_paise uses Fraction
   throughout, largest remainder, lexical stable participant IDs for ties, with
   unallocated bucket ordered last. Allocations plus explicit unallocated paise
   equal original total; unallocated fraction is also returned. Consolidation
   exposes each included resource's allocated/unallocated amounts. For allocation
   among multiple owners call allocate_paise once with all stable owner IDs; do not
   sum independently rounded personal books. This never grants spendable capacity.
   Files: household.py, household_service.py, tests/test_stage_j.py and test_stage_j2.py.
   Seeded 2,500-case property-style conservation/order/bounded-error checks, tie
   fixture, fractional-paise input and >100% rejection ran successfully.

4. **DONE ? J2 in-app-only reminders (existing implementation retained).** Shared
   notification_service/queue already provides metadata-only in-app delivery;
   household policy writes schedule that existing path. No email adapter/path wired.
   Existing T1104 tests cover unknown facts, opt-in, edited policy suppression and
   delivery. Email **DEFERRED/PENDING**, including any future channel approval.

5. **DONE ? remaining scope documented here only.** No feature spec/plan/task files
   edited. Proposed affected-spec corrections: T1102 must specify resource grants
   and four independent permissions; T1103 queued download reauthorization and no
   implicit shared chat; T1101/T1106 exact decimal ownership, largest-remainder and
   explicit unallocated fractions; T1104 in-app only; adult declaration unverified.
   Feature-wide T1102/T1104/T1106 acceptance remains PARTIAL for listed gaps;
   T1105 UI PENDING (orchestrator-owned). Nothing here approves production launch.

## Actual verification

Python for every command below:
`C:/Users/Arghyadeep/Desktop/V.E.C.T.O.R/Projects/AI Advisory/.venv/Scripts/python.exe`

- `-m pytest tests/test_stage_j.py -q -p no:cacheprovider -W ignore`:
  initial 30 passed / 3 failed (fixtures still assumed whole-book grants and set
  serialization). Updated fixtures to explicit resources and JSON mode.
- `-m pytest tests/test_stage_j.py tests/test_stage_j2.py -q -p no:cacheprovider -W ignore`:
  33 passed / 2 fixture errors; imported synthetic_config explicitly, then
  `-m pytest tests/test_stage_j2.py -q -p no:cacheprovider -W ignore`: 2 passed.
- Same J2 command after adult persistence: **3 passed in 4.06s**.
- Final focused `-m pytest tests/test_stage_j.py tests/test_stage_j2.py -q -p no:cacheprovider -W ignore`:
  **36 passed in 27.13s** (obsolete non-whole-paise rejection case replaced).
- `-m pytest tests/test_stage_j.py -k 'T1104' -q -p no:cacheprovider -W ignore`:
  **8 passed, 24 deselected in 3.45s**.
- Full backend and one tests/web run: results to be recorded after completion.

## Migration/recovery and assumptions

0200 down_revision=0173; 0201 down_revision=0200. No new tables; existing
owned_stores registry automatically exports/purges added columns. Coverage and
schema/migration roundtrip checks passed. Temporary SQLite only, no user DB touched.
0200 downgrade refuses to discard resource grants; 0201 refuses to discard adult
attestations. Export/preserve then authorized purge before downgrade, or restore
backup; never silently broaden old grants on rollback. Legacy whole-book grants
require explicit new resource authorization; old export tickets cannot revive them.

Safest scope assumption awaiting owner approval: retain synthetic-only default-off
household gate and production refusal. D06 scope itself is approved, but production
age assurance, imported-account adapter scope, real-data privacy/retention and legal
review, UI/review, independent security and PostgreSQL operational evidence remain
PENDING. External integrations disabled/mocked, no live mail, billing, tax filing,
trades, deployment, remote push or secrets. Prior lane J/H/I open questions outside
this lane remain with their owners. No second ledger/export/queue service created.
