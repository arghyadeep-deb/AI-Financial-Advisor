from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.schemas.schemas import SignupRequest, LoginRequest, AuthResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse)
def signup(
    payload: SignupRequest,
    db:      Session = Depends(get_db)
):
    """Register a new user. Returns JWT token."""
    return AuthService(db).signup(
        email     = payload.email,
        full_name = payload.full_name,
        password  = payload.password
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    db:      Session = Depends(get_db)
):
    """Login with email and password. Returns JWT token."""
    return AuthService(db).login(
        email    = payload.email,
        password = payload.password
    )