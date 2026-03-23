import jwt
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "changeme-in-production")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7


# ─── Password Hashing ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using SHA-256 + secret key."""
    return hmac.new(
        SECRET_KEY.encode(),
        password.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if plain password matches the stored hash."""
    return hash_password(plain_password) == hashed_password


# ─── JWT Token ───────────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """Create a JWT token that expires in 7 days."""
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload.update({"exp": expire})
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    Returns the payload dict if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None