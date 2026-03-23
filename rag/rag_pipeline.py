import json
from rag.retriever import (
    retrieve_credit_cards,
    retrieve_investments,
    retrieve_stocks,
    get_portfolio_allocation,
    calculate_health_metrics
)
from rag.kb_loader import (
    load_systematic_rules,
    get_credit_card_rules,
    get_investment_rules,
    get_budget_rules,
    get_common_mistakes
)


# ─── Credit Card Context Builder ─────────────────────────────────────────────

def build_credit_card_context(profile: dict) -> str:
    """
    Build full context string for credit card agent.
    Includes eligible cards + rules + user spend pattern.
    """
    cards        = retrieve_credit_cards(profile, top_k=6)
    cc_rules     = get_credit_card_rules()
    monthly_income = profile.get("monthly_income", 0)
    credit_spend   = profile.get("monthly_credit_spend", 0)
    categories     = profile.get("top_spend_categories", [])

    # ── Format Cards ─────────────────────────────────────────────────────
    cards_json = json.dumps(cards, indent=2)

    # ── Key Rules Summary ─────────────────────────────────────────────────
    fees     = cc_rules.get("fees_and_charges", {})
    interest = cc_rules.get("interest_rates", {})
    rewards  = cc_rules.get("reward_rules", {})
    lounge   = cc_rules.get("lounge_access_rules", {})
    forex    = cc_rules.get("forex_rules", {})

    context = f"""
=== USER FINANCIAL PROFILE ===
Monthly Income       : Rs {monthly_income:,.0f}
Monthly Credit Spend : Rs {credit_spend:,.0f}
Annual Credit Spend  : Rs {credit_spend * 12:,.0f}
Top Spend Categories : {categories}

=== ELIGIBLE CREDIT CARDS (Pre-filtered for income Rs {monthly_income:,.0f}/month) ===
{cards_json}

=== CREDIT CARD RULES AND CHARGES ===
Redemption Fee       : Rs {fees.get('redemption_fee', {}).get('amount', 99)} + GST per event
Forex Markup Avg     : {forex.get('average_markup_percent', 3.5)}%
APR Range            : {interest.get('apr_range_percent', {}).get('minimum', 42)}% to {interest.get('apr_range_percent', {}).get('maximum', 49.36)}%
DCC Fee              : {fees.get('dcc_fee_percent', {}).get('rate', 1)}% on international INR transactions
Rent Payment Fee     : {fees.get('rent_payment_fee_percent', {}).get('rate', 1)}%
Late Payment Max     : Rs {cc_rules.get('late_payment_penalties', {}).get('maximum_penalty', 1300)}

=== 2025-2026 KEY DEVALUATIONS TO MENTION ===
{json.dumps(rewards.get('devaluations_2025_2026', []), indent=2)}

=== LOUNGE ACCESS INSIGHT ===
{lounge.get('unused_percent_statistic', 45)}% of cardholders never use lounge access.
Spend unlock range: Rs {lounge.get('spend_unlock_range', {}).get('minimum', 5000)} to Rs {lounge.get('spend_unlock_range', {}).get('maximum', 75000)}

=== NRY FORMULA ===
Net Reward Yield = (Sum of CategorySpend x RewardRate) - AnnualFee / TotalAnnualSpend
Use this to calculate actual return for user's spending pattern.
"""
    return context


# ─── Investment Context Builder ───────────────────────────────────────────────

def build_investment_context(profile: dict) -> str:
    """
    Build full context string for investment agent.
    Includes recommended instruments + allocation + rules.
    """
    investments    = retrieve_investments(profile, top_k=7)
    allocation     = get_portfolio_allocation(profile)
    inv_rules      = get_investment_rules()
    rules          = load_systematic_rules()
    budget_rules   = get_budget_rules()

    monthly_income   = profile.get("monthly_income", 0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    existing_savings = profile.get("existing_savings", 0)
    existing_invest  = profile.get("existing_investments", 0)
    existing_debts   = profile.get("existing_debts", 0)
    age              = profile.get("age", 30)
    risk             = profile.get("risk_tolerance", "moderate")
    horizon          = profile.get("investment_horizon", "long")
    goals            = profile.get("financial_goals", [])
    employment       = profile.get("employment_type", "salaried")

    monthly_surplus   = monthly_income - monthly_expenses
    emergency_needed  = monthly_expenses * inv_rules.get("recommended_emergency_fund_months", 6)
    emergency_gap     = max(0, emergency_needed - existing_savings)

    sip_rules  = rules.get("sip_rules", {})
    min_sip    = monthly_income * sip_rules.get("minimum_sip_percent_income", 10) / 100
    rec_sip    = monthly_income * sip_rules.get("recommended_sip_percent_income", 20) / 100
    agg_sip    = monthly_income * sip_rules.get("aggressive_sip_percent_income", 30) / 100

    investments_json = json.dumps(investments, indent=2)
    allocation_json  = json.dumps(allocation, indent=2)

    context = f"""
=== USER FINANCIAL PROFILE ===
Age                  : {age}
Employment           : {employment}
Risk Tolerance       : {risk}
Investment Horizon   : {horizon}
Financial Goals      : {goals}

=== KEY NUMBERS ===
Monthly Income       : Rs {monthly_income:,.0f}
Monthly Expenses     : Rs {monthly_expenses:,.0f}
Monthly Surplus      : Rs {monthly_surplus:,.0f}
Existing Savings     : Rs {existing_savings:,.0f}
Existing Investments : Rs {existing_invest:,.0f}
Existing Debts       : Rs {existing_debts:,.0f}

=== EMERGENCY FUND STATUS ===
Required (6 months expenses) : Rs {emergency_needed:,.0f}
Current Savings              : Rs {existing_savings:,.0f}
Gap to Fill                  : Rs {emergency_gap:,.0f}
Action Required              : {"YES - Build emergency fund first" if emergency_gap > 0 else "NO - Emergency fund is adequate"}

=== RECOMMENDED PORTFOLIO ALLOCATION ===
(Blended: 60% age-based + 40% risk-based for Age {age}, Risk {risk})
{allocation_json}

=== SIP TARGETS ===
Minimum SIP (10% income)     : Rs {min_sip:,.0f}/month
Recommended SIP (20% income) : Rs {rec_sip:,.0f}/month
Aggressive SIP (30% income)  : Rs {agg_sip:,.0f}/month
Available for Investment      : Rs {monthly_surplus:,.0f}/month

=== RECOMMENDED INVESTMENT INSTRUMENTS ===
(Pre-filtered for risk={risk}, horizon={horizon}, age={age})
{investments_json}

=== INVESTMENT RULES ===
Max single stock allocation  : {inv_rules.get('max_single_stock_allocation_percent', 10)}%
Max sector allocation        : {inv_rules.get('max_sector_percent', 25)}%
Max crypto allocation        : {inv_rules.get('max_crypto_allocation_percent', 5)}%
Max alternative investments  : {inv_rules.get('max_alternative_investment_percent', 10)}%

=== TAX SAVING OPPORTUNITIES ===
Section 80C limit            : Rs 1,50,000 (ELSS, PPF, EPF principal)
Section 80CCD(1B) NPS        : Additional Rs 50,000 over 80C limit
Section 80D health insurance : Rs 25,000 (self+family), Rs 50,000 (senior citizens)
LTCG equity threshold        : Rs 1,25,000 per year tax free
"""
    return context


# ─── Stock Context Builder ────────────────────────────────────────────────────

def build_stock_context(profile: dict) -> str:
    """
    Build full context string for stock agent.
    Includes recommended stocks + allocation rules.
    """
    stocks         = retrieve_stocks(profile, top_k=8)
    allocation     = get_portfolio_allocation(profile)
    inv_rules      = get_investment_rules()

    monthly_income   = profile.get("monthly_income", 0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    monthly_surplus  = monthly_income - monthly_expenses
    existing_invest  = profile.get("existing_investments", 0)
    risk             = profile.get("risk_tolerance", "moderate")
    horizon          = profile.get("investment_horizon", "long")
    goals            = profile.get("financial_goals", [])

    equity_percent = allocation.get("equity", 60)
    equity_amount  = existing_invest * equity_percent / 100

    stocks_json = json.dumps(stocks, indent=2)

    context = f"""
=== USER STOCK INVESTMENT PROFILE ===
Risk Tolerance       : {risk}
Investment Horizon   : {horizon}
Financial Goals      : {goals}
Monthly Surplus      : Rs {monthly_surplus:,.0f}
Existing Investments : Rs {existing_invest:,.0f}
Equity Allocation    : {equity_percent}% = Rs {equity_amount:,.0f}

=== RECOMMENDED STOCKS AND ETFS ===
(Pre-filtered for risk={risk}, horizon={horizon})
{stocks_json}

=== STOCK INVESTMENT RULES ===
Max single stock     : {inv_rules.get('max_single_stock_allocation_percent', 10)}% of equity portfolio
Max single sector    : 25% of equity portfolio
Min stocks for diversification : 15 stocks
Always include       : At least 1 Nifty 50 index fund as core holding

=== PORTFOLIO CONSTRUCTION GUIDANCE ===
Core Holdings (50-60%)  : Nifty 50 Index Fund + Large Cap Quality Stocks
Satellite Holdings (30%): Mid Cap Funds or Stocks
International (10-20%)  : US S&P 500 ETF or Nasdaq 100 ETF
Gold (5-10%)            : Sovereign Gold Bonds preferred

=== LTCG TAX RULES ===
Short Term (under 1 year) : 20% tax on gains
Long Term (over 1 year)   : 12.5% on gains above Rs 1,25,000 per year
Strategy                  : Hold stocks minimum 1 year to get LTCG benefit
Annual LTCG Harvesting    : Book Rs 1,25,000 profit every year to use tax free limit

=== DISCLAIMER ===
Stocks are subject to market risk.
Past performance does not guarantee future returns.
Please consult a SEBI registered investment advisor before investing.
"""
    return context


# ─── Financial Health Context Builder ────────────────────────────────────────

def build_health_context(profile: dict) -> str:
    """
    Build full context string for health agent.
    Includes pre-calculated metrics + benchmarks.
    """
    metrics        = calculate_health_metrics(profile)
    rules          = load_systematic_rules()
    benchmarks     = rules.get("financial_health_benchmarks", {})
    budget_rules   = get_budget_rules()
    mistakes       = get_common_mistakes()

    monthly_income   = profile.get("monthly_income", 0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    age              = profile.get("age", 30)
    goals            = profile.get("financial_goals", [])
    employment       = profile.get("employment_type", "salaried")

    # ── Budget Split (50/30/20) ───────────────────────────────────────────
    needs_target       = monthly_income * 0.50
    wants_target       = monthly_income * 0.20
    savings_target     = monthly_income * 0.30

    context = f"""
=== USER FINANCIAL DATA ===
Age                  : {age}
Employment           : {employment}
Monthly Income       : Rs {monthly_income:,.0f}
Monthly Expenses     : Rs {monthly_expenses:,.0f}
Existing Savings     : Rs {profile.get('existing_savings', 0):,.0f}
Existing Investments : Rs {profile.get('existing_investments', 0):,.0f}
Existing Debts       : Rs {profile.get('existing_debts', 0):,.0f}
Credit Score         : {profile.get('credit_score', 'unknown')}
Risk Tolerance       : {profile.get('risk_tolerance', 'moderate')}
Financial Goals      : {goals}

=== PRE-CALCULATED HEALTH METRICS ===
Monthly Surplus      : Rs {metrics['monthly_surplus']:,.0f}
Savings Rate         : {metrics['savings_rate']:.1f}%
Emergency Fund       : {metrics['emergency_months']:.1f} months
Debt to Income Ratio : {metrics['dti_ratio']:.1f}%
Investment Rate      : {metrics['investment_rate']:.1f}%
Preliminary Score    : {metrics['overall_score']}/100
Grade                : {metrics['grade']}

=== COMPONENT SCORES (use these as base) ===
Savings Rate Score   : {metrics['component_scores']['savings_rate']}/25
Emergency Fund Score : {metrics['component_scores']['emergency_fund']}/25
Debt Ratio Score     : {metrics['component_scores']['debt_ratio']}/25
Investment Rate Score: {metrics['component_scores']['investment_rate']}/15
Credit Score Score   : {metrics['component_scores']['credit_score']}/10

=== BENCHMARKS ===
Savings Rate         : Poor <10% | Average 10-19% | Good 20-29% | Excellent 30%+
Emergency Fund       : Poor <1 month | Average 1-3 | Good 3-6 | Excellent 6+ months
Debt to Income       : Excellent <20% | Good 20-35% | Average 36-49% | Poor 50%+
Investment Rate      : Poor <10% | Average 10-14% | Good 15-19% | Excellent 20%+
Credit Score         : Poor <650 | Average 650-699 | Good 700-749 | Excellent 750+

=== SUGGESTED BUDGET (50/20/30 India Rule) ===
Needs (50%)          : Rs {needs_target:,.0f}/month
Wants (20%)          : Rs {wants_target:,.0f}/month
Savings+Invest (30%) : Rs {savings_target:,.0f}/month

=== COMMON MISTAKES TO CHECK AGAINST ===
{json.dumps([m['mistake'] for m in mistakes[:5]], indent=2)}
"""
    return context


# ─── Summary Context Builder ──────────────────────────────────────────────────

def build_summary_context(
    profile: dict,
    health_result: dict,
    investment_result: dict,
    credit_result: dict,
    stock_result: dict
) -> str:
    """
    Build context for summary agent by combining
    outputs from all other agents.
    """
    monthly_income   = profile.get("monthly_income", 0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    monthly_surplus  = monthly_income - monthly_expenses

    health_score = health_result.get("overall_score", 0)
    health_grade = health_result.get("grade", "N/A")

    top_card = ""
    if credit_result.get("recommendations"):
        top_card = credit_result["recommendations"][0].get("card_name", "")

    portfolio_alloc   = investment_result.get("portfolio_allocation", {})
    total_monthly_sip = investment_result.get("total_monthly_investment", 0)
    corpus_5yr        = investment_result.get("projected_corpus_5yr", 0)
    corpus_10yr       = investment_result.get("projected_corpus_10yr", 0)

    context = f"""
=== USER SUMMARY ===
Age              : {profile.get('age')}
Monthly Income   : Rs {monthly_income:,.0f}
Monthly Surplus  : Rs {monthly_surplus:,.0f}
Risk Tolerance   : {profile.get('risk_tolerance')}
Goals            : {profile.get('financial_goals', [])}

=== HEALTH AGENT OUTPUT ===
Overall Score    : {health_score}/100
Grade            : {health_grade}
Strengths        : {health_result.get('strengths', [])}
Improvement Areas: {[a.get('area', '') for a in health_result.get('improvement_areas', [])]}
Priority Actions : {health_result.get('priority_actions', [])}

=== INVESTMENT AGENT OUTPUT ===
Portfolio Alloc  : {json.dumps(portfolio_alloc)}
Total Monthly SIP: Rs {total_monthly_sip:,.0f}
5 Year Corpus    : Rs {corpus_5yr:,.0f}
10 Year Corpus   : Rs {corpus_10yr:,.0f}
Key Advice       : {investment_result.get('key_advice', '')}

=== CREDIT AGENT OUTPUT ===
Top Card         : {top_card}
Strategy Note    : {credit_result.get('strategy_note', '')}
Avoid Pitfalls   : {credit_result.get('avoid_pitfalls', [])}

=== STOCK AGENT OUTPUT ===
Strategy         : {stock_result.get('portfolio_strategy', '')}
SIP vs Lumpsum   : {stock_result.get('sip_vs_lumpsum', '')}

=== INSTRUCTIONS FOR SUMMARY ===
Synthesize all the above into a clear executive summary.
Be specific with rupee amounts.
Give top 3 priority actions the user should take immediately.
Be encouraging but honest.
All amounts in Indian Rupees.
"""
    return context