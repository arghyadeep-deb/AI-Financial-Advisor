# Stage I2 - D05 allocation assumption register

Completed by Claude after the Codex usage limit; code authored by the Codex lane, verified here. No new migration (0190..0199 unused).

1. Versioned assumption register: **done**. `backend/finance/allocation_assumptions.py`, `knowledge_base/allocation/register-v1.json` (id, version, source name/url/publisher, as_of, expires, methodology, uncertainty, status). Read API in portfolio controller. Real recommendations are refused ("assumptions not validated") unless every used assumption is `validated`; none are. Invented numbers live only in `tests/fixtures/allocation/` labelled synthetic_test. Old `synthetic-v1/v2.json` removed.
2. 10% cash floor and 36-month rule: **done**. Configurable `cash_floor_bps`/`near_term_months`, status `unvalidated_prototype`, labelled in outputs; invalid overrides rejected; register expiry blocks the solver; policy revision stales owned plans without rewriting them.
3. Blanket 7-day liquidity: **removed**. Liquidity is `unknown` unless instrument/restriction/settlement evidence is supplied; unknown never meets a deadline.
4. Solver, constraints, scenarios, explanations: working. Execution disabled, public advice hard-false, no named products.
5. PENDING (no reviewer appointed): parameter validation of the prototype values; separate public-advice eligibility decision.

Tests: `python -m pytest tests/allocation tests/portfolio -q -p no:cacheprovider -W ignore` -> **124 passed**.
