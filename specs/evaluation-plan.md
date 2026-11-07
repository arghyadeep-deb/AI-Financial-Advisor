# Evaluation design and release evidence

## Test layers
1. Deterministic unit/property tests: exact money, conservation, boundaries, invariants and independent expected totals.
2. PostgreSQL/service integration: migrations, multi-account concurrency, leases, revisions, auth, outbox, deletion and restore.
3. API and browser acceptance: actual signup/edit/upload/review/export paths for two isolated users; responsive and accessibility checks.
4. AI evaluations: intent, extraction suggestions, citations, abstention, injection resistance, factuality, usefulness and language parity.
5. Operations experiments: worker kill, DB/LLM/storage/scanner/exporter failure, quota exhaustion, load and recovery.

## Dataset governance
Use synthetic or expressly authorized sanitized fixtures. Keep development, regression and held-out sets separate; split by document/layout/merchant family, not random rows from the same statement. Record labels, independent calculation method, reviewer, version and known ambiguity. Never tune prompts on the held-out release set; refresh it when it becomes development material. Customer feedback enters a restricted review process and is not automatically copied into LangSmith or training data.

## Initial proposed evaluation inventory
| Area | Minimum initial coverage | Acceptance |
|---|---|---|
| Financial arithmetic | FIN-01 through FIN-16 plus boundary/property tests | Exact expected paise; no missing-as-zero substitution |
| Import | At least 30 synthetic documents across supported/unsupported/overlap/error cases; held-out family per supported adapter | All critical amount/date/balance cases exact or explicitly blocked; never silently publish wrong critical field |
| Workflow | Kill before/after each durable boundary; duplicate/concurrent submit/resume/reverse/cancel | Zero duplicate business commits or stale publication in suite |
| Authorization/privacy | Every resource endpoint and graph resume; unique synthetic markers in traces/storage/export | Zero cross-user results or forbidden data egress in suite |
| Agent behavior | At least 100 cases across normal questions, missing data, fabricated facts, injection, outages and invalid schemas | Zero unsupported published financial facts/actions in safety suite; measure refusal and fallback rate |
| Categorization | Labeled merchant families, ambiguous/split/refund examples and unseen descriptions | Proposed auto-accept precision >=95% on held-out accepted suggestions, with coverage and per-category counts reported; otherwise review-only |
| Knowledge | At least 40 questions covering stale/conflicting/irrelevant sources and private-data isolation | Every published factual claim has relevant evidence; no stale-source bypass |
| UX | Five novice participants or documented pilot equivalent | Target >=4 unaided core journey completions; record observed results and unresolved blockers |

Counts/thresholds are initial proposed release criteria, not statistical proof of production error rates. Precision with tiny samples is insufficient; report sample counts and confidence intervals and keep auto-accept off if evidence is weak. Increased conservatism must not be hidden: measure abstention, review burden and time to completion alongside accuracy. Financial critical fields require validation regardless of category performance.

## AI output checks
Prefer a schema of referenced metric IDs, allowed categories, evidence IDs and narrative segments. Render authoritative numeric values in application code. Reject mismatched amounts, invented sources, unsupported products, unauthorized actions and stale snapshot IDs. Allow one bounded repair attempt for nonfinancial schema formatting if configured; otherwise deterministic fallback. A model judge may grade clarity, not authorize money or access. Log evaluator/model/prompt versions and failure reasons without raw customer data.

## Tools and lifecycle
Use pytest and deterministic assertions as mandatory release gates. LangSmith can compare approved synthetic/sanitized experiments and metadata traces; it is optional for runtime. Do not introduce multiple eval frameworks solely for branding; adopt an existing repository runner if it can produce reproducible evidence. Every prompt/model/parser/rule change runs affected regression plus held-out evaluation before flag rollout. Canary metadata monitors acceptance, correction and abstention drift; content review requires explicit data policy.

## Run artifact
Record code revision, feature IDs, fixture hash, runner version, prompt/model/provider configuration, seeds where supported, commands, counts by category, failures, coverage, abstentions, cost and timings. Store sanitized results under implementation `evals/results/` or release artifacts. A failed financial safety/tenancy case blocks release regardless of average score. If unavailable providers prevent model tests, report them skipped; offline correctness passing does not imply model quality passed.
