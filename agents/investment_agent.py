import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import INVESTMENT_AGENT_PROMPT
from rag.rag_pipeline import build_investment_context, build_stock_context
from rag.retriever import retrieve_stocks
from engines.investment_engine import InvestmentEngine
from engines.risk_engine import RiskEngine


@traceable(
    run_type = "chain",
    name     = "investment_agent",
    tags     = ["agent", "investment"]
)
def run_investment_agent(profile: dict) -> dict:
    """
    Build complete investment plan including stocks.
    Traced in LangSmith under investment_agent.
    """

    # Risk engine
    risk_engine      = RiskEngine()
    risk_result      = risk_engine.calculate_risk_score(profile)
    final_risk       = risk_result["final_profile"]
    enriched_profile = {**profile, "risk_tolerance": final_risk}

    # Investment engine
    inv_engine  = InvestmentEngine()
    allocation  = inv_engine.get_allocation(enriched_profile)
    sip_data    = inv_engine.build_sip_plan(enriched_profile, allocation)

    monthly_income   = profile.get("monthly_income",       0)
    monthly_expenses = profile.get("monthly_expenses",     0)
    existing_invest  = profile.get("existing_investments", 0)
    monthly_surplus  = monthly_income - monthly_expenses

    current_monthly   = monthly_surplus * 0.5
    optimized_monthly = sip_data["total_sip"]

    projections = inv_engine.project_both_trajectories(
        profile            = enriched_profile,
        current_monthly    = current_monthly,
        optimized_monthly  = optimized_monthly,
        years_list         = [5, 10, 20]
    )

    retirement = inv_engine.retirement_corpus_needed(
        monthly_expenses = monthly_expenses,
        current_age      = profile.get("age", 30)
    )

    investment_context = build_investment_context(enriched_profile)
    stock_context      = build_stock_context(enriched_profile)

    age        = profile.get("age",              30)
    horizon    = profile.get("investment_horizon", "long")
    goals      = profile.get("financial_goals",  [])
    employment = profile.get("employment_type",  "salaried")

    optimized_5yr  = projections["optimized"].get(5,  0)
    optimized_10yr = projections["optimized"].get(10, 0)
    optimized_20yr = projections["optimized"].get(20, 0)
    current_5yr    = projections["current"].get(5,  0)
    current_10yr   = projections["current"].get(10, 0)
    current_20yr   = projections["current"].get(20, 0)

    user_message = f"""
{investment_context}

=== STOCK AND ETF UNIVERSE ===
{stock_context}

=== ENGINE PRE-CALCULATED RESULTS ===

RISK PROFILE:
- Declared Risk      : {profile.get('risk_tolerance', 'moderate')}
- Calculated Risk    : {risk_result['calculated_profile']}
- Final Blended Risk : {final_risk}

PORTFOLIO ALLOCATION:
{json.dumps(allocation, indent=2)}

SIP PLAN:
Total Monthly SIP: Rs {sip_data['total_sip']:,.0f}
{json.dumps(sip_data['sip_plan'], indent=2)}

TAX SAVING PLAN:
{json.dumps(sip_data['tax_plan'], indent=2)}

EMERGENCY FUND GAP: Rs {sip_data['emergency_gap']:,.0f}

WEALTH PROJECTIONS:
Current Path (8%, Rs {current_monthly:,.0f}/month):
  5yr: Rs {current_5yr:,.0f} | 10yr: Rs {current_10yr:,.0f} | 20yr: Rs {current_20yr:,.0f}

Optimized Path (11%, Rs {optimized_monthly:,.0f}/month):
  5yr: Rs {optimized_5yr:,.0f} | 10yr: Rs {optimized_10yr:,.0f} | 20yr: Rs {optimized_20yr:,.0f}

RETIREMENT:
- Years to retire    : {retirement['years_to_retire']}
- Corpus needed      : Rs {retirement['corpus_needed']:,.0f}
- Future monthly exp : Rs {retirement['future_monthly_exp']:,.0f}

USER PROFILE:
- Age: {age} | Employment: {employment} | Risk: {final_risk}
- Horizon: {horizon} | Goals: {goals}
- Monthly Income: Rs {monthly_income:,.0f} | Surplus: Rs {monthly_surplus:,.0f}

INSTRUCTIONS:
1. Use the EXACT SIP plan, allocation, and projections from engine
2. Add rationale for each SIP instrument based on user profile
3. Stock section: 4-6 stocks from universe above
   - Always include Nifty 50 Index Fund as core
   - No single stock above 10% allocation
   - Match stocks to risk profile: {final_risk}
4. Use engine corpus projections — do not recalculate
5. Include disclaimer

Respond in the exact JSON format from system prompt.
No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = INVESTMENT_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 3000,
            agent_name    = "investment_agent"
        )

        return _parse_response(
            raw         = raw_response,
            profile     = enriched_profile,
            allocation  = allocation,
            sip_data    = sip_data,
            projections = projections,
            retirement  = retirement,
            inv_engine  = inv_engine
        )
    except Exception as e:
        # Keep analysis available when provider keys are invalid or exhausted.
        fallback = _fallback_response(
            profile     = enriched_profile,
            allocation  = allocation,
            sip_data    = sip_data,
            projections = projections,
            retirement  = retirement
        )
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _parse_response(
    raw:         str,
    profile:     dict,
    allocation:  dict,
    sip_data:    dict,
    projections: dict,
    retirement:  dict,
    inv_engine:  InvestmentEngine
) -> dict:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)

        result = json.loads(cleaned)

        # Always inject engine numbers for accuracy
        result["portfolio_allocation"]     = allocation
        result["total_monthly_investment"] = sip_data["total_sip"]
        result["projected_corpus_5yr"]     = projections["optimized"].get(5,  0)
        result["projected_corpus_10yr"]    = projections["optimized"].get(10, 0)
        result["projected_corpus_20yr"]    = projections["optimized"].get(20, 0)
        result["emergency_fund_status"]    = {
            "current_months": round(
                profile.get("existing_savings", 0) /
                max(profile.get("monthly_expenses", 1), 1), 1
            ),
            "target_months": 6,
            "gap_amount":    sip_data["emergency_gap"],
            "action": "Build emergency fund first" if sip_data["emergency_gap"] > 0
                      else "Emergency fund is adequate"
        }
        if "tax_saving_plan" not in result:
            result["tax_saving_plan"] = sip_data["tax_plan"]

        return result

    except json.JSONDecodeError:
        return _fallback_response(profile, allocation, sip_data, projections, retirement)


def _fallback_response(
    profile:     dict,
    allocation:  dict,
    sip_data:    dict,
    projections: dict,
    retirement:  dict
) -> dict:
    risk             = profile.get("risk_tolerance", "moderate")
    age              = profile.get("age", 30)
    goals            = profile.get("financial_goals", [])
    monthly_expenses = profile.get("monthly_expenses", 0)

    stocks     = retrieve_stocks(profile, top_k=5)
    stock_recs = [{
        "symbol":             s.get("ticker", ""),
        "company":            s.get("company", ""),
        "sector":             s.get("sector", ""),
        "allocation_percent": 10,
        "why_now":            s.get("analyst_view", "Strong long term pick"),
        "ideal_holding_period": s.get("ideal_holding_period", "5-10 years"),
        "investment_style":   ", ".join(s.get("investment_style", []))
    } for s in stocks]

    existing_savings = profile.get("existing_savings", 0)
    emergency_needed = monthly_expenses * 6
    surplus_savings  = max(0, existing_savings - emergency_needed)
    lumpsum          = []

    if surplus_savings > 10000:
        lumpsum = [
            {"instrument": "Nifty 50 Index Fund", "amount": round(surplus_savings * 0.50),
             "rationale": "Deploy surplus into equity for long term growth."},
            {"instrument": "PPF Annual Top-up",   "amount": round(min(surplus_savings * 0.30, 150000)),
             "rationale": "Max out PPF limit before March 31."},
            {"instrument": "Sovereign Gold Bonds","amount": round(surplus_savings * 0.20),
             "rationale": "Tax free gold investment on maturity."}
        ]

    return {
        "portfolio_allocation":     allocation,
        "monthly_sip_plan":         sip_data["sip_plan"],
        "stock_recommendations":    stock_recs,
        "lumpsum_suggestions":      lumpsum,
        "emergency_fund_status": {
            "current_months": round(
                profile.get("existing_savings", 0) / max(monthly_expenses, 1), 1
            ),
            "target_months": 6,
            "gap_amount":    sip_data["emergency_gap"],
            "action": "Build emergency fund first" if sip_data["emergency_gap"] > 0
                      else "Emergency fund adequate"
        },
        "tax_saving_plan":          sip_data["tax_plan"],
        "total_monthly_investment": sip_data["total_sip"],
        "projected_corpus_5yr":     projections["optimized"].get(5,  0),
        "projected_corpus_10yr":    projections["optimized"].get(10, 0),
        "projected_corpus_20yr":    projections["optimized"].get(20, 0),
        "stock_strategy_note":      f"Core: Nifty 50 ETF. Add quality large caps for {risk} risk.",
        "key_advice":               f"At age {age}, start SIP immediately. Step up 10% every year. Target retirement corpus: Rs {retirement['corpus_needed']:,.0f}",
        "disclaimer":               "Stocks are subject to market risk. Please read all scheme related documents carefully.",
        "parse_error":              True
    }