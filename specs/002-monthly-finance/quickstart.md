# Synthetic pilot walkthrough

1. Start the database, object storage, API, worker and frontend per the implementation README. Create two fictional test users.
2. Upload the golden bank fixture to user A’s account. Repeat the upload and confirm the same logical job or dedupe response. Upload an overlapping file and review ambiguous candidates.
3. Use a fixture with a balance mismatch. Confirm the displayed expected and computed totals. Restart the worker, apply the correct review revision, and confirm it can resume. Submit the same resume again and confirm one commit.
4. Open Dashboard, Report and Chat on a fixture with ₹45,000 income and ₹55,000 expenses. Verify the ₹10,000 shortfall in all three, and inspect the source rows. Validate a transfer/card/refund fixture separately and compare CSV/PDF totals.
5. Attempt to view, resume and download user A’s data using user B. Verify access is denied. Check captured logs and traces for synthetic identifiers, then turn off the model and trace exporter and repeat the deterministic report.
6. Reverse a completed import and confirm ledger/report versioning, stale status and correct recomputation. Record actual results in the review handoff.

7. Reverse one of two imports supporting the same transaction; confirm it remains exactly once, then reverse the remaining source and verify only the new report revision removes it.
8. Race cancellation with publication and simulate a stale worker; verify one final outcome and a useful UI action.
9. Apply FIN-04 through FIN-16 and verify cash movement, spending, debt and contribution are distinct.
10. Change one account while a multi-account report computes; old results cannot become current. Change a budget and confirm the report's versioned interpretation.
11. Revoke optional processing and request deletion while a job is queued. Confirm no later publication, complete purge status and backup suppression after restore.
12. Run the approved load fixture, scanner outage and quota exhaustion; record measured results. Perform the core journey at phone width and by keyboard.
