from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration for the API Gateway Microservice.
    Loads settings from environment variables.
    """

    # Service URLs (Defaults for local development/Docker Compose)
    CORE_KERNEL_URL: str = "http://core-kernel:8000"
    PLANNING_AGENT_URL: str = "http://planning-agent:8000"
    MEMORY_AGENT_URL: str = "http://memory-agent:8000"
    USER_SERVICE_URL: str = "http://user-service:8000"
    OBSERVABILITY_SERVICE_URL: str = "http://observability-service:8000"
    RESEARCH_AGENT_URL: str = "http://research-agent:8000"
    REASONING_AGENT_URL: str = "http://reasoning-agent:8000"

    # Gateway Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CogniForge API Gateway"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
