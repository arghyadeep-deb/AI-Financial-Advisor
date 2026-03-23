from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email:     EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password:  str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      int
    full_name:    str
    email:        str


# ─── User ─────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:         int
    email:      str
    full_name:  str
    is_active:  bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Financial Profile ────────────────────────────────────────────────────────

class FinancialProfileRequest(BaseModel):

    # Personal
    age:             int = Field(ge=18, le=80)
    employment_type: str = Field(pattern="^(salaried|self_employed|business)$")

    # Income
    monthly_income:   float = Field(gt=0)
    monthly_expenses: float = Field(ge=0)

    # Existing wealth
    existing_savings:     float = Field(ge=0, default=0)
    existing_investments: float = Field(ge=0, default=0)
    existing_debts:       float = Field(ge=0, default=0)

    # Investment preferences
    risk_tolerance:     str = Field(pattern="^(low|moderate|high|very_high)$")
    investment_horizon: str = Field(pattern="^(short|medium|long)$")
    financial_goals:    List[str] = []

    # Credit card
    credit_score:           Optional[int]   = Field(ge=300, le=900, default=700)
    monthly_credit_spend:   float           = Field(ge=0, default=0)
    top_spend_categories:   List[str]       = []

    class Config:
        json_schema_extra = {
            "example": {
                "age":                  28,
                "employment_type":      "salaried",
                "monthly_income":       80000,
                "monthly_expenses":     45000,
                "existing_savings":     150000,
                "existing_investments": 50000,
                "existing_debts":       0,
                "risk_tolerance":       "moderate",
                "investment_horizon":   "long",
                "financial_goals":      ["house", "retirement"],
                "credit_score":         740,
                "monthly_credit_spend": 20000,
                "top_spend_categories": ["online shopping", "dining", "travel"]
            }
        }


class FinancialProfileResponse(BaseModel):
    id:                   int
    user_id:              int
    age:                  int
    employment_type:      str
    monthly_income:       float
    monthly_expenses:     float
    existing_savings:     float
    existing_investments: float
    existing_debts:       float
    risk_tolerance:       str
    investment_horizon:   str
    financial_goals:      Optional[List[str]]
    credit_score:         Optional[int]
    monthly_credit_spend: float
    top_spend_categories: Optional[List[str]]
    created_at:           datetime
    updated_at:           datetime

    class Config:
        from_attributes = True


# ─── Analysis ─────────────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    analysis_type: str = Field(
        default="full",
        description="full | quick | health | investment | credit | optimizer | simulation | rebalance | summary"
    )

    class Config:
        json_schema_extra = {
            "example": {"analysis_type": "full"}
        }


class AnalysisResponse(BaseModel):
    success:       bool
    analysis_type: str
    results:       Dict[str, Any]
    errors:        Dict[str, Any] = {}


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:   str
    thread_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "message":   "Explain my health score",
                "thread_id": None
            }
        }


class ChatResponse(BaseModel):
    reply:     str
    thread_id: int


# ─── Threads ──────────────────────────────────────────────────────────────────

class ThreadCreate(BaseModel):
    title:       str = Field(min_length=1, max_length=200)
    thread_type: str = Field(default="general")


class ThreadResponse(BaseModel):
    id:          int
    title:       str
    thread_type: str
    created_at:  datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id:         int
    role:       str
    content:    str
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    thread_id: int
    messages:  List[MessageResponse]


# ─── Financial State ──────────────────────────────────────────────────────────

class FinancialStateResponse(BaseModel):
    health_score:         float
    portfolio_value:      float
    monthly_savings_rate: float
    last_updated:         Optional[datetime]
    message:              Optional[str] = None


# ─── Last Analysis ────────────────────────────────────────────────────────────

class LastAnalysisResponse(BaseModel):
    found:   bool
    results: Dict[str, Any] = {}


# ─── Health Check ─────────────────────────────────────────────────────────────

class HealthCheckResponse(BaseModel):
    status:  str
    service: str
    version: str = "1.0.0"