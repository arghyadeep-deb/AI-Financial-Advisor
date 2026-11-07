# Requirement and task coverage index

Planning inventory only. No task has implementation/test evidence yet. FR identifiers in the original five specs are local to their feature; qualify them with the folder. New identifiers use Fnnn-FRnn. Each implementation must map every selected requirement to concrete tests and record partial/deferred coverage explicitly.

| Feature | Requirements | Task IDs |
|---|---|---|
| [001-reliable-foundation](001-reliable-foundation/spec.md) | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, F001-FR09, F001-FR10, F001-FR11, F001-FR12 | T101, T102, T103, T104, T105, T106, T107, T108, T109, T110, T111, T112, T113, T114, T115 |
| [002-monthly-finance](002-monthly-finance/spec.md) | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, F002-FR09, F002-FR10, F002-FR11, F002-FR12, F002-FR13, F002-FR14 | T201, T202, T203, T204, T205, T206, T207, T208, T209, T210, T211, T212, T213, T214, T215, T216, T217, T218, T219, T220 |
| [003-portfolio-risk](003-portfolio-risk/spec.md) | FR-001, FR-002, FR-003, FR-004, F003-FR05, F003-FR06, F003-FR07, F003-FR08 | T301, T302, T303, T304, T305, T306, T307, T308, T309, T310 |
| [004-tax-preparation](004-tax-preparation/spec.md) | FR-001, FR-002, FR-003, FR-004, F004-FR05, F004-FR06, F004-FR07, F004-FR08 | T401, T402, T403, T404, T405, T406, T407, T408, T409 |
| [005-external-integrations](005-external-integrations/spec.md) | FR-001, FR-002, FR-003, FR-004, F005-FR05, F005-FR06, F005-FR07, F005-FR08 | T501, T502, T503, T504, T505, T506, T507, T508, T509, T510 |
| [006-budgets-goals-debt](006-budgets-goals-debt/spec.md) | F006-FR01, F006-FR02, F006-FR03, F006-FR04, F006-FR05, F006-FR06 | T0601, T0602, T0603, T0604, T0605, T0606, T0607 |
| [007-personalized-allocation](007-personalized-allocation/spec.md) | F007-FR01, F007-FR02, F007-FR03, F007-FR04, F007-FR05, F007-FR06 | T0701, T0702, T0703, T0704, T0705, T0706, T0707 |
| [008-privacy-account-lifecycle](008-privacy-account-lifecycle/spec.md) | F008-FR01, F008-FR02, F008-FR03, F008-FR04, F008-FR05, F008-FR06 | T0801, T0802, T0803, T0804, T0805, T0806, T0807 |
| [009-production-operations](009-production-operations/spec.md) | F009-FR01, F009-FR02, F009-FR03, F009-FR04, F009-FR05, F009-FR06 | T0901, T0902, T0903, T0904, T0905, T0906, T0907 |
| [010-product-experience](010-product-experience/spec.md) | F010-FR01, F010-FR02, F010-FR03, F010-FR04, F010-FR05, F010-FR06 | T1001, T1002, T1003, T1004, T1005, T1006 |
| [011-household-networth-protection](011-household-networth-protection/spec.md) | F011-FR01, F011-FR02, F011-FR03, F011-FR04, F011-FR05, F011-FR06 | T1101, T1102, T1103, T1104, T1105, T1106 |
| [012-knowledge-research](012-knowledge-research/spec.md) | F012-FR01, F012-FR02, F012-FR03, F012-FR04, F012-FR05, F012-FR06 | T1201, T1202, T1203, T1204, T1205, T1206 |
| [013-commercial-support](013-commercial-support/spec.md) | F013-FR01, F013-FR02, F013-FR03, F013-FR04, F013-FR05, F013-FR06 | T1301, T1302, T1303, T1304, T1305, T1306 |
| [014-document-coverage](014-document-coverage/spec.md) | F014-FR01, F014-FR02, F014-FR03, F014-FR04, F014-FR05, F014-FR06 | T1401, T1402, T1403, T1404, T1405, T1406 |

## Requirement-to-evidence handoff template

| Requirement | Implementing task(s) | Positive/negative/owner/concurrency tests | Fixture/version | Actual result and artifact |
|---|---|---|---|---|
| Populate for selected scope | Not yet implemented | Include applicable classes; justify N/A | Independent expected values | Pending |

Shared requirements must be mapped too: financial examples to ledger/planning tests; privacy lifecycle to all persisted stores; snapshot revisions to all derived views; operational budgets to every async/model path. Existing broad tasks are not proof of full coverage.
