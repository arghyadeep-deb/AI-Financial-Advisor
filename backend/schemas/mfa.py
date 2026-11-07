"""MFA contracts: never expose a stored secret or recovery hashes."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class MfaChallengeResponse(BaseModel):
    mfa_required: Literal[True] = True
    challenge: str
    expires_in: int = 300


class MfaCode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: SecretStr = Field(min_length=1, max_length=128)


class MfaVerify(MfaCode):
    challenge: SecretStr = Field(min_length=1, max_length=128)


class MfaSetupResponse(BaseModel):
    otpauth_uri: str
    expires_in: int = 600
