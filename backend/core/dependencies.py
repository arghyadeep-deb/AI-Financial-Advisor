from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.auth import decode_token
from backend.models.models import User, FinancialProfile

bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db:          Session = Depends(get_db)
) -> User:

    payload = decode_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again."
        )

    user = db.query(User).filter(
        User.id == int(payload.get("sub", 0))
    ).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )

    return user


def get_current_profile(
    current_user: User = Depends(get_current_user),
    db:           Session = Depends(get_db)
) -> FinancialProfile:

    profile = db.query(FinancialProfile).filter(
        FinancialProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not found. Please complete your profile first."
        )

    return profile


def profile_to_dict(profile: FinancialProfile) -> dict:
    """Convert SQLAlchemy model to plain dict for agents."""
    return {
        "age":                  profile.age,
        "employment_type":      profile.employment_type,
        "monthly_income":       profile.monthly_income,
        "monthly_expenses":     profile.monthly_expenses,
        "existing_savings":     profile.existing_savings     or 0,
        "existing_investments": profile.existing_investments or 0,
        "existing_debts":       profile.existing_debts       or 0,
        "risk_tolerance":       profile.risk_tolerance,
        "investment_horizon":   profile.investment_horizon,
        "financial_goals":      profile.financial_goals      or [],
        "credit_score":         profile.credit_score         or 700,
        "monthly_credit_spend": profile.monthly_credit_spend or 0,
        "top_spend_categories": profile.top_spend_categories or []
    }