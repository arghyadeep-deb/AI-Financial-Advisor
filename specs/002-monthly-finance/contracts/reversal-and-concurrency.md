# Import cancellation, reversal and evidence lifecycle

## Scope and invariants
Business DB is authoritative. Every canonical transaction has one or more active supporting evidence links. Reversing an import deactivates that import's support, not necessarily the canonical transaction. Origin rows remain immutable until privacy deletion policy purges them. A reversal must be replay-safe and serialized against publication for affected accounts.

## State transitions
Queued/validating/quarantined/extracting/needs_review can transition to cancel_requested then cancelled after the worker acknowledges or a fenced recovery worker takes over. Publishing cancellation competes on the same transactional guard: if commit wins, report completed and offer reversal; if cancellation wins, no ledger write. Only failed_retryable may use the retry action; failed_final requires corrected input or an explicitly permitted new reprocess generation. Completed may reverse to reversed; repeat reversal returns original result. A reversed job cannot be resumed or retried into publication. Reimport requires an explicit new generation under the same document identity, not an accidental bypass of digest dedupe.

## Evidence-aware reversal algorithm
1. Authenticate owner, expected job revision and idempotency payload. Lock affected account(s) in stable ID order; check cancellation/deletion state.
2. Deactivate evidence from the target import; retain evidence from other active imports/manual confirmed origin.
3. A canonical transaction with remaining active support stays active exactly once. With no support, mark inactive by new revision; do not destructively remove published historical rows.
4. Invalidate affected transfer/refund/reimbursement and settlement links. Recompute remaining eligible amounts; require review if links become ambiguous. Never leave a link to an inactive transaction counted in current totals.
5. Increment affected account/link revision vector, write audit/outbox events and job outcome in one transaction. Recompute current reports; historical snapshots keep their historical lineage and explicit superseded status.
6. Recheck report scope revision vector before publication. A stale worker cannot overwrite a later report. Exports identify their immutable report version and may warn that a newer version exists.

## Required scenarios
| Case | Expected |
|---|---|
| A and B statements both support transaction X; reverse A | X remains once via B |
| Reverse B after A | X inactive in new current revision; original reports remain inspectable |
| A has X and Y; B corroborates X | Reverse A retains X and removes only unsupported Y |
| X linked transfer to Z; reverse sole support for X | Link invalidated; Z becomes unmatched, not new salary |
| Refunded purchase removed | Refund link reviewed/unlinked; cash credit remains; no fabricated income |
| Concurrent reverse A and report compute | Report either uses complete old vector or new vector; old result cannot be current |
| Cancel races with commit | Exactly one final business result; UI offers reversal if commit won |
| Retry after graph checkpoint failed post-commit | Read committed business marker; no second posting |
| Corrected parser version reprocesses same bytes | Explicit generation with comparison/review; no duplicate append |

## API additions
`POST /statement-imports/{id}/cancel`, `/reverse`, `/reprocess` accept expected revision and idempotency key; response includes generation, state, affected accounts/months and review references. Changed payload with reused key returns 409. `GET /statement-imports/{id}/events` pages safe owned events. Document expiry/deletion may remove source bytes; retained report access follows approved retention rather than an unconditional promise of permanent originals.
