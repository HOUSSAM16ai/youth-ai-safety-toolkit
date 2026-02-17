from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration for the API Gateway Microservice.
    Loads settings from environment variables.
    """

    # Service URLs (Defaults for local development/Docker Compose)
    PLANNING_AGENT_URL: str = "http://planning-agent:8000"
    MEMORY_AGENT_URL: str = "http://memory-agent:8000"
    USER_SERVICE_URL: str = "http://user-service:8000"
    OBSERVABILITY_SERVICE_URL: str = "http://observability-service:8000"
    RESEARCH_AGENT_URL: str = "http://research-agent:8000"
    REASONING_AGENT_URL: str = "http://reasoning-agent:8000"

    # Gateway Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CogniForge API Gateway"
    SECRET_KEY: str = "super_secret_key_change_in_production"

    # Resiliency Settings
    CONNECT_TIMEOUT: float = 5.0  # Seconds
    READ_TIMEOUT: float = 60.0  # Seconds
    WRITE_TIMEOUT: float = 60.0  # Seconds
    POOL_LIMIT: int = 100  # Max connections in pool

    # Circuit Breaker Settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5  # Number of failures before opening
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: float = 30.0  # Seconds to stay open

    # Retry Settings
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 0.5  # Base backoff in seconds

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
