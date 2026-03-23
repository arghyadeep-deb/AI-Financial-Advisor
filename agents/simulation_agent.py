import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import SIMULATION_AGENT_PROMPT


@traceable(
    run_type = "chain",
    name     = "simulation_agent",
    tags     = ["agent", "simulation"]
)
def run_simulation_agent(
    profile:          dict,
    investment_result: dict
) -> dict:
    """
    Run wealth projection simulations.
    Traced in LangSmith under simulation_agent.
    """

    monthly_income   = profile.get("monthly_income",       0)
    monthly_expenses = profile.get("monthly_expenses",     0)
    existing_invest  = profile.get("existing_investments", 0)
    existing_savings = profile.get("existing_savings",     0)
    age              = profile.get("age",                  30)
    risk             = profile.get("risk_tolerance",       "moderate")
    goals            = profile.get("financial_goals",      [])

    monthly_surplus   = monthly_income - monthly_expenses
    years_to_retire   = max(0, 60 - age)
    total_sip         = investment_result.get("total_monthly_investment", 0)
    current_alloc     = investment_result.get("portfolio_allocation",     {})

    current_monthly   = monthly_surplus * 0.5
    optimized_monthly = total_sip if total_sip > 0 else monthly_surplus * 0.8

    current_proj  = _calculate_all_projections(current_monthly,   8,  existing_invest, [5, 10, 20, years_to_retire])
    optimized_proj = _calculate_all_projections(optimized_monthly, 11, existing_invest, [5, 10, 20, years_to_retire])

    goal_analysis = _analyze_goals(goals, monthly_surplus, optimized_monthly, existing_invest)

    user_message = f"""
=== USER FINANCIAL PROFILE ===
Age                    : {age}
Monthly Income         : Rs {monthly_income:,.0f}
Monthly Expenses       : Rs {monthly_expenses:,.0f}
Monthly Surplus        : Rs {monthly_surplus:,.0f}
Existing Investments   : Rs {existing_invest:,.0f}
Existing Savings       : Rs {existing_savings:,.0f}
Risk Tolerance         : {risk}
Financial Goals        : {goals}
Years to Retirement    : {years_to_retire}

=== PRE-CALCULATED PROJECTIONS ===

CURRENT TRAJECTORY (8% return, Rs {current_monthly:,.0f}/month):
- 5yr  : Rs {current_proj[5]:,.0f}
- 10yr : Rs {current_proj[10]:,.0f}
- 20yr : Rs {current_proj[20]:,.0f}
- Retirement: Rs {current_proj[years_to_retire]:,.0f}

OPTIMIZED TRAJECTORY (11% return, Rs {optimized_monthly:,.0f}/month):
- 5yr  : Rs {optimized_proj[5]:,.0f}
- 10yr : Rs {optimized_proj[10]:,.0f}
- 20yr : Rs {optimized_proj[20]:,.0f}
- Retirement: Rs {optimized_proj[years_to_retire]:,.0f}

DIFFERENCE AT 10yr : Rs {optimized_proj[10] - current_proj[10]:,.0f}
DIFFERENCE AT 20yr : Rs {optimized_proj[20] - current_proj[20]:,.0f}

=== GOAL FEASIBILITY ===
{json.dumps(goal_analysis, indent=2)}

INSTRUCTIONS:
1. Use the pre-calculated projections — do not change numbers
2. Key insight must mention the biggest difference between trajectories
3. Be specific with rupee amounts

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = SIMULATION_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 1500,
            agent_name    = "simulation_agent"
        )
        return _parse_response(
            raw_response, current_proj, optimized_proj,
            current_monthly, optimized_monthly,
            years_to_retire, goal_analysis
        )
    except Exception as e:
        fallback = _parse_response(
            "", current_proj, optimized_proj,
            current_monthly, optimized_monthly,
            years_to_retire, goal_analysis
        )
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _fv_sip(monthly, annual_rate, years):
    if monthly <= 0 or years <= 0: return 0
    r  = annual_rate / 12 / 100
    n  = years * 12
    return round(monthly * (((1 + r) ** n - 1) / r) * (1 + r))


def _fv_lumpsum(principal, annual_rate, years):
    if principal <= 0 or years <= 0: return 0
    return round(principal * ((1 + annual_rate / 100) ** years))


def _calculate_all_projections(monthly, rate, existing, years_list):
    result = {}
    for years in years_list:
        if years <= 0:
            result[years] = round(existing)
            continue
        result[years] = _fv_sip(monthly, rate, years) + _fv_lumpsum(existing, rate, years)
    return result


def _analyze_goals(goals, monthly_surplus, optimized_monthly, existing_invest):
    goal_templates = {
        "retirement": {"target_amount": 30000000, "timeline_years": 25},
        "house":      {"target_amount": 5000000,  "timeline_years": 7},
        "car":        {"target_amount": 800000,   "timeline_years": 3},
        "education":  {"target_amount": 3000000,  "timeline_years": 10},
        "wedding":    {"target_amount": 2000000,  "timeline_years": 5},
        "travel":     {"target_amount": 500000,   "timeline_years": 2},
        "business":   {"target_amount": 5000000,  "timeline_years": 5}
    }

    analyzed = []
    for goal in goals:
        goal_lower = goal.lower()
        template   = next(
            (v.copy() for k, v in goal_templates.items() if k in goal_lower),
            {"target_amount": 2000000, "timeline_years": 5}
        )

        target   = template["target_amount"]
        timeline = template["timeline_years"]

        if target <= 0:
            continue

        r        = 11 / 12 / 100
        n        = timeline * 12
        exist_fv = existing_invest * 0.1 * ((1 + r) ** n)
        rem      = max(0, target - exist_fv)
        denom    = (((1 + r) ** n - 1) / r) * (1 + r)
        req_sip  = round(rem / denom) if denom > 0 else round(rem)

        analyzed.append({
            "goal":               goal,
            "target_amount":      target,
            "timeline_years":     timeline,
            "required_monthly_sip": req_sip,
            "current_monthly_sip":  round(optimized_monthly),
            "feasible":           req_sip <= optimized_monthly,
            "gap":                max(0, req_sip - round(optimized_monthly))
        })

    return analyzed


def _parse_response(raw, current_proj, optimized_proj,
                    current_monthly, optimized_monthly,
                    years_to_retire, goal_analysis):
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        diff_10yr = optimized_proj[10] - current_proj[10]
        diff_20yr = optimized_proj[20] - current_proj[20]
        return {
            "current_trajectory": {
                "monthly_investment":    round(current_monthly),
                "annual_return_assumed": "8%",
                "corpus_5yr":            current_proj[5],
                "corpus_10yr":           current_proj[10],
                "corpus_20yr":           current_proj[20],
                "retirement_corpus":     current_proj[years_to_retire]
            },
            "optimized_trajectory": {
                "monthly_investment":    round(optimized_monthly),
                "annual_return_assumed": "11%",
                "corpus_5yr":            optimized_proj[5],
                "corpus_10yr":           optimized_proj[10],
                "corpus_20yr":           optimized_proj[20],
                "retirement_corpus":     optimized_proj[years_to_retire]
            },
            "difference_10yr":  diff_10yr,
            "difference_20yr":  diff_20yr,
            "goal_feasibility": goal_analysis,
            "key_insight": (
                f"By investing Rs {optimized_monthly:,.0f}/month optimally, "
                f"you could build Rs {diff_10yr:,.0f} more in 10 years and "
                f"Rs {diff_20yr:,.0f} more in 20 years."
            ),
            "parse_error": False
        }