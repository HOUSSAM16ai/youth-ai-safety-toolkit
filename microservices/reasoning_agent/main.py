from contextlib import asynccontextmanager

from fastapi import FastAPI

from microservices.reasoning_agent.src.api.routes import router
from microservices.reasoning_agent.src.core.config import settings
from microservices.reasoning_agent.src.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the Reasoning Agent."""
    setup_logging()
    print(f"🚀 {settings.SERVICE_NAME} Started in {settings.ENVIRONMENT} mode")
    yield
    print(f"🛑 {settings.SERVICE_NAME} Stopped")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Reasoning Agent",
        description="High-performance Deep Reasoning Microservice",
        version="2.0.0",
        lifespan=lifespan
    )

    app.include_router(router)
    return app

app = create_app()
