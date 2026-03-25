import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import INVESTMENT_AGENT_PROMPT
from rag.rag_pipeline import build_investment_context, build_stock_context
from engines.investment_engine import InvestmentEngine
from engines.risk_engine import RiskEngine


def _normalize_risk(risk_tolerance: str) -> str:
    risk = str(risk_tolerance or "moderate").lower().strip()
    aliases = {
        "conservative": "low",
        "very low": "low",
        "aggressive": "high",
        "very aggressive": "very_high"
    }
    return aliases.get(risk, risk if risk in {"low", "moderate", "high", "very_high"} else "moderate")


def _determine_stock_strategy(age: int, risk_category: str, horizon: str) -> dict:
    """Build an age, risk, and horizon-aware stock strategy."""
    risk = _normalize_risk(risk_category)
    hz   = str(horizon or "long").lower().strip()

    if age <= 25:
        age_group = "early_career"
    elif age <= 35:
        age_group = "growth_phase"
    elif age <= 45:
        age_group = "mid_career"
    elif age <= 55:
        age_group = "pre_retirement"
    else:
        age_group = "near_retirement"

    strategies = {
        "early_career": {
            "index_allocation": 30,
            "midcap_allocation": 40,
            "max_stocks": 5,
            "smallcap_allowed": True,
            "holding_period": "7-10 years",
            "approach": "Long runway allows higher growth tilt."
        },
        "growth_phase": {
            "index_allocation": 40,
            "midcap_allocation": 30,
            "max_stocks": 5,
            "smallcap_allowed": True,
            "holding_period": "5-7 years",
            "approach": "Balance compounding with quality large caps."
        },
        "mid_career": {
            "index_allocation": 50,
            "midcap_allocation": 20,
            "max_stocks": 4,
            "smallcap_allowed": False,
            "holding_period": "5-7 years",
            "approach": "Shift toward quality and stability as retirement gets closer."
        },
        "pre_retirement": {
            "index_allocation": 70,
            "midcap_allocation": 0,
            "max_stocks": 3,
            "smallcap_allowed": False,
            "holding_period": "3-5 years",
            "approach": "Capital preservation and income become top priorities."
        },
        "near_retirement": {
            "index_allocation": 80,
            "midcap_allocation": 0,
            "max_stocks": 3,
            "smallcap_allowed": False,
            "holding_period": "2-4 years",
            "approach": "Defensive equity allocation with limited stock concentration."
        }
    }

    base = strategies[age_group].copy()

    if risk in {"low"} and age_group in {"early_career", "growth_phase"}:
        base["index_allocation"] = min(80, base["index_allocation"] + 20)
        base["midcap_allocation"] = max(0, base["midcap_allocation"] - 20)
        base["smallcap_allowed"] = False
        base["approach"] += " Reduced risk exposure due to low risk tolerance."

    if risk in {"high", "very_high"} and age_group in {"mid_career", "pre_retirement"}:
        base["midcap_allocation"] = min(20, base["midcap_allocation"] + 10)
        base["approach"] += " Slight growth tilt maintained for higher risk tolerance."

    if hz == "short":
        base["smallcap_allowed"] = False
        base["midcap_allocation"] = 0
        base["index_allocation"] = min(90, base["index_allocation"] + 20)
        base["holding_period"] = "1-3 years"
        base["approach"] += " Short horizon prioritizes index-heavy allocation."
    elif hz == "medium":
        base["smallcap_allowed"] = False
        base["holding_period"] = "3-5 years"

    base["age_group"] = age_group
    base["risk_category"] = risk
    base["horizon"] = hz
    base["strategy_note"] = (
        f"Age {age} ({age_group.replace('_', ' ')}), risk {risk}, horizon {hz}: "
        f"{base['index_allocation']}% core index, {base['midcap_allocation']}% midcap, "
        f"rest in selected stocks. {base['approach']}"
    )
    return base


def _fallback_stocks(risk_tolerance: str, age: int, allocation: dict, horizon: str = "long") -> list:
    """Deterministic age-aware stock baskets to avoid one-size-fits-all output."""
    risk = _normalize_risk(risk_tolerance)
    hz   = str(horizon or "long").lower().strip()
    strategy = _determine_stock_strategy(age=age, risk_category=risk, horizon=hz)

    if age >= 55:
        return [
            {
                "company": "Nifty 50 Index Fund",
                "symbol": "NIFTY50_INDEX",
                "sector": "Diversified Index",
                "allocation_percent": 80,
                "investment_style": "Index, Defensive",
                "why_now": "At this age, capital preservation and broad diversification are priorities.",
                "ideal_holding_period": "3-5 years"
            },
            {
                "company": "Power Grid Corporation",
                "symbol": "POWERGRID",
                "sector": "Utilities",
                "allocation_percent": 10,
                "investment_style": "Dividend, Defensive",
                "why_now": "Stable cash flows and dividend orientation support pre-retirement income goals.",
                "ideal_holding_period": "3-5 years"
            },
            {
                "company": "ITC Limited",
                "symbol": "ITC",
                "sector": "FMCG",
                "allocation_percent": 10,
                "investment_style": "Dividend, Defensive",
                "why_now": "Defensive business mix and steady dividends fit low-volatility goals.",
                "ideal_holding_period": "3-5 years"
            }
        ]

    if age >= 45:
        return [
            {
                "company": "Nifty 50 Index Fund",
                "symbol": "NIFTY50_INDEX",
                "sector": "Diversified Index",
                "allocation_percent": 60 if hz != "short" else 80,
                "investment_style": "Index, Core",
                "why_now": "Core market exposure with lower stock-specific risk.",
                "ideal_holding_period": strategy["holding_period"]
            },
            {
                "company": "HDFC Bank",
                "symbol": "HDFCBANK",
                "sector": "Banking",
                "allocation_percent": 15 if hz != "short" else 10,
                "investment_style": "Quality, Core",
                "why_now": "Large-cap quality stock with long track record.",
                "ideal_holding_period": "5 years"
            },
            {
                "company": "Asian Paints",
                "symbol": "ASIANPAINT",
                "sector": "Consumer",
                "allocation_percent": 15 if hz != "short" else 5,
                "investment_style": "Quality, Defensive",
                "why_now": "Steady demand profile and defensive characteristics.",
                "ideal_holding_period": "5 years"
            },
            {
                "company": "ITC Limited",
                "symbol": "ITC",
                "sector": "FMCG",
                "allocation_percent": 10 if hz != "short" else 5,
                "investment_style": "Dividend",
                "why_now": "Income support through dividends with defensive business profile.",
                "ideal_holding_period": "3-5 years"
            }
        ]

    if age >= 35:
        return [
            {
                "company": "Nifty 50 Index Fund",
                "symbol": "NIFTY50_INDEX",
                "sector": "Diversified Index",
                "allocation_percent": 50 if hz == "long" else 65,
                "investment_style": "Index, Core",
                "why_now": "Core long-term compounding base.",
                "ideal_holding_period": strategy["holding_period"]
            },
            {
                "company": "Nifty Next 50 Index Fund",
                "symbol": "NIFTYNEXT50_INDEX",
                "sector": "Large/Mid Index",
                "allocation_percent": 20 if hz == "long" else 10,
                "investment_style": "Index, Growth",
                "why_now": "Adds growth potential above Nifty 50 while keeping diversification.",
                "ideal_holding_period": "5-7 years"
            },
            {
                "company": "HDFC Bank",
                "symbol": "HDFCBANK",
                "sector": "Banking",
                "allocation_percent": 15,
                "investment_style": "Quality, Value",
                "why_now": "Consistent quality large-cap in financials.",
                "ideal_holding_period": "5 years"
            },
            {
                "company": "Infosys",
                "symbol": "INFY",
                "sector": "IT Services",
                "allocation_percent": 15 if hz != "short" else 10,
                "investment_style": "Quality, Dividend",
                "why_now": "Global IT exposure and cash-generative business model.",
                "ideal_holding_period": "5 years"
            }
        ]

    if age >= 25:
        return [
            {
                "company": "Nifty 50 Index Fund",
                "symbol": "NIFTY50_INDEX",
                "sector": "Diversified Index",
                "allocation_percent": 40 if hz == "long" else 70,
                "investment_style": "Index, Core",
                "why_now": "Low-cost core for long-term wealth creation.",
                "ideal_holding_period": strategy["holding_period"]
            },
            {
                "company": "Nifty Midcap 150 Index Fund",
                "symbol": "NIFTYMID150_INDEX",
                "sector": "Midcap Index",
                "allocation_percent": 30 if hz == "long" and risk in {"moderate", "high", "very_high"} else 10,
                "investment_style": "Index, Growth",
                "why_now": "Long horizon allows measured midcap compounding exposure.",
                "ideal_holding_period": "7+ years"
            },
            {
                "company": "Reliance Industries",
                "symbol": "RELIANCE",
                "sector": "Energy/Telecom/Retail",
                "allocation_percent": 15 if hz != "short" else 10,
                "investment_style": "Growth, Core",
                "why_now": "Diversified large-cap growth exposure.",
                "ideal_holding_period": "5-7 years"
            },
            {
                "company": "Infosys",
                "symbol": "INFY",
                "sector": "IT Services",
                "allocation_percent": 15 if hz != "short" else 10,
                "investment_style": "Quality, Dividend",
                "why_now": "Strong cash flow quality growth in IT.",
                "ideal_holding_period": "5 years"
            }
        ]

    return [
        {
            "company": "Nifty 50 Index Fund",
            "symbol": "NIFTY50_INDEX",
            "sector": "Diversified Index",
            "allocation_percent": 30,
            "investment_style": "Index, Core",
            "why_now": "Early start and long runway make index compounding very effective.",
            "ideal_holding_period": "10+ years"
        },
        {
            "company": "Nifty Midcap 150 Index Fund",
            "symbol": "NIFTYMID150_INDEX",
            "sector": "Midcap Index",
            "allocation_percent": 40 if risk in {"moderate", "high", "very_high"} else 20,
            "investment_style": "Index, Growth",
            "why_now": "Higher growth sleeve suited for very long horizon investors.",
            "ideal_holding_period": "10+ years"
        },
        {
            "company": "Parag Parikh Flexi Cap Fund",
            "symbol": "PPFAS",
            "sector": "Flexi Cap",
            "allocation_percent": 20,
            "investment_style": "Growth",
            "why_now": "Diversified managed equity allocation suitable for beginner investors.",
            "ideal_holding_period": "7+ years"
        },
        {
            "company": "HDFC Bank",
            "symbol": "HDFCBANK",
            "sector": "Banking",
            "allocation_percent": 10,
            "investment_style": "Quality, Value",
            "why_now": "Introductory direct stock exposure via a quality large cap.",
            "ideal_holding_period": "5+ years"
        }
    ]


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
    - Differentiate picks by age {age} and horizon {horizon}
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
        age      = profile.get("age", 30)
        risk     = profile.get("risk_tolerance", "moderate")
        horizon  = profile.get("investment_horizon", "long")
        strategy = _determine_stock_strategy(age=age, risk_category=risk, horizon=horizon)

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
        result["stock_recommendations"] = _fallback_stocks(
            risk_tolerance = risk,
            age            = age,
            allocation     = allocation,
            horizon        = horizon
        )
        result["stock_strategy_note"] = strategy["strategy_note"]
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
    horizon          = profile.get("investment_horizon", "long")
    goals            = profile.get("financial_goals", [])
    monthly_expenses = profile.get("monthly_expenses", 0)

    strategy   = _determine_stock_strategy(age=age, risk_category=risk, horizon=horizon)
    stock_recs = _fallback_stocks(
        risk_tolerance = risk,
        age            = age,
        allocation     = allocation,
        horizon        = horizon
    )

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
        "stock_strategy_note":      strategy["strategy_note"],
        "key_advice":               f"At age {age}, start SIP immediately. Step up 10% every year. Target retirement corpus: Rs {retirement['corpus_needed']:,.0f}",
        "disclaimer":               "Stocks are subject to market risk. Please read all scheme related documents carefully.",
        "parse_error":              True
    }