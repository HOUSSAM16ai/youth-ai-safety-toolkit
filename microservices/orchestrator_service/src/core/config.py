from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Orchestrator Service"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="dev_secret_key", validation_alias="SECRET_KEY")

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_DB: str = "orchestrator_db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = Field(default="", validation_alias="ORCHESTRATOR_DATABASE_URL")

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # Microservices URLs
    PLANNING_AGENT_URL: str = "http://planning-agent:8000"
    MEMORY_AGENT_URL: str = "http://memory-agent:8000"
    RESEARCH_AGENT_URL: str = "http://research-agent:8000"
    REASONING_AGENT_URL: str = "http://reasoning-agent:8000"
    USER_SERVICE_URL: str = "http://user-service:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def model_post_init(self, __context):
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
