import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Unified Configuration for Orchestrator Service.
    Safe defaults, environment-aware, and decoupled from Monolith.
    """

    # Service Identity
    SERVICE_NAME: str = "orchestrator-service"
    SERVICE_VERSION: str = "1.0.0"
    PROJECT_NAME: str = "Orchestrator Service"

    # Environment
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = Field(
        "development", description="Operational environment"
    )
    DEBUG: bool = Field(False, description="Debug mode")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Logging level"
    )
    CODESPACES: bool = Field(False, description="Is running in GitHub Codespaces")

    # Security
    SECRET_KEY: str = Field(default="dev_secret_key", validation_alias="SECRET_KEY")
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(default=["*"], description="CORS Allowed Origins")

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"  # Safe default
    POSTGRES_DB: str = "orchestrator_db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(default="", validation_alias="ORCHESTRATOR_DATABASE_URL")

    # Redis
    REDIS_URL: str = "redis://localhost:6379"  # Safe default

    # AI Config
    OPENAI_API_KEY: str | None = Field(None, description="OpenAI API Key")
    OPENROUTER_API_KEY: str | None = Field(None, description="OpenRouter API Key")

    # Microservices URLs (Dynamic Resolution)
    # Default is None so validator can set the correct default based on env
    PLANNING_AGENT_URL: str | None = Field(default=None, validate_default=True)
    MEMORY_AGENT_URL: str | None = Field(default=None, validate_default=True)
    RESEARCH_AGENT_URL: str | None = Field(default=None, validate_default=True)
    REASONING_AGENT_URL: str | None = Field(default=None, validate_default=True)
    USER_SERVICE_URL: str | None = Field(default=None, validate_default=True)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("CODESPACES", mode="before")
    @classmethod
    def detect_codespaces(cls, v: object) -> bool:
        if v is not None:
            return bool(v)
        return os.getenv("CODESPACES") == "true"

    @field_validator(
        "USER_SERVICE_URL",
        "RESEARCH_AGENT_URL",
        "PLANNING_AGENT_URL",
        "REASONING_AGENT_URL",
        "MEMORY_AGENT_URL",
        mode="before",
    )
    @classmethod
    def resolve_service_urls(cls, v: str | None, info: ValidationInfo) -> str:
        """
        Resolves service URLs based on environment (Docker vs Local/Codespaces).
        """
        if v:
            return v

        field_name = info.field_name
        is_codespaces = info.data.get("CODESPACES")
        if is_codespaces is None:
            is_codespaces = os.getenv("CODESPACES") == "true"

        # Map: Field -> (Local Port, Docker Host, Docker Port)
        service_map = {
            "USER_SERVICE_URL": ("8003", "user-service", "8000"),
            "RESEARCH_AGENT_URL": ("8007", "research-agent", "8000"),
            "PLANNING_AGENT_URL": ("8001", "planning-agent", "8000"),
            "REASONING_AGENT_URL": ("8008", "reasoning-agent", "8000"),
            "MEMORY_AGENT_URL": ("8002", "memory-agent", "8000"),
        }

        if field_name not in service_map:
            # Fallback
            return "http://localhost:8000"

        local_port, host, docker_port = service_map[field_name]

        if is_codespaces:
            return f"http://localhost:{local_port}"

        # Default to Docker service name (for production/docker-compose)
        return f"http://{host}:{docker_port}"

    def model_post_init(self, __context):
        if not self.DATABASE_URL:
            # Construct DB URL from components
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Enforces security rules in production."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if self.SECRET_KEY == "dev_secret_key" or len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be strong in production")
            if self.BACKEND_CORS_ORIGINS == ["*"]:
                raise ValueError("SECURITY RISK: BACKEND_CORS_ORIGINS cannot be '*' in production.")
        return self


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
