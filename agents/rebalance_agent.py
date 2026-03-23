import json
from langsmith import traceable
from utils.llm_brain import call_llm
from intelligence.system_prompts import REBALANCE_AGENT_PROMPT
from rag.retriever import get_portfolio_allocation


@traceable(
    run_type = "chain",
    name     = "rebalance_agent",
    tags     = ["agent", "rebalance"]
)
def run_rebalance_agent(
    profile:          dict,
    investment_result: dict
) -> dict:
    """
    Suggest portfolio rebalancing actions.
    Traced in LangSmith under rebalance_agent.
    """

    existing_invest = profile.get("existing_investments", 0)
    risk            = profile.get("risk_tolerance", "moderate")
    age             = profile.get("age", 30)

    current_alloc   = investment_result.get("portfolio_allocation", {})
    total_sip       = investment_result.get("total_monthly_investment", 0)
    sip_plan        = investment_result.get("monthly_sip_plan", [])
    target_alloc    = get_portfolio_allocation(profile)

    drift_analysis    = _calculate_drift(current_alloc, target_alloc, existing_invest)
    needs_rebalancing = any(abs(d["drift_numeric"]) >= 5 for d in drift_analysis)
    method = "redirect_sips" if existing_invest < 50000 else "combination"
    method_note = (
        "Portfolio under Rs 50,000 — redirect SIPs only. Do not sell."
        if existing_invest < 50000 else
        "Redirect new SIPs first. Sell overweight assets only if drift exceeds 10%."
    )

    user_message = f"""
=== USER PORTFOLIO DATA ===
Age                    : {age}
Risk Tolerance         : {risk}
Total Portfolio Value  : Rs {existing_invest:,.0f}
Monthly SIP            : Rs {total_sip:,.0f}

=== CURRENT ALLOCATION ===
{json.dumps(current_alloc, indent=2)}

=== TARGET ALLOCATION ===
{json.dumps(target_alloc, indent=2)}

=== DRIFT ANALYSIS ===
{json.dumps(drift_analysis, indent=2)}

=== METHOD ===
Method : {method}
Note   : {method_note}

=== CURRENT SIP PLAN ===
{json.dumps([{"instrument": s.get("instrument",""), "monthly": s.get("monthly_amount",0)} for s in sip_plan], indent=2)}

RULES:
1. Portfolio under Rs 50,000 — redirect SIPs only, NO selling
2. Selling triggers capital gains — mention this
3. STCG under 1 year: 20% | LTCG over 1 year equity: 12.5% above Rs 1.25 lakh
4. Prefer redirecting SIPs first
5. Only suggest selling if drift above 10% and portfolio above Rs 1 lakh
6. If already balanced (drift under 5%) — say so clearly

Respond in valid JSON only. No extra text. No markdown.
"""

    try:
        raw_response = call_llm(
            system_prompt = REBALANCE_AGENT_PROMPT,
            user_message  = user_message,
            max_tokens    = 1000,
            agent_name    = "rebalance_agent"
        )
        return _parse_response(
            raw_response, drift_analysis, needs_rebalancing,
            method, current_alloc, target_alloc,
            existing_invest, total_sip, sip_plan
        )
    except Exception as e:
        fallback = _fallback_response(
            drift_analysis, needs_rebalancing, method,
            current_alloc, target_alloc, existing_invest, total_sip, sip_plan
        )
        fallback["llm_error"] = str(e)
        fallback["fallback_used"] = True
        return fallback


def _calculate_drift(current_alloc, target_alloc, portfolio_value):
    all_assets = set(list(current_alloc.keys()) + list(target_alloc.keys()))
    drift_list = []
    for asset in all_assets:
        current_pct = current_alloc.get(asset, 0)
        target_pct  = target_alloc.get(asset, 0)
        drift       = current_pct - target_pct
        drift_list.append({
            "asset_class":        asset,
            "current_percent":    current_pct,
            "target_percent":     target_pct,
            "drift":              f"{drift:+.1f}%",
            "drift_numeric":      drift,
            "drift_amount_rupees":round(portfolio_value * abs(drift) / 100),
            "action":             "reduce" if drift > 0 else "increase" if drift < 0 else "hold"
        })
    return drift_list


def _parse_response(raw, drift_analysis, needs_rebalancing,
                    method, current_alloc, target_alloc,
                    portfolio_value, total_sip, sip_plan):
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            lines   = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_response(
            drift_analysis, needs_rebalancing, method,
            current_alloc, target_alloc, portfolio_value, total_sip, sip_plan
        )


def _fallback_response(drift_analysis, needs_rebalancing, method,
                       current_alloc, target_alloc, portfolio_value,
                       total_sip, sip_plan):
    if not needs_rebalancing:
        return {
            "needs_rebalancing":   False,
            "drift_analysis":      drift_analysis,
            "rebalancing_method":  "none_needed",
            "rebalancing_actions": [],
            "tax_impact":          "No selling required — no tax impact",
            "next_rebalance_date": "12 months",
            "summary":             "Portfolio is well balanced. Review again in 12 months.",
            "parse_error":         False
        }

    overweight  = [d for d in drift_analysis if d["drift_numeric"] > 5]
    underweight = [d for d in drift_analysis if d["drift_numeric"] < -5]
    actions     = []

    for asset in underweight:
        to_instrument = {
            "debt": "Parag Parikh Liquid Fund or PPF",
            "gold": "Sovereign Gold Bonds or Gold ETF"
        }.get(asset["asset_class"], "Nifty 50 Index Fund")

        monthly_redirect = round(min(total_sip * 0.3, asset["drift_amount_rupees"] / 12))
        if monthly_redirect > 0:
            actions.append({
                "action":          "Redirect SIP",
                "from_instrument": f"{overweight[0]['asset_class']} SIP" if overweight else "existing SIP",
                "to_instrument":   to_instrument,
                "amount_monthly":  monthly_redirect,
                "reason":          f"{asset['asset_class']} is {abs(asset['drift_numeric']):.1f}% underweight"
            })

    if portfolio_value >= 100000:
        for asset in overweight:
            if abs(asset["drift_numeric"]) >= 10:
                actions.append({
                    "action":          "Consider Partial Sell",
                    "from_instrument": f"{asset['asset_class'].capitalize()} funds",
                    "to_instrument":   "Underweight asset class",
                    "amount_lumpsum":  round(asset["drift_amount_rupees"] * 0.5),
                    "reason":          f"{asset['asset_class']} is {asset['drift_numeric']:+.1f}% overweight"
                })

    tax_impact = (
        "No selling required — zero tax impact. Redirect future SIPs."
        if method == "redirect_sips" else
        "Selling equity under 1 year: 20% STCG. Over 1 year: 12.5% LTCG above Rs 1.25 lakh. Sell older holdings first."
    )

    overweight_names  = [d["asset_class"] for d in overweight]
    underweight_names = [d["asset_class"] for d in underweight]
    summary = ""
    if overweight_names:  summary += f"{', '.join(overweight_names)} is above target. "
    if underweight_names: summary += f"{', '.join(underweight_names)} needs topping up. "
    summary += f"Method: {method.replace('_', ' ')}. Review in 12 months."

    return {
        "needs_rebalancing":   needs_rebalancing,
        "drift_analysis":      drift_analysis,
        "rebalancing_method":  method,
        "rebalancing_actions": actions,
        "tax_impact":          tax_impact,
        "next_rebalance_date": "12 months",
        "summary":             summary,
        "parse_error":         False
    }