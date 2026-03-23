from typing import Optional
from rag.kb_loader import load_credit_cards, get_credit_card_rules


class RewardEngine:
    """
    Calculates credit card reward yields and
    estimates annual savings for a user's spend pattern.

    Implements the NRY formula:
    NRY = (Sum of CategorySpend × RewardRate) - AnnualFee
          ──────────────────────────────────────────────
                      TotalAnnualSpend
    """

    def __init__(self):
        self.cards = load_credit_cards()
        self.rules = get_credit_card_rules()

    # ─── Net Reward Yield ─────────────────────────────────────────────────

    def calculate_nry(
        self,
        card:             dict,
        monthly_spend:    float,
        spend_categories: list
    ) -> dict:
        """
        Calculate Net Reward Yield for a card
        given the user's monthly spend pattern.
        """

        annual_fee    = card.get("annual_fee", card.get("renewal_fee", 0))
        annual_spend  = monthly_spend * 12
        reward_earned = 0

        if annual_spend <= 0:
            return {
                "nry_percent":          0,
                "annual_reward_earned": 0,
                "annual_fee":           annual_fee,
                "net_savings":          -annual_fee,
                "breakeven_spend":      self._breakeven_spend(card)
            }

        # ── Cashback Cards ────────────────────────────────────────────────
        cashback = card.get("cashback", {})
        if isinstance(cashback, dict) and cashback:
            reward_earned = self._calculate_cashback_reward(
                cashback=cashback,
                monthly_spend=monthly_spend,
                spend_categories=spend_categories,
                monthly_cap=card.get("cashback_cap_monthly", float("inf"))
            )

        # ── Reward Point Cards ────────────────────────────────────────────
        base_rate = card.get("base_reward_rate", card.get("reward_rate", 0))
        if base_rate > 0 and reward_earned == 0:
            reward_earned = monthly_spend * 12 * (base_rate / 100)

        # ── Multiplier Cards ──────────────────────────────────────────────
        multipliers = card.get("multipliers", {})
        if multipliers:
            bonus = self._calculate_multiplier_bonus(
                multipliers=multipliers,
                monthly_spend=monthly_spend,
                spend_categories=spend_categories
            )
            reward_earned += bonus

        # ── UPI Cashback ──────────────────────────────────────────────────
        upi_cashback = card.get("upi_cashback", card.get("upi_reward", 0))
        if upi_cashback > 0:
            upi_spend     = monthly_spend * 0.3   # assume 30% of spend is UPI
            reward_earned += upi_spend * 12 * (upi_cashback / 100)

        # ── Redemption Fee ────────────────────────────────────────────────
        redemption_fee        = self.rules.get("fees_and_charges", {}).get(
            "redemption_fee", {}
        ).get("amount", 99)
        redemption_cost       = 12 * redemption_fee   # assume monthly redemption

        net_savings           = reward_earned - annual_fee - redemption_cost
        nry_percent           = (net_savings / annual_spend * 100) if annual_spend > 0 else 0

        return {
            "nry_percent":          round(nry_percent, 2),
            "annual_reward_earned": round(reward_earned),
            "annual_fee":           annual_fee,
            "redemption_cost":      redemption_cost,
            "net_savings":          round(net_savings),
            "breakeven_spend":      self._breakeven_spend(card)
        }

    def _calculate_cashback_reward(
        self,
        cashback:         dict,
        monthly_spend:    float,
        spend_categories: list,
        monthly_cap:      float
    ) -> float:
        """Calculate cashback earned based on spend categories."""

        categories_lower = [c.lower() for c in spend_categories]
        total_cashback   = 0
        matched_spend    = 0

        for merchant, rate in cashback.items():
            merchant_lower = merchant.lower()

            # Check if user spends in this category
            is_match = any(
                merchant_lower in cat or cat in merchant_lower
                for cat in categories_lower
            )

            if is_match:
                # Assume 40% of spend goes to this category
                category_spend  = monthly_spend * 0.40
                monthly_cashback = category_spend * (rate / 100)
                monthly_cashback = min(monthly_cashback, monthly_cap / len(cashback))
                total_cashback  += monthly_cashback
                matched_spend   += category_spend

        # Base rate on unmatched spend
        unmatched_spend = monthly_spend - matched_spend
        base_cashback   = cashback.get("other", cashback.get("other_spends", 1))
        total_cashback  += unmatched_spend * (base_cashback / 100)

        # Apply monthly cap
        total_cashback = min(total_cashback, monthly_cap)

        return total_cashback * 12   # annualize

    def _calculate_multiplier_bonus(
        self,
        multipliers:      dict,
        monthly_spend:    float,
        spend_categories: list
    ) -> float:
        """Calculate bonus from category multipliers."""

        categories_lower = [c.lower() for c in spend_categories]
        bonus            = 0

        for category, multiplier in multipliers.items():
            cat_lower = category.lower()

            is_match = any(
                cat_lower in cat or cat in cat_lower
                for cat in categories_lower
            )

            if is_match:
                category_spend = monthly_spend * 0.30    # 30% in this category
                # Bonus above base rate (assume base = 1%)
                bonus_rate     = max(0, (multiplier - 1)) / 100
                bonus         += category_spend * 12 * bonus_rate

        return bonus

    def _breakeven_spend(self, card: dict) -> float:
        """
        Calculate minimum monthly spend needed
        to break even on annual fee.
        """
        annual_fee = card.get("annual_fee", card.get("renewal_fee", 0))
        if annual_fee == 0:
            return 0

        base_rate = card.get("base_reward_rate", card.get("reward_rate", 1))
        if base_rate <= 0:
            base_rate = 1

        # Monthly spend needed so annual reward covers annual fee
        annual_spend_needed  = annual_fee / (base_rate / 100)
        monthly_spend_needed = annual_spend_needed / 12

        return round(monthly_spend_needed)

    # ─── Card Comparison ─────────────────────────────────────────────────

    def compare_cards(
        self,
        profile: dict
    ) -> list:
        """
        Compare all eligible cards for a user
        and return ranked by NRY.
        """

        monthly_income   = profile.get("monthly_income",       0)
        monthly_spend    = profile.get("monthly_credit_spend", 0)
        spend_categories = profile.get("top_spend_categories", [])

        compared = []

        for card in self.cards:
            # Check eligibility
            income_req = card.get("income_requirement_monthly", 0)
            if income_req and monthly_income < income_req:
                continue

            nry_data = self.calculate_nry(
                card=card,
                monthly_spend=monthly_spend,
                spend_categories=spend_categories
            )

            compared.append({
                "card_name":    card.get("card_name", ""),
                "bank":         card.get("bank", ""),
                "annual_fee":   card.get("annual_fee", 0),
                "nry_percent":  nry_data["nry_percent"],
                "net_savings":  nry_data["net_savings"],
                "best_for":     card.get("best_for", [])
            })

        # Sort by net savings descending
        compared.sort(key=lambda x: x["net_savings"], reverse=True)

        return compared[:10]

    # ─── Lounge Value Calculator ──────────────────────────────────────────

    def calculate_lounge_value(
        self,
        card:          dict,
        trips_per_year: int = 4
    ) -> float:
        """
        Calculate monetary value of lounge access benefit.
        Average lounge visit = Rs 1,500.
        """
        lounge = card.get("lounge_access", {})

        if not lounge or lounge == "None":
            return 0

        if isinstance(lounge, str) and "unlimited" in lounge.lower():
            # Unlimited — value based on actual trips
            return trips_per_year * 1500

        if isinstance(lounge, dict):
            lounge_type = lounge.get("type", "")

            if "unlimited" in str(lounge_type).lower():
                return trips_per_year * 1500

            domestic    = lounge.get("domestic", 0)
            intl        = lounge.get("international", 0)

            if isinstance(domestic, str):
                domestic = trips_per_year
            if isinstance(intl, str):
                intl = 2

            total_visits = min(int(domestic) + int(intl), trips_per_year * 2)
            return total_visits * 1500

        return 0