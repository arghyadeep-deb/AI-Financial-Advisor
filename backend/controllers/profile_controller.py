from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.schemas.schemas import (
    FinancialProfileRequest,
    FinancialProfileResponse,
    UserResponse
)
from backend.services.profile_service import ProfileService
from backend.models.models import User

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("", response_model=FinancialProfileResponse)
def save_profile(
    payload:      FinancialProfileRequest,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Save or update financial profile."""
    return ProfileService(db).save(
        user_id = current_user.id,
        data    = payload.model_dump()
    )


@router.get("", response_model=FinancialProfileResponse)
def get_profile(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    """Get current user's financial profile."""
    return ProfileService(db).get_or_raise(current_user.id)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current logged-in user details."""
    return current_user