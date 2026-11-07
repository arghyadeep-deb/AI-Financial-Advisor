from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field

from backend.core.money import MoneyError, parse_rupees


def _money_in(value):
    try:
        return parse_rupees(value)
    except MoneyError as exc:
        raise ValueError(str(exc)) from exc


# Rupee amount accepted from clients: finite, <= 2 decimals, bounded.  Parsed
# exactly (never through binary float) and converted to paise by the service.
MoneyIn = Annotated[Decimal, BeforeValidator(_money_in)]


# ─── Auth ─────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email:     EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    # Strength rules (length, common passwords) live in AuthService so the
    # same policy applies to signup and reset.
    password:  str = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    expires_in:   Optional[int] = None
    user_id:      int
    full_name:    str
    email:        str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token:        str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=1, max_length=128)


class MessageOnly(BaseModel):
    message: str


# ─── User ─────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    email:      str
    full_name:  str
    is_active:  bool
    created_at: datetime


# ─── Financial Profile ────────────────────────────────────────────────────────

class FinancialProfileRequest(BaseModel):
    """Saved-profile contract.  Rupee fields keep their legacy names; values
    are parsed exactly and stored as integer paise."""

    # Personal
    age:             int = Field(ge=18, le=80)
    employment_type: str = Field(pattern="^(salaried|self_employed|business)$")

    # Income
    monthly_income:   MoneyIn = Field(gt=0)
    monthly_expenses: MoneyIn = Field(ge=0)

    # Existing wealth
    existing_savings:     MoneyIn = Field(ge=0, default=Decimal("0"))
    existing_investments: MoneyIn = Field(ge=0, default=Decimal("0"))
    existing_debts:       MoneyIn = Field(ge=0, default=Decimal("0"))      # outstanding BALANCE
    # Distinct from the balance.  Omit/null = not declared (unknown, not zero).
    monthly_debt_payment: Optional[MoneyIn] = Field(ge=0, default=None)

    # Investment preferences
    risk_tolerance:     str = Field(pattern="^(low|moderate|high|very_high)$")
    investment_horizon: str = Field(pattern="^(short|medium|long)$")
    financial_goals:    List[str] = Field(default_factory=list, max_length=20)

    # Credit.  Omitted == unknown; never defaulted to a number.
    credit_score:           Optional[int] = Field(ge=300, le=900, default=None)
    monthly_credit_spend:   MoneyIn = Field(ge=0, default=Decimal("0"))
    top_spend_categories:   List[str] = Field(default_factory=list, max_length=20)

    # Optimistic concurrency: reject (409) if the stored revision moved on.
    expected_revision: Optional[int] = Field(default=None, ge=1)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "age": 28, "employment_type": "salaried",
            "monthly_income": 80000, "monthly_expenses": 45000,
            "existing_savings": 150000, "existing_investments": 50000,
            "existing_debts": 0, "monthly_debt_payment": 0,
            "risk_tolerance": "moderate", "investment_horizon": "long",
            "financial_goals": ["house", "retirement"],
            "credit_score": 740, "monthly_credit_spend": 20000,
            "top_spend_categories": ["online shopping", "dining", "travel"],
        }
    })


class FinancialProfileResponse(BaseModel):
    """Legacy float fields are retained for existing clients (deprecated);
    the ``*_paise`` integers are authoritative."""
    model_config = ConfigDict(from_attributes=True)

    id:                   int
    user_id:              int
    revision:             int
    money_schema_version: int = 1
    age:                  int
    employment_type:      str
    monthly_income:       Optional[float]
    monthly_expenses:     Optional[float]
    existing_savings:     Optional[float]
    existing_investments: Optional[float]
    existing_debts:       Optional[float]
    monthly_debt_payment: Optional[float] = None
    monthly_income_paise:       Optional[int] = None
    monthly_expenses_paise:     Optional[int] = None
    existing_savings_paise:     Optional[int] = None
    existing_investments_paise: Optional[int] = None
    existing_debts_paise:       Optional[int] = None
    monthly_debt_payment_paise: Optional[int] = None
    risk_tolerance:       str
    investment_horizon:   str
    financial_goals:      Optional[List[str]]
    credit_score:         Optional[int]
    credit_score_source:  Optional[str] = None
    monthly_credit_spend: Optional[float]
    top_spend_categories: Optional[List[str]]
    needs_reentry:        List[str] = Field(default_factory=list)
    created_at:           datetime
    updated_at:           datetime


# ─── Analysis ─────────────────────────────────────────────────────────────────

class ScenarioOverrides(BaseModel):
    """One-off what-if values.  Never persisted to the saved profile."""
    model_config = ConfigDict(extra="forbid")

    monthly_income:       Optional[MoneyIn] = Field(default=None, gt=0)
    monthly_expenses:     Optional[MoneyIn] = Field(default=None, ge=0)
    existing_savings:     Optional[MoneyIn] = Field(default=None, ge=0)
    existing_investments: Optional[MoneyIn] = Field(default=None, ge=0)
    existing_debts:       Optional[MoneyIn] = Field(default=None, ge=0)
    monthly_debt_payment: Optional[MoneyIn] = Field(default=None, ge=0)
    monthly_credit_spend: Optional[MoneyIn] = Field(default=None, ge=0)
    credit_score:         Optional[int]     = Field(default=None, ge=300, le=900)
    age:                  Optional[int]     = Field(default=None, ge=18, le=80)
    risk_tolerance:       Optional[str]     = Field(default=None, pattern="^(low|moderate|high|very_high)$")
    investment_horizon:   Optional[str]     = Field(default=None, pattern="^(short|medium|long)$")
    employment_type:      Optional[str]     = Field(default=None, pattern="^(salaried|self_employed|business)$")
    financial_goals:      Optional[List[str]] = Field(default=None, max_length=20)
    top_spend_categories: Optional[List[str]] = Field(default=None, max_length=20)


class AnalysisRequest(BaseModel):
    analysis_type: str = Field(
        default="full",
        description="full | quick | health | investment | credit | optimizer | simulation | rebalance | summary"
    )
    # Present => scenario run: uses these values on top of the saved profile
    # and leaves the saved profile (and its revision) untouched.
    scenario: Optional[ScenarioOverrides] = None

    model_config = ConfigDict(json_schema_extra={"example": {"analysis_type": "full"}})


class AnalysisResponse(BaseModel):
    success:       bool
    analysis_type: str
    results:       Dict[str, Any]
    errors:        Dict[str, Any] = Field(default_factory=dict)
    # Additive (FR-002 / FR-007)
    analysis_id:      Optional[str] = None
    # complete | degraded | partial | failed | superseded
    status:           str = "complete"
    is_scenario:      bool = False
    profile_revision: Optional[int] = None
    stale:            bool = False
    section_status:   Dict[str, Any] = Field(default_factory=dict)
    snapshot:         Dict[str, Any] = Field(default_factory=dict)


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:   str = Field(min_length=1, max_length=4000)
    thread_id: Optional[int] = None
    # Client-generated id for this logical turn; a retry with the same id
    # returns the stored turn instead of creating a duplicate (FR-007).
    client_message_id: Optional[str] = Field(default=None, min_length=8, max_length=64,
                                             pattern=r"^[A-Za-z0-9._:-]+$")

    model_config = ConfigDict(json_schema_extra={
        "example": {"message": "Explain my health score", "thread_id": None,
                    "client_message_id": "7f3a2c9e-0d1b-4c7e-9a51-3b2f8d6c1e44"}})


class ChatResponse(BaseModel):
    reply:     str
    thread_id: int
    status:    str = "ok"                 # ok | degraded
    replayed:  bool = False


# ─── Threads ──────────────────────────────────────────────────────────────────

class ThreadCreate(BaseModel):
    title:       str = Field(min_length=1, max_length=200)
    thread_type: str = Field(default="general")


class ThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          int
    title:       str
    thread_type: str
    created_at:  datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         int
    role:       str
    content:    str
    created_at: datetime


class HistoryResponse(BaseModel):
    thread_id: int
    messages:  List[MessageResponse]


# ─── Financial State ──────────────────────────────────────────────────────────

class FinancialStateResponse(BaseModel):
    # None == unknown (never coerced to 0 or a default).
    health_score:         Optional[float] = None
    # Observed holdings declared by the user. Never a projection.
    portfolio_value:      Optional[float] = None
    portfolio_value_basis: str = "user_declared_aggregate"
    monthly_savings_rate: Optional[float] = None
    last_updated:         Optional[datetime] = None
    profile_revision:     Optional[int] = None
    health_score_revision: Optional[int] = None
    stale:                bool = False
    message:              Optional[str] = None


# ─── Last Analysis ────────────────────────────────────────────────────────────

class LastAnalysisResponse(BaseModel):
    found:   bool
    results: Dict[str, Any] = Field(default_factory=dict)
    # Additive
    analysis_id:      Optional[str] = None
    status:           Optional[str] = None
    profile_revision: Optional[int] = None
    current_revision: Optional[int] = None
    stale:            Optional[bool] = None
    completed_at:     Optional[datetime] = None
    section_status:   Dict[str, Any] = Field(default_factory=dict)
    by_kind:          Dict[str, Any] = Field(default_factory=dict)
    snapshot:         Dict[str, Any] = Field(default_factory=dict)


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthCheckResponse(BaseModel):
    status:  str
    service: str
