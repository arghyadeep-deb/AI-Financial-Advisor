import json
from typing import Optional
from rag.kb_loader import (
    load_credit_cards,
    load_investments,
    load_stocks,
    load_systematic_rules,
    get_portfolio_allocation_by_age,
    get_risk_profile_allocation,
    get_health_benchmarks
)


def _to_float(value) -> Optional[float]:
    """Convert allocation values to float when possible."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


# ─── Credit Card Retriever ────────────────────────────────────────────────────

def retrieve_credit_cards(profile: dict, top_k: int = 5) -> list:
    """
    Filter and rank credit cards based on user profile.
    Considers income eligibility, spend categories, and monthly spend.
    """
    cards              = load_credit_cards()
    monthly_income     = profile.get("monthly_income", 0)
    spend_categories   = [c.lower() for c in profile.get("top_spend_categories", [])]
    credit_spend       = profile.get("monthly_credit_spend", 0)
    annual_credit_spend = credit_spend * 12

    scored = []

    for card in cards:

        score = 0

        # ── Income Eligibility Check ──────────────────────────────────────
        income_req = card.get("income_requirement_monthly", 0)
        if income_req and monthly_income < income_req:
            continue  # User not eligible — skip this card

        # ── Category Match Scoring ────────────────────────────────────────
        best_for = [b.lower() for b in card.get("best_for", [])]

        for user_cat in spend_categories:
            for card_cat in best_for:
                if user_cat in card_cat or card_cat in user_cat:
                    score += 15  # Strong category match

        # ── Annual Fee vs Spend Justification ─────────────────────────────
        annual_fee = card.get("annual_fee", card.get("renewal_fee", 0))

        if annual_credit_spend == 0:
            if annual_fee == 0:
                score += 10   # Free card is always good for no-spenders
        else:
            fee_ratio = annual_fee / annual_credit_spend
            if fee_ratio < 0.01:
                score += 10   # Fee is less than 1% of spend — very justifiable
            elif fee_ratio < 0.02:
                score += 5
            elif fee_ratio > 0.05:
                score -= 5    # Fee too high vs spend

        # ── Lifetime Free Bonus ───────────────────────────────────────────
        fee_waiver = card.get("fee_waiver", "")
        if "lifetime free" in str(fee_waiver).lower():
            score += 8

        # ── Reward Rate Bonus ─────────────────────────────────────────────
        reward = card.get("base_reward_rate", card.get("reward_rate", 0))
        score += reward * 3

        # ── Cashback Bonus ────────────────────────────────────────────────
        cashback = card.get("base_cashback", 0)
        if cashback:
            score += cashback * 2

        # ── Lounge Access Bonus ───────────────────────────────────────────
        lounge = card.get("lounge_access", {})
        if isinstance(lounge, dict):
            lounge_type = lounge.get("type", "")
            if "unlimited" in str(lounge_type).lower():
                score += 8
            elif lounge_type and lounge_type != "None":
                score += 4
        elif isinstance(lounge, str):
            if "unlimited" in lounge.lower():
                score += 8

        # ── High Spend User — Prefer Premium Cards ────────────────────────
        if credit_spend > 100000 and annual_fee >= 10000:
            score += 10
        elif credit_spend > 50000 and annual_fee >= 2500:
            score += 5
        elif credit_spend < 10000 and annual_fee <= 500:
            score += 5

        scored.append((score, card))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [card for _, card in scored[:top_k]]


# ─── Investment Retriever ─────────────────────────────────────────────────────

def retrieve_investments(profile: dict, top_k: int = 6) -> list:
    """
    Filter and rank investment instruments based on
    risk tolerance, investment horizon, and age.
    """
    investments = load_investments()
    risk        = profile.get("risk_tolerance", "moderate").lower()
    horizon     = profile.get("investment_horizon", "long").lower()
    age         = profile.get("age", 30)

    # ── Risk Level Mapping ────────────────────────────────────────────────
    risk_map = {
        "low":      ["very low", "low", "low to medium"],
        "moderate": ["low", "low to medium", "medium", "medium to high"],
        "high":     ["medium", "medium to high", "high"],
        "very_high":["medium to high", "high", "very high", "extremely high"]
    }

    # ── Horizon Mapping ───────────────────────────────────────────────────
    horizon_map = {
        "short":  ["short term", "short to medium term"],
        "medium": ["short to medium term", "medium term", "medium to long term"],
        "long":   ["medium to long term", "long term", "lifetime"]
    }

    allowed_risks    = risk_map.get(risk, risk_map["moderate"])
    allowed_horizons = horizon_map.get(horizon, horizon_map["long"])

    scored = []

    for inv in investments:

        score = 0
        inv_risk    = inv.get("risk_level", "").lower()
        inv_horizon = inv.get("time_horizon", "").lower()

        # ── Risk Match ────────────────────────────────────────────────────
        for ar in allowed_risks:
            if ar in inv_risk:
                score += 10

        # ── Horizon Match ─────────────────────────────────────────────────
        for ah in allowed_horizons:
            if ah in inv_horizon:
                score += 8

        # ── Age Based Priority ────────────────────────────────────────────
        if age < 30:
            # Young investors — prefer equity and growth
            if inv.get("category") == "Equity":
                score += 10
            if inv.get("category") == "Retirement":
                score += 5

        elif age < 45:
            # Mid-age — balance growth and safety
            if inv.get("category") in ["Equity", "Mixed Assets"]:
                score += 8
            if inv.get("category") == "Retirement":
                score += 8

        elif age < 60:
            # Pre-retirement — shift to stability
            if inv.get("category") == "Fixed Income":
                score += 8
            if inv.get("category") == "Retirement":
                score += 10

        else:
            # Retired — prefer income and safety
            if inv.get("category") in ["Fixed Income", "Retirement Income"]:
                score += 15

        # ── Inflation Beating Bonus ───────────────────────────────────────
        if inv.get("inflation_beating") is True:
            score += 3

        # ── High Liquidity Bonus ──────────────────────────────────────────
        liquidity_score = inv.get("liquidity_score", 5)
        if liquidity_score >= 8:
            score += 2

        # ── Skip ULIPs — always bad recommendation ────────────────────────
        if "ulip" in inv.get("name", "").lower():
            score -= 20

        # ── Skip Crypto for low/moderate risk ────────────────────────────
        if "crypto" in inv.get("name", "").lower():
            if risk in ["low", "moderate"]:
                score -= 50  # Effectively remove from results

        if score > 0:
            scored.append((score, inv))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [inv for _, inv in scored[:top_k]]


# ─── Stock Retriever ──────────────────────────────────────────────────────────

def retrieve_stocks(profile: dict, top_k: int = 6) -> list:
    """
    Filter and rank stocks based on risk profile
    and investment style preferences.
    """
    stocks  = load_stocks()
    risk    = profile.get("risk_tolerance", "moderate").lower()
    horizon = profile.get("investment_horizon", "long").lower()

    # ── Risk Level Mapping ────────────────────────────────────────────────
    risk_map = {
        "low":      ["low", "low to medium"],
        "moderate": ["low", "low to medium", "medium"],
        "high":     ["medium", "medium to high", "high"],
        "very_high":["medium", "medium to high", "high", "very high"]
    }

    allowed_risks = risk_map.get(risk, ["medium"])

    scored = []

    for stock in stocks:

        score       = 0
        stock_risk  = stock.get("risk_level", "medium").lower()

        # ── Risk Match ────────────────────────────────────────────────────
        for ar in allowed_risks:
            if ar in stock_risk:
                score += 10

        # ── Growth Score Bonus ────────────────────────────────────────────
        growth_score = stock.get("long_term_growth_score", 5)
        score += growth_score * 2

        # ── Risk Profile Specific Preferences ────────────────────────────
        if risk == "low":
            # Prefer defensive and dividend stocks
            styles = stock.get("investment_style", [])
            if any("defensive" in s.lower() or "dividend" in s.lower()
                   for s in styles):
                score += 10

            # Penalise high growth / speculative
            if any("growth" in s.lower() for s in styles):
                score -= 5

        elif risk == "moderate":
            # Prefer quality and core portfolio
            styles = stock.get("investment_style", [])
            if any("quality" in s.lower() or "core" in s.lower()
                   for s in styles):
                score += 8

        elif risk in ["high", "very_high"]:
            # Prefer high growth scores
            if growth_score >= 9:
                score += 10
            # Include index fund always
            if "index" in stock.get("ticker", "").lower():
                score += 5

        # ── Always include index fund ─────────────────────────────────────
        if stock.get("market_cap_category") == "Index":
            score += 15   # Index fund always in recommendations

        # ── Penalise stocks not suitable for short horizon ────────────────
        if horizon == "short":
            if "speculative" in str(stock.get("ideal_holding_period", "")).lower():
                score -= 20

        if score > 0:
            scored.append((score, stock))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [stock for _, stock in scored[:top_k]]


# ─── Portfolio Allocation Retriever ──────────────────────────────────────────

def get_portfolio_allocation(profile: dict) -> dict:
    """
    Return blended portfolio allocation based on
    age AND risk tolerance combined.
    """
    age  = profile.get("age", 30)
    risk = profile.get("risk_tolerance", "moderate").lower()

    age_alloc  = get_portfolio_allocation_by_age(age)
    risk_alloc = get_risk_profile_allocation(risk)

    # ── Blend 60% age-based + 40% risk-based ─────────────────────────────
    all_keys = set(list(age_alloc.keys()) + list(risk_alloc.keys()))
    blended  = {}

    for key in all_keys:
        age_val = _to_float(age_alloc.get(key))
        risk_val = _to_float(risk_alloc.get(key))

        # Blend only numeric allocation buckets; skip descriptive metadata.
        if age_val is None and risk_val is None:
            continue

        age_num = age_val if age_val is not None else 0.0
        risk_num = risk_val if risk_val is not None else 0.0
        blended[key] = round((age_num * 0.6) + (risk_num * 0.4), 1)

    # ── Normalise to 100% ─────────────────────────────────────────────────
    total = sum(blended.values())
    if total != 100 and total > 0:
        diff = 100 - total
        # Add/subtract difference from equity
        blended["equity"] = round(blended.get("equity", 0) + diff, 1)

    return blended


# ─── Financial Health Calculator ──────────────────────────────────────────────

def calculate_health_metrics(profile: dict) -> dict:
    """
    Health metrics for prompt context.

    Delegates to FinancialHealthEngine so there is exactly ONE implementation
    of the score (no divergent copy); an unknown credit score is excluded from
    the score rather than defaulted.
    """
    from engines.financial_health_engine import FinancialHealthEngine
    result = FinancialHealthEngine().calculate(profile)
    raw = result["raw_metrics"]
    return {
        "monthly_surplus":   raw["monthly_surplus"],
        "monthly_shortfall": raw.get("monthly_shortfall", 0),
        "savings_rate":      raw["savings_rate"],
        "emergency_months":  raw["emergency_months"],
        "dti_ratio":         raw["dti_ratio"],
        "investment_rate":   raw["investment_rate"],
        "overall_score":     result["overall_score"],
        "grade":             result["grade"],
        "component_scores":  result["component_scores"],
    }
