import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import SUMMARY_AGENT_PROMPT
from rag.rag_pipeline import build_summary_context


@traceable(
    run_type = "chain",
    name     = "summary_agent",
    tags     = ["agent", "summary"]
)
def run_summary_agent(profile: dict, all_results: dict) -> dict:
    """
    Synthesize all agent outputs into executive summary.
    Traced in LangSmith under summary_agent.
    """

    health_result     = all_results.get("health",     {})
    investment_result = all_results.get("investment", {})
    credit_result     = all_results.get("credit",     {})

    context = build_summary_context(
        profile           = profile,
        health_result     = health_result,
        investment_result = investment_result,
        credit_result     = credit_result,
        stock_result      = {}
    )

    monthly_income   = profile.get("monthly_income",   0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    monthly_surplus  = monthly_income - monthly_expenses
    goals            = profile.get("financial_goals",  [])

    health_score  = health_result.get("overall_score", 0)
    health_grade  = health_result.get("grade",         "N/A")
    total_sip     = investment_result.get("total_monthly_investment", 0)
    corpus_5yr    = investment_result.get("projected_corpus_5yr",     0)
    corpus_10yr   = investment_result.get("projected_corpus_10yr",    0)
    corpus_20yr   = investment_result.get("projected_corpus_20yr",    0)
    tax_saved     = investment_result.get("tax_saving_plan", {}).get("total_tax_saved_annually", 0)
    emergency_gap = investment_result.get("emergency_fund_status", {}).get("gap_amount", 0)

    top_card = ""
    if credit_result.get("recommendations"):
        top_card = credit_result["recommendations"][0].get("card_name", "")

    user_message = f"""
{context}

=== TASK ===
Create a final executive summary synthesizing all agent outputs.

USER OVERVIEW:
- Age             : {profile.get('age')}
- Monthly Income  : Rs {monthly_income:,.0f}
- Monthly Surplus : Rs {monthly_surplus:,.0f}
- Risk Tolerance  : {profile.get('risk_tolerance')}
- Goals           : {goals}

HEALTH SUMMARY:
- Score           : {health_score}/100 (Grade: {health_grade})
- Strengths       : {health_result.get('strengths', [])}
- Improvements    : {[a.get('area', '') for a in health_result.get('improvement_areas', [])]}
- Priority Actions: {health_result.get('priority_actions', [])}

INVESTMENT SUMMARY:
- Monthly SIP     : Rs {total_sip:,.0f}
- 5yr Corpus      : Rs {corpus_5yr:,.0f}
- 10yr Corpus     : Rs {corpus_10yr:,.0f}
- 20yr Corpus     : Rs {corpus_20yr:,.0f}
- Annual Tax Saved: Rs {tax_saved:,.0f}
- Emergency Gap   : Rs {emergency_gap:,.0f}

CREDIT SUMMARY:
- Top Card        : {top_card}
- Strategy        : {credit_result.get('strategy_note', '')}

INSTRUCTIONS:
1. Executive summary must mention health score, top investment action, best credit card
2. Top 3 priorities must be specific with rupee amounts
3. Quick wins must be achievable within 30 days
4. Personalized message must reference user goals: {goals}
5. Tone must be encouraging

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = SUMMARY_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 1500,
            agent_name    = "summary_agent"
        )
        return _parse_response(
            raw_response, profile, health_result, investment_result, credit_result
        )
    except Exception as e:
        fallback = _fallback_response(profile, health_result, investment_result, credit_result)
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _parse_response(raw, profile, health_result, investment_result, credit_result):
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_response(profile, health_result, investment_result, credit_result)


def _fallback_response(profile, health_result, investment_result, credit_result):
    monthly_income   = profile.get("monthly_income",   0)
    monthly_expenses = profile.get("monthly_expenses", 0)
    monthly_surplus  = monthly_income - monthly_expenses
    goals            = profile.get("financial_goals",  [])

    health_score  = health_result.get("overall_score", 0)
    health_grade  = health_result.get("grade",         "N/A")
    total_sip     = investment_result.get("total_monthly_investment", 0)
    corpus_10yr   = investment_result.get("projected_corpus_10yr",   0)
    corpus_20yr   = investment_result.get("projected_corpus_20yr",   0)
    tax_saved     = investment_result.get("tax_saving_plan", {}).get("total_tax_saved_annually", 0)
    emergency_gap = investment_result.get("emergency_fund_status",   {}).get("gap_amount", 0)
    h_priorities  = health_result.get("priority_actions", [])

    top_card = ""
    if credit_result.get("recommendations"):
        top_card = credit_result["recommendations"][0].get("card_name", "")

    grade_text = {
        "A+": "excellent", "A": "very strong", "B+": "good",
        "B": "decent",     "C": "average",     "D": "needs improvement"
    }.get(health_grade, "developing")

    exec_summary = (
        f"Your financial health score is {health_score}/100 ({health_grade}) — {grade_text}. "
        f"With Rs {monthly_surplus:,.0f} monthly surplus, invest Rs {total_sip:,.0f}/month "
        f"to build Rs {corpus_10yr:,.0f} in 10 years. "
    )
    if top_card:
        exec_summary += f"Best credit card for your spending: {top_card}. "
    if tax_saved > 0:
        exec_summary += f"Save Rs {tax_saved:,.0f} annually in taxes with proper planning."

    top_priorities = []
    if emergency_gap > 0:
        top_priorities.append({
            "priority": 1,
            "action":   f"Build emergency fund — save Rs {round(emergency_gap/12):,.0f}/month until Rs {emergency_gap:,.0f} gap is filled",
            "timeline": "immediate",
            "impact":   "high"
        })
    for i, action in enumerate(h_priorities[:2], start=len(top_priorities) + 1):
        top_priorities.append({
            "priority": i,
            "action":   action,
            "timeline": "1 month",
            "impact":   "high"
        })
    if total_sip > 0 and len(top_priorities) < 3:
        top_priorities.append({
            "priority": len(top_priorities) + 1,
            "action":   f"Start monthly SIP of Rs {total_sip:,.0f} — set up auto-debit on salary date",
            "timeline": "this week",
            "impact":   "high"
        })
    while len(top_priorities) < 3:
        top_priorities.append({
            "priority": len(top_priorities) + 1,
            "action":   "Update nominees on all investments and insurance policies",
            "timeline": "1 month",
            "impact":   "medium"
        })

    quick_wins = []
    if top_card:
        quick_wins.append(f"Apply for {top_card} — start earning rewards immediately")
    quick_wins.append("Switch mutual funds to DIRECT plans on MF Central — saves 1% annually")
    quick_wins.append("Set up auto-pay for credit card full outstanding — avoid 42-49% interest")

    goals_text = f"Your goal of {goals[0]} is achievable — " if goals else ""
    if health_score >= 70:
        message = f"{goals_text}you have built a solid financial foundation. Stay consistent."
    elif health_score >= 50:
        message = f"{goals_text}you are on the right path. Focus on the top 3 priorities."
    else:
        message = "Every journey starts with awareness. Small consistent actions create big results."

    return {
        "executive_summary":    exec_summary,
        "health_score":         health_score,
        "grade":                health_grade,
        "top_priorities":       top_priorities[:3],
        "quick_wins":           quick_wins[:3],
        "key_numbers": {
            "monthly_surplus":       monthly_surplus,
            "recommended_sip":       total_sip,
            "emergency_fund_gap":    emergency_gap,
            "best_credit_card":      top_card,
            "annual_tax_saving":     tax_saved,
            "projected_corpus_10yr": corpus_10yr
        },
        "next_review_date":     "3 months",
        "personalized_message": message,
        "parse_error":          False
    }