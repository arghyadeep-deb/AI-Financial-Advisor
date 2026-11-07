"""Versioned suitability answers; missing material facts never imply capacity."""
from typing import Literal

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

    def blockers(self) -> tuple[str, ...]:
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
            (self.horizon_months is not None and self.horizon_months < 36)
            or (self.essential_goal_months is not None and self.essential_goal_months < 36)
            or self.income_stable is False
        ):
            reasons.append("Resolve high tolerance against near-term needs or unstable income")
        return tuple(reasons)
