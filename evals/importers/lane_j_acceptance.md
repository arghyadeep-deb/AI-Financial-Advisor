# Lane J adapter evaluation scope

Synthetic adapter only: synthetic-inr-v1 / synthetic.v1. No additional bank
adapter, OCR, protected PDF or real-data support is approved by these tests.

`tests/test_stage_j.py::test_T1406_parser_drift_quarantine_rollback_and_immutable_snapshot`
uses the actual credential-free parser subprocess: a pinned version mismatch
quarantines generation 2, explicit rollback/reprocess creates generation 3;
the original 45,000 income/55,000 spending snapshot and CSV remain byte-stable.
Digest upload still returns latest attempt; direct completed reprocess fails.

`tests/test_stage_j.py::test_T1406_reprocess_restart_lease_fencing_and_wrong_owner`
uses real SQLite sessions, queue claims and lease expiry; old worker cannot
publish and replacement stages exactly two rows. Foreign owner gets 404.

Existing Stage C/F suites retain wrapped/locale/refund/overlap, reconciliation,
financial-envelope comparison and concurrency regression coverage. These are
synthetic regression cases, not held-out evidence for any unapproved adapter.
Actual commands/results and remaining review gates: specs/progress-lane-stage-j.md.
