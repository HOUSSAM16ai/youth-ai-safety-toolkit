"""
UMS Schemas for User Service.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from microservices.user_service.src.core.common import CaseInsensitiveEnum


class UserStatus(CaseInsensitiveEnum):
    """User Lifecycle Status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DISABLED = "disabled"


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class ReauthRequest(BaseModel):
    password: str


class ReauthResponse(BaseModel):
    reauth_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    status: str = "reset_requested"
    reset_token: str | None = None
    expires_in: int | None = None


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower().strip() if value else value

    @model_validator(mode="after")
    def ensure_changes(self) -> ProfileUpdateRequest:
        if self.full_name is None and self.email is None:
            raise ValueError("At least one field must be provided for update")
        return self


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    status: UserStatus
    roles: list[str] = Field(default_factory=list)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminCreateUserRequest(BaseModel):
    full_name: str
    email: str
    password: str
    is_admin: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()


class StatusUpdateRequest(BaseModel):
    status: UserStatus


class RoleAssignmentRequest(BaseModel):
    role_name: str
    reauth_password: str | None = None
    reauth_token: str | None = None
    justification: str | None = None


class QuestionRequest(BaseModel):
    question: str


class PolicyBlockResponse(BaseModel):
    allowed: bool
    reason: str
    classification: str
