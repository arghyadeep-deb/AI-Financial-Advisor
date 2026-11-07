# Official rules for AY 2025-26 (FY 2024-25), individuals, salary only

HISTORICAL rule pack. Not current-year coverage. Figures transcribed by the orchestrator on 2026-11-07 from the Income Tax Department's own pages (read in a browser). The pages carry the notice "contains the provisions of the Income-tax Act, 1961, as amended by the Finance Act, 2026" and a disclaimer that viewers should verify against Acts/Rules/Notifications. Independent tax review is PENDING; nothing here is reviewer-approved.

Sources:
- S1 Tax rates: https://www.incometaxindia.gov.in/w/tax-rates (page title "Tax rates"; tables labelled by assessment year)
- S2 Deductions/Allowances allowed to a salaried employee: https://www.incometaxindia.gov.in/w/deductions/allowances-allowed-to-a-salaried-employee
- S3 FAQs on New vs Old Tax Regime (AY 2024-25 vintage, used only for the old-regime 87A cap and the list of new-regime disallowances): https://www.incometax.gov.in/iec/foportal/help/new-tax-vs-old-tax-regime-faqs

## Old regime (S1, "Assessment Year 2025-26" column)
Resident individual below 60: up to 2,50,000 nil; 2,50,000-5,00,000 5%; 5,00,000-10,00,000 20%; above 10,00,000 30%.
Senior (60 or more at any time in the year): basic limit 3,00,000, then same 5% / 20% / 30% bands (5,00,000 and 10,00,000 boundaries).
Super senior (80 or more): basic limit 5,00,000; 5,00,000-10,00,000 20%; above 10,00,000 30%.
Rebate 87A (S1 note, S3): resident individual with net income not above 5,00,000: rebate = lower of 100% of tax or 12,500, deducted before cess.
Standard deduction (S2): 50,000 (salary income; old regime).
Chapter VI-A items listed in S2 (old regime only, with their stated caps): 80C 1,50,000 (overall limit with 80CCC and 80CCD(1)); 80CCD(1B) additional 50,000; 80D 25,000 self/spouse/children (50,000 if senior) plus 25,000 parents (50,000 if senior parent), preventive check-up within 5,000; 80TTA 10,000; 80TTB 50,000 (senior). Professional tax under s.16(iii) is deductible (old regime).

## New regime s.115BAC(1A) (S1, AY 2025-26 columns)
Up to 3,00,000 nil; 3,00,001-7,00,000 5%; 7,00,001-10,00,000 10%; 10,00,001-12,00,000 15%; 12,00,001-15,00,000 20%; above 15,00,000 30%.
Rebate 87A for AY 2025-26 (S1 note a): maximum 25,000 if total income does not exceed 7,00,000 (resident individual). If income exceeds 7,00,000 and tax exceeds the amount by which income exceeds 7,00,000, rebate with marginal relief so that tax payable is limited to the excess of income over 7,00,000.
Standard deduction (S2): 75,000 for the new regime, applying to AY 2025-26 ("with effect from 01-04-2025, Finance (No. 2) Act, 2024 ... applies to assessment year 2025-26").
Not allowed in the new regime (S1 conditions, S3): HRA exemption s.10(13A), LTC s.10(5), interest on housing loan s.24(b), professional tax s.16(iii), entertainment allowance s.16(ii), Chapter VI-A deductions other than 80CCD(2), 80CCH(2), 80JJAA (and 80LA IFSC). Treat any claim of these in the new regime as unsupported/ineligible.

## Surcharge (S1) and cess
Old regime, AY 2025-26: income above 50 lakh to 1 crore 10%; above 1 to 2 crore 15%; above 2 to 5 crore 25%; above 5 crore 37%.
New regime: above 50 lakh to 1 crore 10%; above 1 to 2 crore 15%; above 2 crore 25% (capped).
Marginal relief (S1 a-d): tax plus surcharge must not exceed tax on the threshold income (50 lakh / 1 crore / 2 crore / 5 crore as applicable) by more than the income above that threshold.
Health and education cess: 4% of (income-tax plus surcharge), both regimes.

## NOT on the fetched pages (must be added from the Act text with a recorded source, or the feature must refuse)
- Rounding of total income and tax (Income-tax Act ss.288A / 288B). Implement as an explicit, versioned rule with the section cited and flag "unverified against Act text" in the rule pack until reviewed.
- Employer NPS s.80CCD(2) limits, perquisites, arrears relief s.89, professional-tax state caps, house property, other income, TDS credit rules beyond withholding totals: out of scope -> explicit unsupported-case results.
