from typing import Optional


class RiskEngine:
    """
    Calculates and maps risk profiles.

    Handles:
    - Risk score calculation from profile
    - Risk tolerance mapping
    - Age-based risk adjustment
    - Risk-based instrument filtering
    """

    # ── Risk Score Thresholds ─────────────────────────────────────────────
    RISK_THRESHOLDS = {
        "low":      (0,  30),
        "moderate": (31, 60),
        "high":     (61, 80),
        "very_high":(81, 100)
    }

    def calculate_risk_score(self, profile: dict) -> dict:
        """
        Calculate a numeric risk score (0-100)
        from the user's profile.

        Factors:
        - Age (younger = higher risk capacity)
        - Income stability (salaried = more stable)
        - Debt ratio (lower debt = more risk capacity)
        - Emergency fund (better fund = more risk capacity)
        - Investment horizon (longer = more risk capacity)
        - Declared risk tolerance
        """

        age              = profile.get("age", 30)
        employment       = profile.get("employment_type", "salaried")
        monthly_income   = profile.get("monthly_income", 0)
        monthly_expenses = profile.get("monthly_expenses", 0)
        existing_savings = profile.get("existing_savings", 0)
        existing_debts   = profile.get("existing_debts", 0)
        horizon          = profile.get("investment_horizon", "long")
        declared_risk    = profile.get("risk_tolerance", "moderate")

        score = 0

        # ── Age Factor (0-25 points) ──────────────────────────────────────
        if age < 25:       score += 25
        elif age < 30:     score += 22
        elif age < 35:     score += 20
        elif age < 40:     score += 17
        elif age < 45:     score += 14
        elif age < 50:     score += 11
        elif age < 55:     score += 8
        elif age < 60:     score += 5
        else:              score += 2

        # ── Employment Stability (0-15 points) ───────────────────────────
        employment_scores = {
            "salaried":      15,
            "business":      10,
            "self_employed":  8
        }
        score += employment_scores.get(employment, 8)

        # ── Investment Horizon (0-20 points) ─────────────────────────────
        horizon_scores = {
            "long":   20,
            "medium": 12,
            "short":   5
        }
        score += horizon_scores.get(horizon, 12)

        # ── Emergency Fund (0-15 points) ─────────────────────────────────
        if monthly_expenses > 0:
            emergency_months = existing_savings / monthly_expenses
            if emergency_months >= 6:  score += 15
            elif emergency_months >= 3: score += 10
            elif emergency_months >= 1: score += 5
            else:                       score += 0

        # ── Debt Ratio (0-15 points) ──────────────────────────────────────
        if monthly_income > 0:
            dti = (existing_debts / (monthly_income * 12)) * 100
            if dti < 10:    score += 15
            elif dti < 20:  score += 12
            elif dti < 36:  score += 8
            elif dti < 50:  score += 4
            else:            score += 0

        # ── Declared Risk Tolerance (0-10 points) ────────────────────────
        declared_scores = {
            "very_high": 10,
            "high":       8,
            "moderate":   5,
            "low":        2
        }
        score += declared_scores.get(declared_risk, 5)

        # ── Map score to profile ──────────────────────────────────────────
        calculated_profile = self._score_to_profile(score)

        return {
            "risk_score":           score,
            "calculated_profile":   calculated_profile,
            "declared_profile":     declared_risk,
            "final_profile":        self._blend_profiles(calculated_profile, declared_risk),
            "score_breakdown": {
                "age_score":        min(25, max(0, score - 65)),
                "horizon_score":    horizon_scores.get(horizon, 12),
                "employment_score": employment_scores.get(employment, 8)
            }
        }

    def _score_to_profile(self, score: int) -> str:
        """Map numeric score to risk profile label."""
        for profile_name, (low, high) in self.RISK_THRESHOLDS.items():
            if low <= score <= high:
                return profile_name
        return "moderate"

    def _blend_profiles(
        self,
        calculated: str,
        declared:   str
    ) -> str:
        """
        Blend calculated and declared risk profiles.
        If they disagree by more than one level — use calculated.
        Otherwise — use declared (respect user preference).
        """
        order = ["low", "moderate", "high", "very_high"]

        calc_idx     = order.index(calculated)    if calculated in order else 1
        declared_idx = order.index(declared)      if declared  in order else 1

        diff = abs(calc_idx - declared_idx)

        if diff <= 1:
            return declared       # Trust user's declared preference
        else:
            return calculated     # Override if very different from calculated

    def get_suitable_instruments(self, risk_profile: str) -> dict:
        """
        Return suitable and unsuitable instruments for a risk profile.
        """
        profiles = {
            "low": {
                "suitable": [
                    "PPF", "SCSS", "Bank FD", "RBI Bonds",
                    "Debt Mutual Funds", "Nifty 50 Index Fund (small)"
                ],
                "avoid": [
                    "Small Cap Funds", "Sectoral Funds",
                    "Individual Stocks", "Crypto"
                ],
                "max_equity_percent": 20
            },
            "moderate": {
                "suitable": [
                    "Nifty 50 Index Fund", "Nifty Next 50",
                    "Large Cap Mutual Funds", "Balanced Advantage Funds",
                    "PPF", "NPS", "SGBs"
                ],
                "avoid": [
                    "Heavy Small Cap", "Individual Stock Trading", "Crypto above 2%"
                ],
                "max_equity_percent": 50
            },
            "high": {
                "suitable": [
                    "Nifty 50 + Nifty Next 50", "Mid Cap Funds",
                    "International Index Funds", "Direct Stocks (large cap)",
                    "REITs", "SGBs"
                ],
                "avoid": [
                    "Leveraged Products", "Crypto above 3%"
                ],
                "max_equity_percent": 70
            },
            "very_high": {
                "suitable": [
                    "All equity categories including small cap",
                    "Direct Stock Picking", "International ETFs",
                    "REITs and InvITs", "Bitcoin (small allocation)"
                ],
                "avoid": [
                    "Capital Guaranteed Products", "Annuities"
                ],
                "max_equity_percent": 80
            }
        }

        return profiles.get(risk_profile, profiles["moderate"])