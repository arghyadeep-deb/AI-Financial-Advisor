import jwt
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional
from backend.core.config import config


def hash_password(password: str) -> str:
    return hmac.new(
        config.SECRET_KEY.encode(),
        password.encode(),
        hashlib.sha256
    ).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def create_access_token(data: dict) -> str:
    payload        = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=config.TOKEN_EXPIRE_DAYS)
    return jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM]
        )
    except jwt.PyJWTError:
        return None