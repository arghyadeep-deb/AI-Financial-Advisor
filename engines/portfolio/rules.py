"""Versioned arithmetic conventions, not a market-data approval."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRules:
    version: str = "portfolio-metrics.v2"
    currency: str = "INR"
    units_decimal_places: int = 8
    monetary_rounding: str = "aggregate half-even to paise; class/issuer largest remainders conserve total"
    concentration_method: str = "issuer HHI over priced subset; unknown issuer separate"


RULES = PortfolioRules()
