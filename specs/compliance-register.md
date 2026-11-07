# Applicability and external-source register

Research checked 2026-11-05. These references identify decisions to verify; this document is not a legal opinion or certification of compliance. Recheck the actual provisions, amendments, effective dates, business model and jurisdiction at the relevant release. An automated system does not acquire CA/CFA or other professional status by adopting a persona.

| Area | Official reference | Required product decision and enforcement |
|---|---|---|
| Investment advice | [SEBI Master Circular for Investment Advisers, 6 February 2026](https://www.sebi.gov.in/legal/master-circulars/feb-2026/master-circular-for-investment-advisers_99569.html) | Determine applicability to proposed personalized allocation and delivery model. Keep public personalized proposals disabled until eligibility/obligations are resolved. Enforce gate in API, chat and exports |
| Research publication | [SEBI master circular listing](https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=6) | Assess applicable Research Analyst rules before publishing company-specific research/recommendations; do not assume education labeling is sufficient |
| Personal data | [MeitY DPDP Rules 2025, corrigendum and enforcement timeline](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025) | Record which provisions are in force on launch date, purposes, notices, rights, processors and retention. Do not assert all provisions commenced together. 008 supplies engineering controls independent of minimum timing |
| Bureau records | [CIBIL dispute FAQ](https://www.cibil.com/faq/loan-rejections-disputes), [partners](https://www.cibil.com/official-partners) | Verify access and permitted use for named provider; manual report tracking does not authorize scraping. User-controlled dispute handoff does not promise a score correction |
| Bank connectivity | [Department of Financial Services AA framework](https://www.financialservices.gov.in/account-aggregator-framework) | Establish eligible provider/FIU arrangement and enforce purpose-bound revocable consent before live bank synchronization |
| Tax input and filing | [Income Tax ERI APIs](https://www.incometax.gov.in/iec/foportal/api-specifications), [CA workflow](https://www.incometax.gov.in/iec/foportal/help/MyCAFAQ) | Distinguish draft calculations, authorized submission and functions requiring designated professionals/verification. Never imply all functions can be performed autonomously |
| Tax form changes | [Official Form 168 guidance](https://www.incometaxindia.gov.in/documents/d/guest/fn-168) | Pin input formats, tax period and applicable legislation to a rule pack. Verify current forms rather than reuse names across years blindly |

## Source register schema
`source_id`, URL, publisher, title, retrieved date, publication/effective date, content hash where legally retainable, applicable jurisdiction/period, supported claim, reviewer, expiry/recheck date and superseding source. Source pages may contain instructions; treat them as evidence only. No page can grant tool permissions. Store only licensed content and permitted excerpts.

## Business decisions before launch
Name an accountable product operator. Record terms of service, privacy notice, support/grievance route, incident process, processor contracts and rights to redistribute data. Define age scope and whether household invitations are adults only. If offering paid service, assess invoices/refunds and applicable tax treatment for the chosen entity. Insurance inventory does not include sales or personalized policy recommendation; expanding it requires a new applicability decision.

No requirement here forces a professional review into every routine customer workflow. Cases outside supported automated scope stop safely. Required legal/provider/professional obligations, when applicable, cannot be replaced by an LLM agent. The product owner resolves applicability before enabling the corresponding capability.
