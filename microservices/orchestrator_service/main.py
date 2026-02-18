import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from microservices.orchestrator_service.src.api import routes
from microservices.orchestrator_service.src.core.config import settings
from microservices.orchestrator_service.src.core.event_bus import event_bus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator_service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Orchestrator Service Starting...")
    yield
    logger.info("Orchestrator Service Shutting Down...")
    await event_bus.close()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    uvicorn.run("microservices.orchestrator_service.main:app", host="0.0.0.0", port=8000, reload=True)
