import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import OPTIMIZER_AGENT_PROMPT


@traceable(
    run_type = "chain",
    name     = "optimizer_agent",
    tags     = ["agent", "optimizer"]
)
def run_optimizer_agent(
    profile:          dict,
    investment_result: dict,
    health_result:    dict
) -> dict:
    """
    Find portfolio optimization opportunities.
    Traced in LangSmith under optimizer_agent.
    """

    monthly_income   = profile.get("monthly_income",       0)
    monthly_expenses = profile.get("monthly_expenses",     0)
    existing_savings = profile.get("existing_savings",     0)
    existing_invest  = profile.get("existing_investments", 0)
    age              = profile.get("age",                  30)
    risk             = profile.get("risk_tolerance",       "moderate")
    employment       = profile.get("employment_type",      "salaried")
    goals            = profile.get("financial_goals",      [])
    monthly_surplus  = monthly_income - monthly_expenses

    tax_plan      = investment_result.get("tax_saving_plan",      {})
    current_alloc = investment_result.get("portfolio_allocation", {})
    total_sip     = investment_result.get("total_monthly_investment", 0)
    sip_plan      = investment_result.get("monthly_sip_plan",     [])
    health_score  = health_result.get("overall_score",            0)
    improvements  = health_result.get("improvement_areas",        [])

    tax_bracket      = 0.30 if monthly_income > 100000 else 0.20 if monthly_income > 50000 else 0.05
    current_80c      = tax_plan.get("section_80C",      {}).get("amount", 0)
    remaining_80c    = max(0, 150000 - current_80c)
    current_nps      = tax_plan.get("section_80CCD_1B", {}).get("amount", 0)
    remaining_nps    = max(0, 50000 - current_nps)
    potential_80c    = round(remaining_80c * tax_bracket)
    potential_nps    = round(remaining_nps * tax_bracket)
    direct_plan_save = round(existing_invest * 0.01)

    user_message = f"""
=== USER FINANCIAL PROFILE ===
Age                    : {age}
Employment             : {employment}
Monthly Income         : Rs {monthly_income:,.0f}
Monthly Surplus        : Rs {monthly_surplus:,.0f}
Existing Savings       : Rs {existing_savings:,.0f}
Existing Investments   : Rs {existing_invest:,.0f}
Risk Tolerance         : {risk}
Financial Goals        : {goals}

=== CURRENT INVESTMENT PLAN ===
Portfolio Allocation   : {json.dumps(current_alloc)}
Monthly SIP Total      : Rs {total_sip:,.0f}
Health Score           : {health_score}/100

=== TAX SAVING ANALYSIS ===
Tax Bracket            : {int(tax_bracket * 100)}%
Current 80C Used       : Rs {current_80c:,.0f}
80C Remaining Limit    : Rs {remaining_80c:,.0f}
Potential 80C Saving   : Rs {potential_80c:,.0f}
Current NPS (80CCD 1B) : Rs {current_nps:,.0f}
NPS Remaining Limit    : Rs {remaining_nps:,.0f}
Potential NPS Saving   : Rs {potential_nps:,.0f}

=== DIRECT PLAN OPPORTUNITY ===
Existing Investments   : Rs {existing_invest:,.0f}
Estimated Saving       : Rs {direct_plan_save:,.0f}/year (1% expense ratio difference)

=== IMPROVEMENT AREAS ===
{json.dumps([i.get('area', '') for i in improvements], indent=2)}

=== TASK ===
Find all optimization opportunities with specific rupee benefits.

CHECK FOR:
1. 80C gap — fully utilizing Rs 1,50,000 limit?
2. NPS 80CCD(1B) — extra Rs 50,000 deduction?
3. 80D — health insurance for Rs 25,000 deduction?
4. Direct vs regular mutual fund plans
5. FD vs liquid fund
6. Emergency fund in savings vs liquid fund
7. ULIP or endowment plan exit
8. Credit card optimization
9. Portfolio rebalancing
10. SIP step-up

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = OPTIMIZER_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 1500,
            agent_name    = "optimizer_agent"
        )
        return _parse_response(
            raw_response, profile,
            remaining_80c, remaining_nps,
            potential_80c, potential_nps,
            direct_plan_save, current_alloc, investment_result
        )
    except Exception as e:
        fallback = _fallback_response(
            profile, remaining_80c, remaining_nps,
            potential_80c, potential_nps,
            direct_plan_save, current_alloc, investment_result
        )
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _parse_response(raw, profile, remaining_80c, remaining_nps,
                    potential_80c, potential_nps, direct_plan_save,
                    current_alloc, investment_result):
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_response(
            profile, remaining_80c, remaining_nps,
            potential_80c, potential_nps,
            direct_plan_save, current_alloc, investment_result
        )


def _fallback_response(profile, remaining_80c, remaining_nps,
                       potential_80c, potential_nps, direct_plan_save,
                       current_alloc, investment_result):
    monthly_income   = profile.get("monthly_income",   0)
    existing_invest  = profile.get("existing_investments", 0)
    existing_savings = profile.get("existing_savings", 0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    employment       = profile.get("employment_type",  "salaried")
    tax_bracket      = 0.30 if monthly_income > 100000 else 0.20 if monthly_income > 50000 else 0.05

    emergency_needed  = monthly_expenses * 6
    liquid_fund_gain  = round(existing_savings * 0.03)
    opportunities     = []

    if remaining_80c > 0:
        opportunities.append({
            "area":                  "Section 80C Tax Saving",
            "current_state":         f"Rs {150000 - remaining_80c:,.0f} of Rs 1,50,000 used",
            "optimized_state":       f"Invest Rs {remaining_80c:,.0f} more in ELSS or PPF",
            "annual_benefit_rupees": round(potential_80c),
            "complexity":            "easy",
            "steps": [
                f"Start ELSS SIP of Rs {round(remaining_80c/12):,.0f}/month",
                "Or deposit lumpsum in PPF before March 31",
                "Use Mirae Asset Tax Saver or Axis Long Term Equity (Direct)"
            ]
        })

    if remaining_nps > 0 and employment == "salaried":
        opportunities.append({
            "area":                  "NPS Section 80CCD(1B) Extra Deduction",
            "current_state":         f"Rs {50000 - remaining_nps:,.0f} of Rs 50,000 used",
            "optimized_state":       f"Invest Rs {remaining_nps:,.0f} in NPS Tier 1",
            "annual_benefit_rupees": round(potential_nps),
            "complexity":            "easy",
            "steps": [
                "Open NPS at nps.proteantech.in",
                f"Invest Rs {round(remaining_nps/12):,.0f}/month via auto-debit",
                "Choose LC75 lifecycle fund if below 40 years"
            ]
        })

    if monthly_income > 30000:
        opportunities.append({
            "area":                  "Section 80D Health Insurance",
            "current_state":         "Health insurance deduction not accounted for",
            "optimized_state":       "Buy family floater — Rs 25,000 deduction",
            "annual_benefit_rupees": round(25000 * tax_bracket),
            "complexity":            "easy",
            "steps": [
                "Buy 10 lakh family floater health insurance",
                "Compare on PolicyBazaar — Niva Bupa, Star Health",
                "Premium of Rs 15,000-25,000 qualifies for 80D"
            ]
        })

    if existing_invest > 50000:
        opportunities.append({
            "area":                  "Switch to Direct Mutual Fund Plans",
            "current_state":         f"Possible regular plan investments of Rs {existing_invest:,.0f}",
            "optimized_state":       "All in direct plans — saves 0.5-1% annually",
            "annual_benefit_rupees": round(direct_plan_save),
            "complexity":            "easy",
            "steps": [
                "Login to mfcentral.com with your PAN",
                "Check for regular plans and switch to direct",
                "Future SIPs via Zerodha Coin or Groww"
            ]
        })

    if existing_savings > 50000:
        opportunities.append({
            "area":                  "Move Emergency Fund to Liquid Fund",
            "current_state":         f"Rs {existing_savings:,.0f} in savings account at 3.5%",
            "optimized_state":       "Move to liquid fund at 6.5-7%",
            "annual_benefit_rupees": liquid_fund_gain,
            "complexity":            "easy",
            "steps": [
                "Keep 1 month expenses in savings for instant access",
                f"Move Rs {max(0, existing_savings - monthly_expenses):,.0f} to Parag Parikh Liquid Fund",
                "Redemption hits bank in 1 business day"
            ]
        })

    from rag.retriever import get_portfolio_allocation
    target_alloc      = get_portfolio_allocation(profile)
    needs_rebalancing = False
    rebalancing_actions = []

    for asset in ["equity", "debt", "gold"]:
        current_pct = current_alloc.get(asset, 0)
        target_pct  = target_alloc.get(asset, 0)
        if abs(current_pct - target_pct) >= 5:
            needs_rebalancing = True
            direction = "reduce" if current_pct > target_pct else "increase"
            rebalancing_actions.append(
                f"{direction.capitalize()} {asset} from {current_pct}% to {target_pct}%"
            )

    total_benefit = sum(o["annual_benefit_rupees"] for o in opportunities)

    return {
        "optimization_opportunities": opportunities,
        "tax_saving_suggestions": [
            {"section": "80C",      "action": f"Invest Rs {remaining_80c:,.0f} in ELSS/PPF",
             "max_deduction": 150000, "tax_saved_at_30_percent": round(remaining_80c * 0.30)},
            {"section": "80CCD(1B)","action": f"Invest Rs {remaining_nps:,.0f} in NPS Tier 1",
             "max_deduction": 50000,  "tax_saved_at_30_percent": round(remaining_nps * 0.30)},
            {"section": "80D",      "action": "Buy health insurance — Rs 25,000 premium",
             "max_deduction": 25000,  "tax_saved_at_30_percent": 7500}
        ],
        "rebalancing_needed":    needs_rebalancing,
        "rebalancing_actions":   rebalancing_actions,
        "switch_to_direct_plans":existing_invest > 50000,
        "direct_plan_annual_saving": round(direct_plan_save),
        "total_optimization_value":  f"Rs {total_benefit:,.0f} potential annual benefit",
        "parse_error": False
    }