import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import CREDIT_AGENT_PROMPT
from rag.rag_pipeline import build_credit_card_context


@traceable(
    run_type = "chain",
    name     = "credit_agent",
    tags     = ["agent", "credit_card"]
)
def run_credit_agent(profile: dict) -> dict:
    """
    Recommend best credit cards for a user.
    Traced in LangSmith under credit_agent.
    """

    context        = build_credit_card_context(profile)
    monthly_income = profile.get("monthly_income",       0)
    credit_spend   = profile.get("monthly_credit_spend", 0)
    categories     = profile.get("top_spend_categories", [])
    credit_score   = profile.get("credit_score",         700)
    employment     = profile.get("employment_type",      "salaried")
    goals          = profile.get("financial_goals",      [])
    age            = profile.get("age",                  30)

    user_message = f"""
{context}

=== TASK ===
Recommend the TOP 3 to 4 credit cards for this user.

USER DETAILS:
- Age                  : {age}
- Monthly Income       : Rs {monthly_income:,.0f}
- Employment Type      : {employment}
- Monthly Credit Spend : Rs {credit_spend:,.0f}
- Annual Credit Spend  : Rs {credit_spend * 12:,.0f}
- Top Spend Categories : {categories}
- Credit Score         : {credit_score}
- Financial Goals      : {goals}

INSTRUCTIONS:
1. Only recommend cards the user is ELIGIBLE for based on monthly income
2. Rank by best Net Reward Yield for their specific spend categories
3. Calculate realistic estimated annual savings for each card
4. Mention any relevant 2025-2026 devaluations for recommended cards
5. Give a clear strategy note on how to use cards together
6. List 2 pitfalls to avoid

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = CREDIT_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 2000,
            agent_name    = "credit_agent"
        )
        return _parse_response(raw_response, profile)
    except Exception as e:
        fallback = _fallback_response("", profile)
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _parse_response(raw: str, profile: dict) -> dict:
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    except json.JSONDecodeError:
        return _fallback_response(raw, profile)


def _fallback_response(raw: str, profile: dict) -> dict:
    from rag.retriever import retrieve_credit_cards
    top_cards       = retrieve_credit_cards(profile, top_k=3)
    recommendations = []

    for i, card in enumerate(top_cards):
        annual_fee = card.get("annual_fee", card.get("renewal_fee", 0))
        recommendations.append({
            "rank":                     i + 1,
            "card_name":                card.get("card_name", ""),
            "bank":                     card.get("bank", ""),
            "annual_fee":               annual_fee,
            "why_recommended":          f"Best match for your spending in {card.get('best_for', [])}",
            "key_benefits":             card.get("pros", [])[:3],
            "estimated_annual_savings": 0,
            "watch_out":                card.get("cons", ["Check terms and conditions"])[0],
            "eligibility":              "eligible"
        })

    return {
        "recommendations": recommendations,
        "strategy_note":   raw[:500] if raw else "Please retry the analysis.",
        "avoid_pitfalls": [
            "Always pay full outstanding every month to avoid 42-49% interest",
            "Check reward expiry — most points expire in 24 months"
        ],
        "parse_error": True
    }