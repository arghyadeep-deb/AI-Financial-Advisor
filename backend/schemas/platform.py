"""Strict wire contracts for shared account controls. Bearer auth; no cookie CSRF surface."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr

class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr
    new_password: SecretStr

class ConsentChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["model_inference", "tracing"]
    granted: bool
    notice_version: str = Field(min_length=1, max_length=40)

class Reauthentication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=1024)


class DeletionReceipt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: SecretStr = Field(min_length=43, max_length=43)

from pydantic import model_validator
class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    categories: list[Literal["report_ready", "reminder"]] = Field(default_factory=lambda: ["report_ready", "reminder"], max_length=2)
    quiet_start: int | None = Field(default=None, ge=0, le=23)
    quiet_end: int | None = Field(default=None, ge=0, le=23)
    @model_validator(mode="after")
    def paired(self):
        if (self.quiet_start is None) != (self.quiet_end is None):
            raise ValueError("Both quiet-hour boundaries are required (Asia/Kolkata).")
        if self.quiet_start is not None and self.quiet_start == self.quiet_end:
            raise ValueError("Quiet-hour boundaries must differ.")
        return self
