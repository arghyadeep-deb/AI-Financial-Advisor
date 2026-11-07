"""Profile persistence with exact money and revisions (T104 / FR-002, FR-003, F001-FR10, FR11).

* All money is stored as integer paise; the legacy float columns are written
  only here, derived from paise, so they can never diverge (rollback aid).
* Every material change creates an immutable ``ProfileRevision`` and bumps
  ``FinancialProfile.revision`` using a compare-and-swap UPDATE.
* ``to_agent_dict`` and ``snapshot_for`` are the ONLY ways other modules read
  profile money, so API, agents, chat and UI see the same facts.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.core.money import paise_to_float, rupees_to_paise
from backend.models.models import FinancialProfile, ProfileRevision
from engines.cashflow import FinanceSnapshot, build_snapshot

# (request field, paise column)
MONEY_FIELDS: List[Tuple[str, str]] = [
    ("monthly_income",       "monthly_income_paise"),
    ("monthly_expenses",     "monthly_expenses_paise"),
    ("existing_savings",     "existing_savings_paise"),
    ("existing_investments", "existing_investments_paise"),
    ("existing_debts",       "existing_debts_paise"),
    ("monthly_credit_spend", "monthly_credit_spend_paise"),
]
DEBT_PAYMENT = ("monthly_debt_payment", "monthly_debt_payment_paise")
PLAIN_FIELDS = ["age", "employment_type", "risk_tolerance", "investment_horizon",
                "financial_goals", "top_spend_categories"]


class ProfileIncomplete(HTTPException):
    def __init__(self, fields: List[str]):
        super().__init__(
            status_code=422,
            detail={"code": "profile_incomplete",
                    "message": "Some saved profile values could not be verified and need to be re-entered.",
                    "fields": fields},
        )


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _paise(value) -> Optional[int]:
    return None if value is None else rupees_to_paise(value)


def needs_reentry(profile: FinancialProfile) -> List[str]:
    """Required money fields that are unknown (e.g. corrupted legacy values)."""
    return [field for field, col in MONEY_FIELDS if getattr(profile, col) is None]


def revision_snapshot(profile: FinancialProfile) -> Dict[str, Any]:
    """Immutable record of the inputs at this revision (no floats)."""
    data: Dict[str, Any] = {col: getattr(profile, col) for _, col in MONEY_FIELDS}
    data[DEBT_PAYMENT[1]] = getattr(profile, DEBT_PAYMENT[1])
    for f in PLAIN_FIELDS:
        data[f] = getattr(profile, f)
    data["credit_score"] = profile.credit_score
    return data


class ProfileService:

    def __init__(self, db: Session):
        self.db = db

    # ── write ─────────────────────────────────────────────────────────────
    def save(self, user_id: int, data: Dict[str, Any]) -> FinancialProfile:
        """Create or update the saved profile.  ``data`` comes from the
        validated request (Decimal rupees).  Returns the stored row."""
        expected = data.pop("expected_revision", None)
        paise_values: Dict[str, Optional[int]] = {col: _paise(data.get(f)) for f, col in MONEY_FIELDS}
        paise_values[DEBT_PAYMENT[1]] = _paise(data.get(DEBT_PAYMENT[0]))
        plain = {f: data.get(f) for f in PLAIN_FIELDS}
        plain["financial_goals"] = list(plain.get("financial_goals") or [])
        plain["top_spend_categories"] = list(plain.get("top_spend_categories") or [])
        credit = data.get("credit_score")
        legacy = self._legacy_floats(paise_values)

        profile = self.db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()
        now = _now()

        if profile is None:
            profile = FinancialProfile(
                user_id=user_id, revision=1, schema_version=1,
                credit_score=credit, credit_score_source="user" if credit is not None else None,
                **plain, **paise_values, **legacy)
            self.db.add(profile)
            self.db.flush()
            self.db.add(ProfileRevision(user_id=user_id, revision=1, source="user_edit",
                                        snapshot=revision_snapshot(profile), created_at=now))
            self.db.commit()
            self.db.refresh(profile)
            return profile

        if expected is not None and expected != profile.revision:
            raise HTTPException(409, detail={"code": "revision_conflict",
                                             "message": "The profile changed since you loaded it.",
                                             "current_revision": profile.revision})

        before = revision_snapshot(profile)
        candidate = {**paise_values, **plain, "credit_score": credit}
        if all(before.get(k) == v for k, v in candidate.items()):
            return profile                      # nothing changed: no new revision

        old_rev = profile.revision
        values = dict(candidate)
        values.pop("credit_score")
        res = self.db.execute(
            update(FinancialProfile)
            .where(FinancialProfile.id == profile.id, FinancialProfile.revision == old_rev)
            .values(**values, **legacy, credit_score=credit,
                    credit_score_source=("user" if credit is not None else None),
                    revision=old_rev + 1, updated_at=now))
        if res.rowcount != 1:
            self.db.rollback()
            raise HTTPException(409, detail={"code": "revision_conflict",
                                             "message": "The profile was modified concurrently; reload and retry."})
        self.db.expire(profile)
        profile = self.db.get(FinancialProfile, profile.id)
        self.db.add(ProfileRevision(user_id=user_id, revision=old_rev + 1, source="user_edit",
                                    snapshot=revision_snapshot(profile), created_at=now))
        self.db.commit()
        self.db.refresh(profile)
        return profile

    @staticmethod
    def _legacy_floats(paise_values: Dict[str, Optional[int]]) -> Dict[str, Optional[float]]:
        return {f: paise_to_float(paise_values[col]) for f, col in MONEY_FIELDS}

    # ── read ──────────────────────────────────────────────────────────────
    def get(self, user_id: int) -> Optional[FinancialProfile]:
        return self.db.query(FinancialProfile).filter(FinancialProfile.user_id == user_id).first()

    def get_or_raise(self, user_id: int) -> FinancialProfile:
        profile = self.get(user_id)
        if not profile:
            raise HTTPException(status_code=404,
                                detail="Profile not found. Please complete your profile first.")
        return profile


# ── canonical views (used by analysis, chat, UI) ───────────────────────────

def profile_money(profile: FinancialProfile,
                  overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Paise-valued mapping for ``build_snapshot`` with optional scenario overrides
    (Decimal rupees).  Raises ProfileIncomplete when required money is unknown."""
    ov = overrides or {}
    def pick(field: str, col: str):
        if ov.get(field) is not None:
            return rupees_to_paise(ov[field])
        return getattr(profile, col)

    income = pick("monthly_income", "monthly_income_paise")
    expenses = pick("monthly_expenses", "monthly_expenses_paise")
    savings = pick("existing_savings", "existing_savings_paise")
    debts = pick("existing_debts", "existing_debts_paise")
    unknown = [f for f, v in (("monthly_income", income), ("monthly_expenses", expenses),
                              ("existing_savings", savings), ("existing_debts", debts)) if v is None]
    if unknown:      # unknown legacy money is never treated as zero when it drives affordability
        raise ProfileIncomplete(unknown)
    payment = (rupees_to_paise(ov["monthly_debt_payment"]) if ov.get("monthly_debt_payment") is not None
               else profile.monthly_debt_payment_paise)
    return {
        "income_paise": income,
        "expenses_paise": expenses,
        "savings_paise": savings,
        "investments_paise": pick("existing_investments", "existing_investments_paise") or 0,
        "debt_balance_paise": debts,
        "monthly_debt_payment_paise": payment,
        "credit_spend_paise": pick("monthly_credit_spend", "monthly_credit_spend_paise") or 0,
        "credit_score": ov["credit_score"] if "credit_score" in ov else profile.credit_score,
    }


def snapshot_for(profile: FinancialProfile, overrides: Optional[Dict[str, Any]] = None) -> FinanceSnapshot:
    return build_snapshot(profile_money(profile, overrides),
                          owner_id=profile.user_id, profile_revision=profile.revision)


def to_agent_dict(profile: FinancialProfile, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Rupee-valued dict for the legacy agents/engines.  Floats here are for
    narrative/legacy heuristics only; authoritative figures come from the snapshot."""
    ov = overrides or {}
    m = profile_money(profile, ov)
    d = {
        "age": ov.get("age") or profile.age,
        "employment_type": ov.get("employment_type") or profile.employment_type,
        "monthly_income": paise_to_float(m["income_paise"]),
        "monthly_expenses": paise_to_float(m["expenses_paise"]),
        "existing_savings": paise_to_float(m["savings_paise"]),
        "existing_investments": paise_to_float(m["investments_paise"]),
        "existing_debts": paise_to_float(m["debt_balance_paise"]),
        "monthly_debt_payment": paise_to_float(m["monthly_debt_payment_paise"]),
        "risk_tolerance": ov.get("risk_tolerance") or profile.risk_tolerance,
        "investment_horizon": ov.get("investment_horizon") or profile.investment_horizon,
        "financial_goals": ov.get("financial_goals") if ov.get("financial_goals") is not None
                           else (profile.financial_goals or []),
        "credit_score": m["credit_score"],               # None == unknown
        "monthly_credit_spend": paise_to_float(m["credit_spend_paise"]),
        "top_spend_categories": ov.get("top_spend_categories") if ov.get("top_spend_categories") is not None
                                else (profile.top_spend_categories or []),
    }
    return d


def profile_to_response(profile: FinancialProfile) -> Dict[str, Any]:
    """Serialisable response dict including additive exact-money fields."""
    return {
        "id": profile.id, "user_id": profile.user_id, "revision": profile.revision,
        "money_schema_version": profile.schema_version or 1,
        "age": profile.age, "employment_type": profile.employment_type,
        "monthly_income": paise_to_float(profile.monthly_income_paise),
        "monthly_expenses": paise_to_float(profile.monthly_expenses_paise),
        "existing_savings": paise_to_float(profile.existing_savings_paise),
        "existing_investments": paise_to_float(profile.existing_investments_paise),
        "existing_debts": paise_to_float(profile.existing_debts_paise),
        "monthly_debt_payment": paise_to_float(profile.monthly_debt_payment_paise),
        "monthly_income_paise": profile.monthly_income_paise,
        "monthly_expenses_paise": profile.monthly_expenses_paise,
        "existing_savings_paise": profile.existing_savings_paise,
        "existing_investments_paise": profile.existing_investments_paise,
        "existing_debts_paise": profile.existing_debts_paise,
        "monthly_debt_payment_paise": profile.monthly_debt_payment_paise,
        "risk_tolerance": profile.risk_tolerance, "investment_horizon": profile.investment_horizon,
        "financial_goals": profile.financial_goals or [],
        "credit_score": profile.credit_score, "credit_score_source": profile.credit_score_source,
        "monthly_credit_spend": paise_to_float(profile.monthly_credit_spend_paise),
        "top_spend_categories": profile.top_spend_categories or [],
        "needs_reentry": needs_reentry(profile),
        "created_at": profile.created_at, "updated_at": profile.updated_at,
    }
