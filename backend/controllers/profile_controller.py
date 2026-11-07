from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend.models.models import User
from backend.schemas.schemas import FinancialProfileRequest, FinancialProfileResponse, UserResponse
from backend.services.profile_service import ProfileService, profile_to_response

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("", response_model=FinancialProfileResponse)
def save_profile(
    payload: FinancialProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save or update the financial profile (a saved edit creates a new revision).

    Use ``POST /analysis`` with a ``scenario`` for one-off what-if values that
    must not change the saved profile.
    """
    profile = ProfileService(db).save(current_user.id, payload.model_dump())
    return profile_to_response(profile)


@router.get("", response_model=FinancialProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's financial profile."""
    return profile_to_response(ProfileService(db).get_or_raise(current_user.id))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current logged-in user details."""
    return current_user
