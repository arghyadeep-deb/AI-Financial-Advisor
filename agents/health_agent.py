import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import HEALTH_AGENT_PROMPT
from rag.rag_pipeline import build_health_context
from engines.financial_health_engine import FinancialHealthEngine


def _generate_detailed_warnings(profile: dict, engine_result: dict) -> list:
    """Generate structured warning payloads for expandable frontend display."""
    warnings = []

    raw            = engine_result.get("raw_metrics", {})
    monthly_income = profile.get("monthly_income", 0)
    monthly_exp    = profile.get("monthly_expenses", 0)
    existing_sav   = profile.get("existing_savings", 0)
    existing_debt  = profile.get("existing_debts", 0)
    credit_score   = profile.get("credit_score", 700)
    age            = profile.get("age", 30)

    savings_rate     = raw.get("savings_rate", 0)
    emergency_months = raw.get("emergency_months", 0)
    dti_ratio        = raw.get("dti_ratio", 0)
    investment_rate  = raw.get("investment_rate", 0)
    emergency_gap    = raw.get("emergency_gap", 0)

    if emergency_months < 1:
        warnings.append({
            "title": "No Emergency Fund",
            "severity": "critical",
            "summary": "You have less than 1 month of expenses saved.",
            "detail": (
                f"Your current savings cover only {emergency_months:.1f} months of expenses. "
                f"The recommended minimum is 6 months (Rs {monthly_exp * 6:,.0f}). "
                "Without this buffer, any unexpected expense can force you to take expensive debt "
                "or liquidate long-term investments at the wrong time."
            ),
            "impact": (
                f"A sudden Rs {monthly_exp * 2:,.0f} expense may push you toward debt costing "
                "12-24% annual interest."
            ),
            "action_steps": [
                "Open a liquid fund dedicated to emergencies.",
                f"Set auto-transfer of Rs {round(monthly_exp * 0.5):,.0f}/month.",
                f"Target Rs {round(monthly_exp * 6):,.0f} over 12 months.",
                "Pause aggressive equity investing until emergency cushion is ready."
            ],
            "timeline": "Immediate"
        })
    elif emergency_months < 3:
        warnings.append({
            "title": "Emergency Fund Below 3 Months",
            "severity": "high",
            "summary": f"Only {emergency_months:.1f} months covered; target is 6 months.",
            "detail": (
                f"You currently have Rs {existing_sav:,.0f} saved, which covers {emergency_months:.1f} months. "
                f"You need another Rs {emergency_gap:,.0f} to reach the 6-month benchmark. "
                "This gap increases stress and may derail SIP continuity during volatility."
            ),
            "impact": "Insufficient emergency reserve is a common reason for breaking SIPs during downturns.",
            "action_steps": [
                f"Add Rs {round(emergency_gap / 12):,.0f}/month to emergency corpus.",
                "Keep this amount in low-risk, high-liquidity instruments.",
                "Do not mix emergency money with regular spending account."
            ],
            "timeline": "Within 3 months"
        })

    if savings_rate < 5:
        warnings.append({
            "title": "Critically Low Savings Rate",
            "severity": "critical",
            "summary": f"You are saving only {savings_rate:.1f}% of income.",
            "detail": (
                f"Your monthly surplus is Rs {monthly_income - monthly_exp:,.0f}, which is below healthy levels. "
                "A long-term wealth plan generally needs at least 20% savings rate."
            ),
            "impact": "At this pace, retirement and long-term goals may be delayed significantly.",
            "action_steps": [
                "Audit all recurring subscriptions and discretionary spend.",
                "Track expenses for 30 days to identify leaks.",
                f"Target an immediate expense reduction of Rs {round(monthly_income * 0.05):,.0f}/month.",
                "Set an automatic transfer to savings on salary day."
            ],
            "timeline": "Immediate"
        })
    elif savings_rate < 10:
        warnings.append({
            "title": "Low Savings Rate",
            "severity": "medium",
            "summary": f"Savings are {savings_rate:.1f}% against a 20%+ target.",
            "detail": (
                f"Current savings of Rs {monthly_income - monthly_exp:,.0f}/month can be improved. "
                f"Reaching 20% (Rs {round(monthly_income * 0.20):,.0f}/month) will materially improve future corpus."
            ),
            "impact": "Even small savings-rate improvements compound strongly over 10+ years.",
            "action_steps": [
                "Cut 2-3 non-essential spend categories.",
                f"Increase SIP by Rs {round(monthly_income * 0.05):,.0f}/month.",
                "Follow a needs-wants-savings monthly cap."
            ],
            "timeline": "Within 1 month"
        })

    if dti_ratio > 50:
        warnings.append({
            "title": "Dangerously High Debt Ratio",
            "severity": "critical",
            "summary": f"Debt-to-income ratio is {dti_ratio:.1f}%.",
            "detail": (
                f"Existing debt of Rs {existing_debt:,.0f} is high versus annual income. "
                "At this level, EMI burden can crowd out savings and investment capacity."
            ),
            "impact": (
                f"At 14% interest, this debt can cost around Rs {round(existing_debt * 0.14):,.0f}/year in interest alone."
            ),
            "action_steps": [
                "List all loans by interest rate.",
                "Repay highest-interest debt first.",
                "Avoid new personal loans until DTI is below 36%.",
                "Use bonuses/windfalls for part prepayment."
            ],
            "timeline": "Immediate priority"
        })
    elif dti_ratio > 36:
        warnings.append({
            "title": "Elevated Debt Ratio",
            "severity": "medium",
            "summary": f"DTI is {dti_ratio:.1f}%; safe range is below 36%.",
            "detail": "Debt is manageable but high enough to constrain new goal-based investing.",
            "impact": "High DTI can reduce loan eligibility and increase borrowing costs.",
            "action_steps": [
                "Avoid adding new debt for 12 months.",
                "Make occasional lump-sum prepayments.",
                "Target DTI below 36% over 12-18 months."
            ],
            "timeline": "12-18 months"
        })

    if credit_score < 650:
        warnings.append({
            "title": "Low Credit Score",
            "severity": "critical",
            "summary": f"Credit score is {credit_score}, below 650.",
            "detail": (
                "This score can lead to lower approval odds and higher borrowing rates for major loans."
            ),
            "impact": "A higher interest rate over long tenures can increase total repayment substantially.",
            "action_steps": [
                "Pay all card dues in full and on time.",
                "Keep utilization below 30%.",
                "Check credit report for errors and disputes.",
                "Avoid new credit applications for 6 months."
            ],
            "timeline": "6-12 months"
        })
    elif credit_score < 700:
        warnings.append({
            "title": "Below Average Credit Score",
            "severity": "medium",
            "summary": f"Credit score is {credit_score}; target 750+.",
            "detail": "Score is serviceable but not optimal for the best lending terms.",
            "impact": "Improving score can reduce borrowing costs and improve card/loan offers.",
            "action_steps": [
                "Pay statement balances in full each month.",
                "Maintain low utilization.",
                "Monitor report and correct inaccuracies."
            ],
            "timeline": "6-9 months"
        })

    if investment_rate < 5 and age < 50:
        warnings.append({
            "title": "Not Investing Meaningfully Yet",
            "severity": "medium",
            "summary": "Investment rate is below 5% of income.",
            "detail": (
                f"At age {age}, delaying investments reduces the compounding runway significantly. "
                "Starting with a smaller SIP now is usually better than waiting to invest more later."
            ),
            "impact": "Late starts can require much higher monthly amounts to reach the same target corpus.",
            "action_steps": [
                "Start with a basic index-fund SIP.",
                f"Set a starting SIP near Rs {round(monthly_income * 0.10):,.0f}/month.",
                "Automate debit on salary date."
            ],
            "timeline": "This week"
        })

    return warnings


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
        result["overall_score"]      = engine_result["overall_score"]
        result["grade"]              = engine_result["grade"]
        result["component_scores"]   = engine_result["component_scores"]
        result["components"]         = engine_result.get("components", {})
        result["raw_metrics"]        = engine_result.get("raw_metrics", {})
        result["detailed_warnings"]  = _generate_detailed_warnings(profile, engine_result)
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
        "raw_metrics":     metrics,
        "strengths":       strengths[:2],
        "improvement_areas": improvements[:3],
        "monthly_budget_suggestion": {
            "needs":               budget["needs"],
            "wants":               budget["wants"],
            "savings_investments": budget["savings_investments"],
            "note":                budget["note"]
        },
        "priority_actions": priority_actions[:3],
        "detailed_warnings": _generate_detailed_warnings(profile, engine_result),
        "parse_error":      False
    }