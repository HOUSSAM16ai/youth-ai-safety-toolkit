"""
User Service Main Entrypoint.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from microservices.user_service.database import init_db
from microservices.user_service.errors import setup_exception_handlers
from microservices.user_service.health import HealthResponse, build_health_payload
from microservices.user_service.logging import get_logger, setup_logging
from microservices.user_service.security import verify_service_token
from microservices.user_service.settings import UserServiceSettings, get_settings
from microservices.user_service.src.api.routes import auth as auth_router
from microservices.user_service.src.api.routes import ums as ums_router

logger = get_logger("user-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings().SERVICE_NAME)
    logger.info("Service Starting...")
    await init_db()
    yield
    logger.info("Service Shutting Down...")


def create_app(settings: UserServiceSettings | None = None) -> FastAPI:
    effective_settings = settings or get_settings()

    app = FastAPI(
        title=effective_settings.SERVICE_NAME,
        description="Isolated microservice for user management.",
        version=effective_settings.SERVICE_VERSION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "System", "description": "System health and metrics"},
            {"name": "Auth", "description": "Authentication operations"},
            {"name": "UMS", "description": "User Management System"},
        ],
    )

    setup_exception_handlers(app)

    # Public Routers
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        return build_health_payload(effective_settings)

    # Protected Routers (Service Token from Gateway)
    # Note: Auth endpoints (Login/Register) are public in terms of user access,
    # but still proxied via Gateway. If Gateway strips service token for public routes, we need to handle that.
    # However, Monolith design usually implies Gateway always sends service token or similar trust.
    # For now, we assume verify_service_token checks that it comes from Gateway.

    # Auth Router (Login/Register - Public access via Gateway)
    app.include_router(auth_router.router, prefix="/api/v1/auth", dependencies=[Depends(verify_service_token)])

    # UMS Router (Protected by User Auth)
    app.include_router(ums_router.router, prefix="/api/v1", dependencies=[Depends(verify_service_token)])

    return app


app = create_app()
