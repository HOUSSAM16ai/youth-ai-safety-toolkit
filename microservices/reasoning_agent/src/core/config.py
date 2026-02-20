from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the Reasoning Agent."""

    # Service Info
    SERVICE_NAME: str = "reasoning-agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API Keys
    OPENAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

    # External Services
    RESEARCH_AGENT_URL: str = "http://research-agent:8007"
    ORCHESTRATOR_URL: str = "http://orchestrator-service:8006"

    # Reasoning Config
    DEFAULT_MODEL: str = "gpt-4o"
    REASONING_TIMEOUT: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
