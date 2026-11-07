"""Versioned arithmetic conventions, not a market-data approval."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRules:
    version: str = "portfolio-metrics.v1"
    currency: str = "INR"
    units_decimal_places: int = 8
    monetary_rounding: str = "aggregate exact values then half-even to paise"
    concentration_method: str = "issuer HHI over priced subset; unknown issuer separate"


RULES = PortfolioRules()
