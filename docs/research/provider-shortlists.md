# Provider shortlists (research only)

Date: 2026-11-07. RESEARCH ONLY: no accounts created, no subscriptions, no credentials entered, no live integration enabled. Sources are mostly vendor or secondary pages found by web search; figures conflict in places. Every number below must be re-verified on the provider's official page or by quote before any decision. Stages are kept apart: provider research (this file) -> adapter implementation (disabled, fake-tested) -> live activation (separate owner/legal/security decision).

## 005 Credit and bank data (pilot = manual dated credit entry + statement uploads; live adapters disabled)

Regulatory finding (to confirm with the RBI Master Direction and Sahamati, and with a lawyer): to be a Financial Information User (FIU) on the Account Aggregator network, a source states only entities regulated by RBI, SEBI, IRDAI or PFRDA are eligible, plus signing Sahamati participation terms and certification (Sahamati, "How to join the Account Aggregator network"; vendor docs). This project may not qualify directly. Do not assume access.

| Candidate | What it is | Cost indication (unverified) | Eligibility / limits | Effort |
|---|---|---|---|---|
| A. AA via a technology service provider (e.g. Setu, Finvu, OneMoney, Anumati) | Consent-based bank data via RBI-licensed aggregators | Finvu ~INR 20-30 per fetch reported; OneMoney per-account INR 0.30-9.90 reported; Setu/Anumati: not found, quote required | FIU eligibility above; a TSP may onboard on your behalf only if you are an eligible regulated entity or work through one | High: ReBIT spec, certification, consent/revocation UX |
| B. Bureau data via multi-bureau aggregator (e.g. Roopya-type "specified user" platforms) | Credit reports through a partner holding bureau agreements | ~INR 45-55 per pull reported; direct membership INR 2-10 lakh/year reported (weak source) | RBI 2022 rules let fintechs be "specified users"; conditions vary by bureau (CISA/certification claims unconfirmed) | High, plus legal |
| C. Direct bureau API (CIBIL, Experian, CRIF, Equifax) | Direct integration | Quote required | Specified-user status plus bureau onboarding | Highest |

Recommendation: stay on manual dated credit entry and statement upload for the pilot (already the decision). Before any live option, get legal advice on whether the project may act as an FIU or specified user, or whether a regulated partner must hold the licence. Unknown: our eligibility, real pricing, sandbox access outside hackathons, retention rules.

## 013 Billing (pilot is free; flag disabled; selection deferred until operating costs and paid features are known)

| Candidate | Reported pricing (verify officially) | Notes |
|---|---|---|
| Razorpay | ~2% + GST standard; subscriptions reported 2% + 0.99% + GST | Clearest published subscription pricing; supports UPI AutoPay |
| Cashfree | ~1.75-1.95% reported; promotions mentioned (check eligibility) | UPI AutoPay reported |
| PayU | ~2% domestic, ~3% international/EMI + GST reported; often negotiated | UPI AutoPay not confirmed |

Recommendation: no selection now. When paid features exist, start with Razorpay or Cashfree sandboxes. Unknown: our transaction volume, refund/dispute fees, settlement terms, KYC needs. GST of 18% applies on the gateway fee per one source.

## 014 Import formats and OCR

Bank PDF layouts: propose TWO candidates only after the owner supplies likely pilot users' banks and authorised, sanitised sample layouts. Suggested starting guesses by market presence (not verified for this project's users): State Bank of India and HDFC Bank. Do not claim support without fixtures. Selected layout first: finish and verify the existing one; then documented CSV with manual column mapping, preview, validation and review.

OCR (deferred for the first pilot; scanned documents get a clear unsupported-format message). Options compared:
| Option | Where it runs | Cost (reported) | Accuracy notes |
|---|---|---|---|
| PaddleOCR (Apache 2.0) | Local | Server cost only | Reported ~90-95% on text; weak table extraction; fewer errors than Tesseract on receipts (loose proxy) |
| Tesseract (Apache 2.0) | Local | Server cost only | Weaker layout detection; lower accuracy on receipts than PaddleOCR in one benchmark |
| Cloud (AWS Textract / Google Document AI / Azure Document Intelligence) | Vendor infrastructure | ~USD 1-1.5 per 1,000 pages basic; tables/forms cost more | Better table handling reported; documents leave our infrastructure |

Recommendation: if OCR is added, test a LOCAL engine first on synthetic statements; do not send documents to any external service until privacy, retention and consent are approved. Unknown: accuracy on Indian bank statements (no public benchmark found), table-extraction quality, cost of engineering and review.
