from pydantic import AliasChoices, Field, ValidationInfo, field_validator

from microservices.user_service.src.schemas.base import RobustBaseModel


class TokenRequest(RobustBaseModel):
    user_id: int | None = None
    scopes: list[str] = Field(default_factory=list)


class LoginRequest(RobustBaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class RegisterRequest(RobustBaseModel):
    full_name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenVerifyRequest(RobustBaseModel):
    token: str | None = None


class UserResponse(RobustBaseModel):
    id: int
    name: str = Field(
        ..., validation_alias=AliasChoices("name", "full_name"), serialization_alias="name"
    )
    full_name: str | None = Field(
        None,
        description="Full Name",
        serialization_alias="full_name",
    )
    email: str
    is_admin: bool = False

    @field_validator("full_name", mode="after")
    @classmethod
    def mirror_full_name(cls, value: str | None, info: ValidationInfo) -> str:
        base_name = info.data.get("name") if hasattr(info, "data") else None
        return value or base_name

    def model_dump(self, *args: object, **kwargs: object) -> dict[str, object]:
        data = super().model_dump(*args, **kwargs)
        if not kwargs.get("by_alias"):
            data.pop("full_name", None)
        return data


class AuthResponse(RobustBaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserResponse
    status: str = "success"
    landing_path: str = "/app/chat"


class RegisterResponse(RobustBaseModel):
    status: str = "success"
    message: str
    user: UserResponse


class HealthResponse(RobustBaseModel):
    status: str
    data: dict[str, object]


class TokenVerifyResponse(RobustBaseModel):
    status: str
    data: dict[str, object]


class TokenGenerateResponse(RobustBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
