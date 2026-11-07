"""Archived FY2024-25 salary-only sandbox pack; no production approval.

Official references checked 2026-11-07. No automatic adjacent-year substitution.
Parameters are immutable; changes require a new version and boundary fixtures.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SalaryRules:
    version: str = "salary-in-fy2024-25-new.v1"
    financial_year: str = "2024-25"
    assessment_year: str = "2025-26"
    regime: str = "new"
    standard_deduction_paise: int = 7500000
    rebate_threshold_paise: int = 70000000
    rebate_maximum_paise: int = 2500000
    cess_bps: int = 400
    # Upper bounds (paise), marginal rates (basis points).
    slabs: tuple = ((30000000, 0), (70000000, 500), (100000000, 1000),
                    (120000000, 1500), (150000000, 2000), (500000000, 3000))
    verified_on: str = "2026-11-07"
    production_approved: bool = False
    sources: tuple = (
        "https://traces61contents.tdscpc.gov.in/en/incometax-2024-2025-new.html",
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2035618&lang=1&reg=6",
        "https://www.incometaxindia.gov.in/w/section-288a-58",
        "https://www.incometaxindia.gov.in/w/section-288b-9",
    )


SALARY_FY2024_25 = SalaryRules()
