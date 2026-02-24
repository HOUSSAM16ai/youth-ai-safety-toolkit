import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure models are registered with SQLModel
import microservices.orchestrator_service.src.models.mission  # noqa: F401
from microservices.orchestrator_service.src.api import routes
from microservices.orchestrator_service.src.core.config import settings
from microservices.orchestrator_service.src.core.database import init_db
from microservices.orchestrator_service.src.core.event_bus import event_bus
from microservices.orchestrator_service.src.services.tools.content import (
    register_content_tools,
)
from microservices.orchestrator_service.src.services.tools.registry import get_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Orchestrator Service Starting...")

    # Register Content Tools
    register_content_tools(get_registry())

    await init_db()
    yield
    logger.info("Orchestrator Service Shutting Down...")
    await event_bus.close()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "orchestrator-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "microservices.orchestrator_service.main:app", host="0.0.0.0", port=8000, reload=True
    )
