"""Versioned suitability answers; missing material facts never imply capacity."""
from typing import Literal
from backend.finance.allocation_assumptions import load_register, policy_value

from pydantic import BaseModel, ConfigDict, Field


class Suitability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    questionnaire_version: Literal["suitability.v1"] = "suitability.v1"
    revision: int = Field(gt=0)
    horizon_months: int | None = Field(default=None, gt=0, le=1200)
    essential_goal_months: int | None = Field(default=None, gt=0, le=1200)
    essential_goals_declared: bool | None = None
    dependants: int | None = Field(default=None, ge=0, le=100)
    income_stable: bool | None = None
    debt_reviewed: bool | None = None
    reserves_reviewed: bool | None = None
    experience: Literal["none", "some", "experienced"] | None = None
    loss_tolerance: Literal["low", "moderate", "high"] | None = None
    loss_capacity: Literal["low", "moderate", "high"] | None = None

    def blockers(self, *, near_term_months: int | None = None) -> tuple[str, ...]:
        if near_term_months is None:
            near_term_months = policy_value("near_term_months")
        required = ("horizon_months", "essential_goals_declared", "dependants", "income_stable",
                    "debt_reviewed", "reserves_reviewed", "experience", "loss_tolerance", "loss_capacity")
        reasons = [f"Provide {name}" for name in required if getattr(self, name) is None]
        if self.essential_goals_declared and self.essential_goal_months is None:
            reasons.append("Provide essential goal horizon")
        if self.essential_goals_declared is False and self.essential_goal_months is not None:
            reasons.append("Resolve contradictory essential goal answers")
        if self.debt_reviewed is False or self.reserves_reviewed is False:
            reasons.append("Review debt and reserve needs")
        rank = {"low": 0, "moderate": 1, "high": 2}
        if self.loss_tolerance and self.loss_capacity and rank[self.loss_tolerance] > rank[self.loss_capacity]:
            reasons.append("Resolve tolerance exceeding loss capacity")
        if self.loss_tolerance == "high" and (
            (self.horizon_months is not None and self.horizon_months < near_term_months)
            or (self.essential_goal_months is not None and self.essential_goal_months < near_term_months)
            or self.income_stable is False
        ):
            reasons.append("Resolve high tolerance against near-term needs or unstable income")
        return tuple(reasons)

    def assessment(self) -> dict:
        """Derived from immutable answers; never inferred from demographics or prose.

        Keep incomplete/conflicting answers so the owner can resolve them in a
        subsequent revision. This assessment grants no public advice eligibility.
        """
        reasons = self.blockers()
        return {
            "assessment_rule_version": "suitability-assessment.v1",
            "questionnaire_version": self.questionnaire_version,
            "revision": self.revision,
            "status": "needs_review" if reasons else "complete",
            "blocks_personalized_proposal": bool(reasons),
            "reasons": list(reasons),
            "resolution": "Submit a new answer revision resolving the listed facts or conflicts." if reasons else None,
            "capacity_basis": "owner_declared_unverified",
            "public_eligible": False,
            "policy_status": "unvalidated_prototype",
            "policy_assumptions": load_register().model_dump(mode="json"),
        }
