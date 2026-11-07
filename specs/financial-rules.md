# Canonical financial rules and golden examples

Planning contract v2. All amounts in examples are INR; store integer paise or exact decimal. Persist UTC timestamps, original posting date and applicable Asia/Kolkata report month. Reject ambiguous date formats. Do not infer a missing value as zero.

## Metric definitions
Account cash movement = sum of posted signed bank rows in the scope. Opening balance + signed movements = closing balance when the source supplies comparable balances; normalize debit/credit and overdraft semantics per adapter. Card liabilities use a separately documented sign convention; do not reuse bank balance arithmetic without conversion.

Household earned/other income excludes own-account transfers, borrowed principal, refunds, investment sale proceeds and unclassified credits. Household spending counts purchases, fees and interest; loan principal and investment contributions are separately reported uses of cash. Card purchases are spending at posting; card settlement is not spending again. Unclassified movements are displayed separately and make the relevant income/spending metrics incomplete. A reconciled account can still have incomplete classification.

Recognized surplus = recognized income minus net spending. It is NOT automatically available to invest. Available contribution uses the conservative minimum of a verified recurring-flow capacity and current eligible liquid cash, subtracting upcoming unfunded commitments, minimum debt payments, explicit reserve shortfall funding and other earmarks. Count each commitment once using obligation IDs; historical cash already spent is not subtracted again from current cash. Missing required coverage means unavailable, not a positive contribution. Historical monthly surplus alone does not prove future salary or liquidity.

Personal expenses, reimbursements, savings, principal repayments and transfers each have separate report metrics. Loan EMI is split into principal and interest only with evidence; otherwise show an unsplit debt payment and incomplete spending composition. No allocation proposal assumes every bank inflow is disposable income.

## Required fixture examples
| ID | Input | Expected behavior |
|---|---|---|
| FIN-01 | Salary 45,000; recognized expenses 55,000 | Surplus -10,000; shortfall 10,000; eligible contribution 0 |
| FIN-02 | Transfer 5,000 from owned A to owned B | A cash -5,000, B cash +5,000, household income/spending 0; selected scope explains excluded counterparty |
| FIN-03 | Card purchase 2,000 and bank settlement 2,000 | Spending 2,000, not 4,000; preserve both rows and liability settlement |
| FIN-04 | Loan disbursement 100,000 | Borrowing inflow 100,000; earned income 0; do not infer complete loan terms from the row |
| FIN-05 | EMI 10,000 documented as principal 8,000/interest 2,000 | Debt cash use 10,000; interest spending 2,000; liability reduction 8,000; no double count in affordability |
| FIN-06 | Stock purchase 5,000 | Investment cash use 5,000; consumption spending 0; bank row alone does not establish instrument/units |
| FIN-07 | Sale proceeds 6,000 without cost basis | Disposal cash inflow 6,000; return/gain unavailable; not salary income |
| FIN-08 | January purchase 1,000; February confirmed refund 400 | January snapshot stays 1,000 spending; February refund adjustment 400 and net category spend -400 if no new purchase; lifetime unreimbursed purchase 600 |
| FIN-09 | User wants January restated after FIN-08 | New explicitly restated snapshot, original retained; February cash movement remains +400; never silently rewrite history |
| FIN-10 | Shared meal 1,200; confirmed reimbursement due 600; received 200 | Cash purchase 1,200; separate own-share view 600; receivable remaining 400; received reimbursement not earned income |
| FIN-11 | Withdrawal 2,000 | Transfer to tracked cash account or unresolved cash movement; not automatically spending. Later cash purchases reduce cash without double counting |
| FIN-12 | Two genuine 500 debits on same date and merchant | Preserve two entries unless stable reference/evidence proves duplicate |
| FIN-13 | Opening 1,000; credits 500; debits 200; closing 1,300 | Reconciled. Closing 1,299 blocks verified status; tolerance zero paise for exact text sources |
| FIN-14 | Income 65,000; spending 55,000; future unfunded principal obligation 4,000 and reserve funding 3,000, liquid availability sufficient | Flow capacity 3,000, not 10,000. Declare which obligations are already included to avoid duplicate deduction |
| FIN-15 | Portfolio A 80,000; bank 20,000; debt 30,000 | Net worth 70,000 if complete and same reporting basis; future projection never added |
| FIN-16 | Missing account covering salary or unknown outgoing transfer | Show coverage warning and unresolved movement; affordability unavailable until sufficient evidence/user-declared assumptions |

## Corrections, sources and time
Corrections are revisions with actor, reason and source. A user-confirmed label is distinct from bank-observed facts. Split categories must sum exactly to the original amount and cannot change its bank balance effect. Refund/reimbursement allocations cannot exceed remaining eligible amounts; allow documented fees and partial settlements as separate components. Pending rows do not count as posted; pending-to-posted transitions are matched explicitly. Future dates and out-of-period rows trigger review.

Statements prove activity in specified accounts and periods, not completeness of the user's finances. Store declared account inventory, coverage intervals and missing-day ranges. Compute household report revision from the complete vector of included account revisions, link revisions and rule version. Recheck all before publishing; a single account revision is insufficient.

## Precision and performance
Units use instrument precision; prices and FX use exact decimals and dated sources; round display amounts only at documented boundaries. Totals sum unrounded components then round consistently. Reject NaN, infinity and numeric overflow. XIRR requires dated cash flows and a terminal value; undefined/no-solution/multiple-root cases must not display a made-up result. Show time-weighted return only with sufficient valuation history. Benchmark comparisons must use the same dates, cash-flow methodology and currency, with missing data labeled. Formulas require independent expected fixtures, not tests derived from the same implementation.
