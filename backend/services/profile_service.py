from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.models.models import FinancialProfile


class ProfileService:

    def __init__(self, db: Session):
        self.db = db

    def save(self, user_id: int, data: dict) -> FinancialProfile:
        """Create or update financial profile."""

        profile = self.db.query(FinancialProfile).filter(
            FinancialProfile.user_id == user_id
        ).first()

        if profile:
            # Update existing
            for key, value in data.items():
                setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
            print(f"[ProfileService] Profile updated for user {user_id}")
        else:
            # Create new
            profile = FinancialProfile(user_id=user_id, **data)
            self.db.add(profile)
            print(f"[ProfileService] Profile created for user {user_id}")

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get(self, user_id: int) -> FinancialProfile:
        """Get profile by user ID."""
        return self.db.query(FinancialProfile).filter(
            FinancialProfile.user_id == user_id
        ).first()

    def get_or_raise(self, user_id: int) -> FinancialProfile:
        """Get profile or raise 404."""
        profile = self.get(user_id)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found. Please complete your profile first."
            )
        return profile