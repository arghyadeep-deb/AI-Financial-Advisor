from typing import List, Optional
from rag.kb_loader import (
    get_portfolio_allocation_by_age,
    get_risk_profile_allocation,
    load_systematic_rules
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


class InvestmentEngine:
    """
    Core investment calculation engine.

    Handles:
    - Portfolio allocation calculation
    - SIP future value projections
    - Retirement corpus calculations
    - Goal-based SIP requirements
    - Tax saving calculations
    """

    def __init__(self):
        self.rules = load_systematic_rules()

    # ─── Portfolio Allocation ─────────────────────────────────────────────

    def get_allocation(self, profile: dict) -> dict:
        """
        Get blended portfolio allocation.
        60% weight to age-based + 40% to risk-based.
        """
        age  = profile.get("age", 30)
        risk = profile.get("risk_tolerance", "moderate")

        age_alloc  = get_portfolio_allocation_by_age(age)
        risk_alloc = get_risk_profile_allocation(risk)

        all_keys = set(list(age_alloc.keys()) + list(risk_alloc.keys()))
        blended  = {}

        for key in all_keys:
            age_val = _to_float(age_alloc.get(key))
            risk_val = _to_float(risk_alloc.get(key))

            # Only blend numeric allocation buckets; skip metadata fields.
            if age_val is None and risk_val is None:
                continue

            age_num = age_val if age_val is not None else 0.0
            risk_num = risk_val if risk_val is not None else 0.0
            blended[key] = round((age_num * 0.6) + (risk_num * 0.4), 1)

        # Normalise to 100
        total = sum(blended.values())
        if total != 100 and total > 0:
            diff = 100 - total
            blended["equity"] = round(blended.get("equity", 0) + diff, 1)

        return blended

    # ─── SIP Calculator ───────────────────────────────────────────────────

    def fv_sip(
        self,
        monthly:     float,
        annual_rate: float,
        years:       int
    ) -> int:
        """
        Future value of SIP.
        FV = P × [((1+r)^n - 1) / r] × (1+r)
        """
        if monthly <= 0 or years <= 0:
            return 0
        r  = annual_rate / 12 / 100
        n  = years * 12
        fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)
        return round(fv)

    def fv_lumpsum(
        self,
        principal:   float,
        annual_rate: float,
        years:       int
    ) -> int:
        """
        Future value of lumpsum.
        FV = P × (1 + r)^n
        """
        if principal <= 0 or years <= 0:
            return 0
        return round(principal * ((1 + annual_rate / 100) ** years))

    def required_sip(
        self,
        target:      float,
        existing:    float,
        annual_rate: float,
        years:       int
    ) -> int:
        """
        Required monthly SIP to reach a target.
        Reverse of FV formula.
        """
        if years <= 0:
            return round(target)

        r = annual_rate / 12 / 100
        n = years * 12

        existing_fv      = self.fv_lumpsum(existing, annual_rate, years)
        remaining_target = max(0, target - existing_fv)

        if remaining_target <= 0:
            return 0

        denominator = (((1 + r) ** n - 1) / r) * (1 + r)
        if denominator <= 0:
            return round(remaining_target)

        return round(remaining_target / denominator)

    # ─── Projections ──────────────────────────────────────────────────────

    def project_corpus(
        self,
        monthly:     float,
        annual_rate: float,
        existing:    float,
        years_list:  List[int]
    ) -> dict:
        """
        Project corpus at multiple time horizons.
        Returns dict keyed by years.
        """
        result = {}
        for years in years_list:
            sip_fv     = self.fv_sip(monthly, annual_rate, years)
            lumpsum_fv = self.fv_lumpsum(existing, annual_rate, years)
            result[years] = sip_fv + lumpsum_fv
        return result

    def project_both_trajectories(
        self,
        profile:          dict,
        current_monthly:  float,
        optimized_monthly: float,
        years_list:       List[int] = None
    ) -> dict:
        """
        Project corpus for current vs optimized trajectory.
        Current  → 8% annual return
        Optimized → 11% annual return
        """
        if years_list is None:
            age              = profile.get("age", 30)
            years_to_retire  = max(0, 60 - age)
            years_list       = [5, 10, 20, years_to_retire]

        existing = profile.get("existing_investments", 0)

        current   = self.project_corpus(current_monthly,   8,  existing, years_list)
        optimized = self.project_corpus(optimized_monthly, 11, existing, years_list)

        return {
            "current":   current,
            "optimized": optimized
        }

    # ─── SIP Plan Builder ─────────────────────────────────────────────────

    def build_sip_plan(self, profile: dict, allocation: dict) -> dict:
        """
        Build a complete SIP plan for the user.
        Returns SIP breakdown + total + tax saving plan.
        """
        monthly_income   = profile.get("monthly_income",   0)
        monthly_expenses = profile.get("monthly_expenses", 0)
        existing_savings = profile.get("existing_savings", 0)
        employment       = profile.get("employment_type",  "salaried")
        monthly_surplus  = monthly_income - monthly_expenses

        rules        = self.rules
        sip_rules    = rules.get("sip_rules", {})
        inv_rules    = rules.get("investment_rules", {})

        # ── Emergency Fund Check ──────────────────────────────────────────
        emergency_needed = monthly_expenses * 6
        emergency_gap    = max(0, emergency_needed - existing_savings)
        emergency_monthly = round(emergency_gap / 12) if emergency_gap > 0 else 0

        # ── Available for Investment ──────────────────────────────────────
        investable = max(0, monthly_surplus - emergency_monthly)
        investable = round(investable * 0.90)   # 10% buffer

        equity_pct = allocation.get("equity", 60) / 100
        debt_pct   = allocation.get("debt",   30) / 100
        gold_pct   = allocation.get("gold",   10) / 100

        equity_sip = round(investable * equity_pct)
        debt_sip   = round(investable * debt_pct)
        gold_sip   = round(investable * gold_pct)

        sip_plan = []
        tax_plan = {
            "section_80C":       {"instrument": "", "amount": 0, "remaining_limit": 150000},
            "section_80CCD_1B":  {"instrument": "NPS Tier 1", "amount": 0, "tax_saved": 0},
            "section_80D":       {"instrument": "Health Insurance", "amount": 25000},
            "total_tax_saved_annually": 0
        }

        # ── Tax bracket ───────────────────────────────────────────────────
        tax_bracket = 0.30 if monthly_income > 100000 else 0.20 if monthly_income > 50000 else 0.05
        running_80c = 0

        # ── Equity SIP ────────────────────────────────────────────────────
        if equity_sip > 0:
            elss_amt   = round(min(equity_sip * 0.35, 12500))   # max 1.5L/year
            nifty_amt  = round(equity_sip * 0.40)
            midcap_amt = round(equity_sip * 0.25)

            sip_plan.append({
                "instrument":      "ELSS Fund — Mirae Asset Tax Saver (Direct)",
                "category":        "Equity — Tax Saving",
                "monthly_amount":  elss_amt,
                "rationale":       "80C tax saving with equity returns. 3 year lock-in.",
                "expected_return": "10-12% per annum"
            })
            running_80c += elss_amt * 12

            sip_plan.append({
                "instrument":      "Nifty 50 Index Fund — UTI Direct",
                "category":        "Equity — Large Cap Index",
                "monthly_amount":  nifty_amt,
                "rationale":       "Core equity holding. Low cost. Market returns.",
                "expected_return": "11-13% per annum"
            })

            if midcap_amt >= 500:
                sip_plan.append({
                    "instrument":      "Nifty Midcap 150 Index Fund",
                    "category":        "Equity — Mid Cap",
                    "monthly_amount":  midcap_amt,
                    "rationale":       "Higher growth potential for long term.",
                    "expected_return": "12-15% per annum"
                })

        # ── Debt SIP ──────────────────────────────────────────────────────
        if debt_sip > 0:
            ppf_amt    = round(min(debt_sip * 0.60, 12500))   # max 1.5L/year
            liquid_amt = round(debt_sip * 0.40)

            sip_plan.append({
                "instrument":      "PPF — Public Provident Fund",
                "category":        "Fixed Income — Government",
                "monthly_amount":  ppf_amt,
                "rationale":       "EEE tax treatment. 7.1% guaranteed.",
                "expected_return": "7.1% tax free"
            })
            running_80c += ppf_amt * 12

            if liquid_amt >= 500 and emergency_gap <= 0:
                sip_plan.append({
                    "instrument":      "Parag Parikh Liquid Fund (Direct)",
                    "category":        "Fixed Income — Liquid",
                    "monthly_amount":  liquid_amt,
                    "rationale":       "Better than FD for short term parking.",
                    "expected_return": "6.5-7% per annum"
                })

        # ── NPS (80CCD 1B) ────────────────────────────────────────────────
        if employment == "salaried" and monthly_income > 30000:
            nps_amt = round(min(4167, investable * 0.10))   # 50000/12
            if nps_amt >= 500:
                sip_plan.append({
                    "instrument":      "NPS Tier 1 — LC75 Aggressive",
                    "category":        "Retirement",
                    "monthly_amount":  nps_amt,
                    "rationale":       "Extra Rs 50,000 deduction under 80CCD(1B).",
                    "expected_return": "9-12% per annum"
                })
                nps_annual              = nps_amt * 12
                tax_plan["section_80CCD_1B"]["amount"]    = min(nps_annual, 50000)
                tax_plan["section_80CCD_1B"]["tax_saved"] = round(min(nps_annual, 50000) * tax_bracket)

        # ── Gold SIP ──────────────────────────────────────────────────────
        if gold_sip >= 500:
            sip_plan.append({
                "instrument":      "Sovereign Gold Bonds (SGB)",
                "category":        "Gold",
                "monthly_amount":  gold_sip,
                "rationale":       "2.5% interest + gold appreciation + tax free at maturity.",
                "expected_return": "Gold price + 2.5% per annum"
            })

        # ── Tax Plan ──────────────────────────────────────────────────────
        running_80c  = min(running_80c, 150000)
        tax_plan["section_80C"]["instrument"]      = "ELSS + PPF"
        tax_plan["section_80C"]["amount"]          = round(running_80c)
        tax_plan["section_80C"]["remaining_limit"] = max(0, 150000 - round(running_80c))

        tax_saved_80c   = round(running_80c * tax_bracket)
        tax_saved_nps   = tax_plan["section_80CCD_1B"]["tax_saved"]
        tax_saved_80d   = round(25000 * tax_bracket)

        tax_plan["total_tax_saved_annually"] = tax_saved_80c + tax_saved_nps + tax_saved_80d

        total_sip = sum(s["monthly_amount"] for s in sip_plan)

        return {
            "sip_plan":      sip_plan,
            "total_sip":     total_sip,
            "tax_plan":      tax_plan,
            "emergency_gap": round(emergency_gap),
            "investable":    investable
        }

    # ─── Retirement Calculator ────────────────────────────────────────────

    def retirement_corpus_needed(
        self,
        monthly_expenses: float,
        current_age:      int,
        retirement_age:   int  = 60,
        inflation_rate:   float = 6.0,
        withdrawal_rate:  float = 4.0
    ) -> dict:
        """
        Calculate how much corpus is needed at retirement.

        Uses:
        - Inflation-adjusted future expenses
        - 4% safe withdrawal rate
        """
        years_to_retire    = max(0, retirement_age - current_age)

        # Future monthly expenses adjusted for inflation
        future_monthly     = monthly_expenses * ((1 + inflation_rate / 100) ** years_to_retire)
        future_annual      = future_monthly * 12

        # Corpus needed at 4% withdrawal rate
        corpus_needed      = future_annual / (withdrawal_rate / 100)

        return {
            "years_to_retire":    years_to_retire,
            "future_monthly_exp": round(future_monthly),
            "future_annual_exp":  round(future_annual),
            "corpus_needed":      round(corpus_needed),
            "withdrawal_rate":    withdrawal_rate
        }