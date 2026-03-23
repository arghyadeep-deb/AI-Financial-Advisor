from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.models.models import User
from backend.core.auth import hash_password, verify_password, create_access_token


class AuthService:

    def __init__(self, db: Session):
        self.db = db

    def signup(
        self,
        email:     str,
        full_name: str,
        password:  str
    ) -> dict:
        """Register a new user."""

        # Check email already exists
        existing = self.db.query(User).filter(
            User.email == email
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please login instead."
            )

        # Create user
        user = User(
            email           = email,
            full_name       = full_name,
            hashed_password = hash_password(password)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        print(f"[AuthService] New user created: {email}")

        return {
            "access_token": create_access_token({"sub": str(user.id)}),
            "user_id":      user.id,
            "full_name":    user.full_name,
            "email":        user.email
        }

    def login(
        self,
        email:    str,
        password: str
    ) -> dict:
        """Login and return JWT token."""

        user = self.db.query(User).filter(
            User.email == email
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found with this email. Please signup first."
            )

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password. Please try again."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive. Please contact support."
            )

        print(f"[AuthService] Login successful: {email}")

        return {
            "access_token": create_access_token({"sub": str(user.id)}),
            "user_id":      user.id,
            "full_name":    user.full_name,
            "email":        user.email
        }