import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import HEALTH_AGENT_PROMPT
from rag.rag_pipeline import build_health_context
from engines.financial_health_engine import FinancialHealthEngine


@traceable(
    run_type = "chain",
    name     = "health_agent",
    tags     = ["agent", "health"]
)
def run_health_agent(profile: dict) -> dict:
    """
    Calculate financial health score and provide advice.
    Traced in LangSmith under health_agent.
    """

    # Engine calculates all metrics
    engine        = FinancialHealthEngine()
    engine_result = engine.calculate(profile)
    improvements  = engine.get_improvement_suggestions(profile)

    metrics     = engine_result["raw_metrics"]
    comp_scores = engine_result["component_scores"]
    overall     = engine_result["overall_score"]
    grade       = engine_result["grade"]
    budget      = engine_result["budget_suggestion"]

    context = build_health_context(profile)

    monthly_income   = profile.get("monthly_income",   0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    credit_score     = profile.get("credit_score",     700)
    age              = profile.get("age",              30)
    goals            = profile.get("financial_goals",  [])
    employment       = profile.get("employment_type",  "salaried")
    risk             = profile.get("risk_tolerance",   "moderate")

    user_message = f"""
{context}

=== ENGINE PRE-CALCULATED RESULTS (use these exact numbers) ===

OVERALL SCORE    : {overall}/100
GRADE            : {grade}

COMPONENT SCORES:
- Savings Rate   : {comp_scores['savings_rate']}/25   — current {metrics['savings_rate']:.1f}% — benchmark 20%+
- Emergency Fund : {comp_scores['emergency_fund']}/25  — current {metrics['emergency_months']:.1f} months — benchmark 6 months
- Debt Ratio     : {comp_scores['debt_ratio']}/25      — current {metrics['dti_ratio']:.1f}% — benchmark below 36%
- Investment Rate: {comp_scores['investment_rate']}/15  — current {metrics['investment_rate']:.1f}% — benchmark 20%+
- Credit Score   : {comp_scores['credit_score']}/10    — current {credit_score} — benchmark 750+

RAW METRICS:
- Monthly Surplus  : Rs {metrics['monthly_surplus']:,.0f}
- Emergency Gap    : Rs {metrics['emergency_gap']:,.0f}
- Emergency Needed : Rs {metrics['emergency_needed']:,.0f}

BUDGET SPLIT (50/20/30 India Rule):
- Needs (50%)          : Rs {budget['needs']:,.0f}/month
- Wants (20%)          : Rs {budget['wants']:,.0f}/month
- Savings + Invest(30%): Rs {budget['savings_investments']:,.0f}/month

USER PROFILE:
- Age              : {age}
- Employment       : {employment}
- Risk Tolerance   : {risk}
- Financial Goals  : {goals}
- Monthly Income   : Rs {monthly_income:,.0f}
- Monthly Expenses : Rs {monthly_expenses:,.0f}

PRE-IDENTIFIED IMPROVEMENT AREAS:
{json.dumps([i['area'] for i in improvements], indent=2)}

INSTRUCTIONS:
1. Use the EXACT scores provided — do not recalculate
2. Identify 2 strengths from the highest scoring components
3. Convert improvement areas into detailed advice with rupee amounts
4. Priority actions must be specific with rupee amounts and timelines
5. Budget suggestion must use the 50/20/30 numbers provided above
6. Tone must be encouraging

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = HEALTH_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 2000,
            agent_name    = "health_agent"
        )
        return _parse_response(raw_response, profile, engine_result, improvements, budget)
    except Exception as e:
        fallback = _fallback_response(profile, engine_result, improvements, budget)
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _parse_response(
    raw:           str,
    profile:       dict,
    engine_result: dict,
    improvements:  list,
    budget:        dict
) -> dict:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)

        result = json.loads(cleaned)

        # Always inject engine scores for accuracy
        result["overall_score"]    = engine_result["overall_score"]
        result["grade"]            = engine_result["grade"]
        result["component_scores"] = engine_result["component_scores"]
        return result

    except json.JSONDecodeError:
        return _fallback_response(profile, engine_result, improvements, budget)


def _fallback_response(
    profile:       dict,
    engine_result: dict,
    improvements:  list,
    budget:        dict
) -> dict:
    monthly_income = profile.get("monthly_income",   0)
    credit_score   = profile.get("credit_score",     700)

    overall     = engine_result["overall_score"]
    grade       = engine_result["grade"]
    comp_scores = engine_result["component_scores"]
    metrics     = engine_result["raw_metrics"]
    components  = engine_result["components"]

    strengths = []
    if metrics["savings_rate"]    >= 20: strengths.append(f"Strong savings rate of {metrics['savings_rate']:.1f}%")
    if metrics["emergency_months"] >= 6: strengths.append(f"Emergency fund fully funded at {metrics['emergency_months']:.1f} months")
    if metrics["dti_ratio"]        < 20: strengths.append(f"Excellent debt management — DTI of {metrics['dti_ratio']:.1f}%")
    if credit_score               >= 750: strengths.append(f"Strong credit score of {credit_score}")
    if metrics["investment_rate"]  >= 15: strengths.append(f"Good investment rate of {metrics['investment_rate']:.1f}%")

    if not strengths:
        strengths = [
            "You are tracking your finances — that is the first step",
            "Awareness is the foundation of financial improvement"
        ]

    priority_actions = []
    if metrics["emergency_gap"] > 0:
        priority_actions.append(
            f"Build emergency fund — save Rs {round(metrics['emergency_gap']/12):,.0f}/month "
            f"in liquid fund until Rs {metrics['emergency_gap']:,.0f} gap is filled"
        )
    if metrics["savings_rate"] < 20:
        gap = max(0, round(monthly_income * 0.20) - round(monthly_income - profile.get("monthly_expenses", 0)))
        if gap > 0:
            priority_actions.append(f"Increase savings rate to 20% — reduce spending by Rs {gap:,.0f}/month")
    if metrics["investment_rate"] < 15:
        priority_actions.append(
            f"Start SIP of Rs {round(monthly_income * 0.15):,.0f}/month in Nifty 50 Index Fund + ELSS"
        )
    if credit_score < 750:
        priority_actions.append("Improve credit score to 750+ — pay full credit card outstanding every month")

    if not priority_actions:
        priority_actions = [
            "Continue financial discipline — you are on the right track",
            "Increase SIP by 10% this year",
            "Ensure all investments have proper nominees"
        ]

    return {
        "overall_score":   overall,
        "grade":           grade,
        "components":      components,
        "strengths":       strengths[:2],
        "improvement_areas": improvements[:3],
        "monthly_budget_suggestion": {
            "needs":               budget["needs"],
            "wants":               budget["wants"],
            "savings_investments": budget["savings_investments"],
            "note":                budget["note"]
        },
        "priority_actions": priority_actions[:3],
        "parse_error":      False
    }