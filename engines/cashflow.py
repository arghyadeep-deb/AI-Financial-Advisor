"""Deterministic cash-flow and affordability rules (FR-001, FIN-01, FIN-14).

Pure functions over integer paise.  No I/O, no model calls.  Every consumer
(analysis agents, chat context, frontend) reads the same ``FinanceSnapshot``
so a deficit is a deficit everywhere.

Rule version ``cashflow.v1`` (profile-aggregate scope):

* ``surplus``  = income - declared monthly expenses (signed, may be negative).
* ``shortfall`` = max(0, -surplus).  Shown wherever surplus is shown.
* Committed obligations = declared monthly debt payment.  If the user has a
  debt balance but has not declared a payment the obligation is UNKNOWN and
  the available contribution is *unavailable*, never a positive guess.
* Reserve funding = ceil(emergency-fund gap / 12) while the gap is positive,
  but never more than the cash actually left after obligations (a top-up
  cannot exceed what is available).
* ``flow_capacity`` = surplus - obligations - reserve funding (signed).
* ``available_contribution`` = floor(max(0, flow_capacity) * 0.90) - a 10%
  buffer, and never negative.  Profile aggregates are user-declared
  estimates; the liquid-cash minimum from financial-rules.md applies once
  ledger/balance evidence exists (feature 002) and is recorded as such.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

RULE_VERSION = "cashflow.v1"
SNAPSHOT_SCHEMA_VERSION = 1
EMERGENCY_MONTHS = 6
BUFFER_NUMERATOR, BUFFER_DENOMINATOR = 9, 10  # keep 10% of capacity unallocated


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


# ── Pure rule functions (independently testable) ───────────────────────────

def surplus_paise(income: int, expenses: int) -> int:
    return income - expenses


def shortfall_paise(income: int, expenses: int) -> int:
    return max(0, expenses - income)


def emergency_gap_paise(savings: int, expenses: int, months: int = EMERGENCY_MONTHS) -> int:
    return max(0, expenses * months - savings)


def reserve_funding_paise(gap: int) -> int:
    return _ceil_div(gap, 12) if gap > 0 else 0


def flow_capacity_paise(income: int, spending: int, obligations: int, reserve_funding: int) -> int:
    """FIN-14: 65,000 - 55,000 - 4,000 - 3,000 = 3,000 (not 10,000)."""
    return income - spending - obligations - reserve_funding


def contribution_from_capacity(capacity: int) -> int:
    return max(0, capacity) * BUFFER_NUMERATOR // BUFFER_DENOMINATOR


# ── Snapshot ───────────────────────────────────────────────────────────────

@dataclass
class FinanceSnapshot:
    owner_id: Optional[int]
    profile_revision: Optional[int]
    income_paise: int
    expenses_paise: int
    surplus_paise: int
    shortfall_paise: int
    savings_paise: int
    investments_paise: int          # user-declared aggregate, NOT verified holdings
    debt_balance_paise: int
    monthly_debt_payment_paise: Optional[int]
    emergency_target_paise: int
    emergency_gap_paise: int
    reserve_funding_paise: int
    flow_capacity_paise: Optional[int]
    available_contribution_paise: Optional[int]   # None == unavailable
    contribution_status: str                      # available | none | unavailable
    contribution_reason: str
    credit_score: Optional[int]
    status: str                                   # complete | partial
    missing_inputs: List[str] = field(default_factory=list)
    rule_version: str = RULE_VERSION
    schema_version: int = SNAPSHOT_SCHEMA_VERSION
    as_of: str = ""
    created_at: str = ""
    coverage: str = "profile_aggregates"
    metric_provenance: Dict[str, str] = field(default_factory=dict)
    source_revision_vector: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["missing_inputs"] = list(self.missing_inputs)
        return d


def build_snapshot(profile: Dict[str, Any], *, owner_id: Optional[int] = None,
                   profile_revision: Optional[int] = None,
                   now: Optional[datetime] = None) -> FinanceSnapshot:
    """Build the canonical snapshot from a paise-valued profile mapping.

    Expected keys (paise ints): income_paise, expenses_paise, savings_paise,
    investments_paise, debt_balance_paise, monthly_debt_payment_paise
    (None = not declared), plus ``credit_score`` (None = unknown).
    """
    now = now or datetime.now(timezone.utc)
    income = int(profile["income_paise"])
    expenses = int(profile["expenses_paise"])
    savings = int(profile.get("savings_paise") or 0)
    investments = int(profile.get("investments_paise") or 0)
    debt_balance = int(profile.get("debt_balance_paise") or 0)
    debt_payment = profile.get("monthly_debt_payment_paise")
    credit = profile.get("credit_score")

    missing: List[str] = []
    surplus = surplus_paise(income, expenses)
    shortfall = shortfall_paise(income, expenses)
    gap = emergency_gap_paise(savings, expenses)
    reserve = reserve_funding_paise(gap)

    capacity: Optional[int]
    contribution: Optional[int]
    if debt_balance > 0 and debt_payment is None:
        missing.append("monthly_debt_payment")
        capacity = None
        contribution = None
        cstatus = "unavailable"
        reason = (
            "A debt balance is recorded but the monthly payment is not, so the amount "
            "you can safely invest cannot be determined. Add your monthly debt payment."
        )
    else:
        obligations = int(debt_payment or 0)
        reserve = min(reserve, max(0, surplus - obligations))
        capacity = flow_capacity_paise(income, expenses, obligations, reserve)
        contribution = contribution_from_capacity(capacity)
        if contribution > 0:
            cstatus = "available"
            reason = "Estimated from declared income, expenses, debt payment and emergency-fund top-up."
        elif shortfall > 0:
            cstatus = "none"
            reason = "Monthly expenses exceed income; there is no surplus to invest."
        else:
            cstatus = "none"
            reason = "After obligations and emergency-fund top-up nothing remains to invest."
    if credit is None:
        missing.append("credit_score")

    provenance = {
        "income": "user_declared", "expenses": "user_declared", "surplus": "derived",
        "shortfall": "derived", "available_contribution": "derived_estimate",
        "emergency_gap": "derived", "investments": "user_declared_aggregate",
        "credit_score": "user_declared" if credit is not None else "unavailable",
    }
    # A missing credit score does not make the cash-flow facts partial.
    snap_status = "partial" if "monthly_debt_payment" in missing else "complete"

    return FinanceSnapshot(
        owner_id=owner_id, profile_revision=profile_revision,
        income_paise=income, expenses_paise=expenses, surplus_paise=surplus,
        shortfall_paise=shortfall, savings_paise=savings, investments_paise=investments,
        debt_balance_paise=debt_balance, monthly_debt_payment_paise=debt_payment,
        emergency_target_paise=expenses * EMERGENCY_MONTHS, emergency_gap_paise=gap,
        reserve_funding_paise=reserve, flow_capacity_paise=capacity,
        available_contribution_paise=contribution, contribution_status=cstatus,
        contribution_reason=reason, credit_score=credit, status=snap_status,
        missing_inputs=missing, as_of=now.date().isoformat(), created_at=now.isoformat(),
        metric_provenance=provenance,
        source_revision_vector={"profile_revision": profile_revision},
    )
