import json
import os
from pathlib import Path

# ─── Path Setup ──────────────────────────────────────────────────────────────

KB_DIR = Path(__file__).parent.parent / "knowledge_base"


# ─── Individual Loaders ──────────────────────────────────────────────────────

def load_credit_cards() -> list:
    """Load all credit cards from knowledge base."""
    path = KB_DIR / "credit_cards.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_investments() -> list:
    """Load all investment instruments from knowledge base."""
    path = KB_DIR / "investments.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_stocks() -> list:
    """Load all stocks and ETFs from knowledge base."""
    path = KB_DIR / "stocks.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_systematic_rules() -> dict:
    """Load all systematic rules, benchmarks and formulas."""
    path = KB_DIR / "systematic_rules.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Filtered Loaders ────────────────────────────────────────────────────────

def load_cards_by_bank(bank_name: str) -> list:
    """Return only cards from a specific bank."""
    cards = load_credit_cards()
    return [
        c for c in cards
        if c.get("bank", "").lower() == bank_name.lower()
    ]


def load_cards_by_tier(tier: str) -> list:
    """Return only cards of a specific tier."""
    cards = load_credit_cards()
    return [
        c for c in cards
        if c.get("tier", "").lower() == tier.lower()
    ]


def load_cards_lifetime_free() -> list:
    """Return only lifetime free cards."""
    cards = load_credit_cards()
    return [
        c for c in cards
        if c.get("annual_fee", 999) == 0
    ]


def load_investments_by_category(category: str) -> list:
    """Return investments of a specific category."""
    investments = load_investments()
    return [
        i for i in investments
        if i.get("category", "").lower() == category.lower()
    ]


def load_investments_by_risk(risk_level: str) -> list:
    """Return investments matching a risk level."""
    investments = load_investments()
    risk_lower = risk_level.lower()
    return [
        i for i in investments
        if risk_lower in i.get("risk_level", "").lower()
    ]


def load_stocks_by_risk(risk_level: str) -> list:
    """Return stocks matching a risk profile."""
    stocks = load_stocks()

    risk_map = {
        "low":       ["low", "low to medium"],
        "moderate":  ["low", "low to medium", "medium"],
        "high":      ["medium", "medium to high", "high"],
        "very_high": ["medium", "medium to high", "high", "very high"]
    }

    allowed = risk_map.get(risk_level.lower(), ["medium"])

    return [
        s for s in stocks
        if any(
            r in s.get("risk_level", "").lower()
            for r in allowed
        )
    ]


def load_stocks_by_style(style: str) -> list:
    """Return stocks matching an investment style."""
    stocks = load_stocks()
    style_lower = style.lower()
    return [
        s for s in stocks
        if any(
            style_lower in str(st).lower()
            for st in s.get("investment_style", [])
        )
    ]


# ─── Rules Loaders ───────────────────────────────────────────────────────────

def get_credit_card_rules() -> dict:
    """Return credit card rules section only."""
    rules = load_systematic_rules()
    return rules.get("credit_card_rules", {})


def get_investment_rules() -> dict:
    """Return investment rules section only."""
    rules = load_systematic_rules()
    return rules.get("investment_rules", {})


def get_portfolio_allocation_by_age(age: int) -> dict:
    """Return portfolio allocation for a given age."""
    rules = load_systematic_rules()
    allocations = rules.get("portfolio_allocation_by_age", {})

    if age < 30:
        return allocations.get("20_30", {})
    elif age < 40:
        return allocations.get("30_40", {})
    elif age < 50:
        return allocations.get("40_50", {})
    elif age < 60:
        return allocations.get("50_60", {})
    else:
        return allocations.get("above_60", {})


def get_risk_profile_allocation(risk_tolerance: str) -> dict:
    """Return portfolio allocation for a given risk profile."""
    rules = load_systematic_rules()
    profiles = rules.get("risk_profiles", {})
    return profiles.get(risk_tolerance.lower(), profiles.get("moderate", {}))


def get_health_benchmarks() -> dict:
    """Return financial health benchmark thresholds."""
    rules = load_systematic_rules()
    return rules.get("financial_health_benchmarks", {})


def get_budget_rules() -> dict:
    """Return budgeting rules."""
    rules = load_systematic_rules()
    return rules.get("budget_rules", {})


def get_common_mistakes() -> list:
    """Return common financial mistakes list."""
    rules = load_systematic_rules()
    return rules.get("common_financial_mistakes", [])


# ─── Full Knowledge Dump ─────────────────────────────────────────────────────

def get_all_knowledge() -> dict:
    """Load everything — used for full context injection."""
    return {
        "credit_cards":     load_credit_cards(),
        "investments":      load_investments(),
        "stocks":           load_stocks(),
        "systematic_rules": load_systematic_rules()
    }


# ─── Summary Stats ───────────────────────────────────────────────────────────

def get_knowledge_base_summary() -> dict:
    """Return a summary of what is loaded in the knowledge base."""
    cards       = load_credit_cards()
    investments = load_investments()
    stocks      = load_stocks()

    return {
        "total_credit_cards":  len(cards),
        "total_investments":   len(investments),
        "total_stocks":        len(stocks),
        "banks_covered":       list(set(c.get("bank") for c in cards)),
        "investment_categories": list(set(i.get("category") for i in investments)),
        "stock_sectors":       list(set(s.get("sector") for s in stocks))
    }