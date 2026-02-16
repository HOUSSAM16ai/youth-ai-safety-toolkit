"""
خدمة المستخدمين.

تقدم إدارة مستخدمين مستقلة عبر واجهات API صارمة ومبسطة.
"""

import re
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from microservices.user_service.database import get_session, init_db
from microservices.user_service.errors import ConflictError, setup_exception_handlers

# Local Domain
from microservices.user_service.health import HealthResponse, build_health_payload
from microservices.user_service.logging import get_logger, setup_logging
from microservices.user_service.models import User
from microservices.user_service.security import verify_service_token
from microservices.user_service.settings import UserServiceSettings, get_settings

logger = get_logger("user-service")

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


# -----------------------------------------------------------------------------
# DTOs (Data Transfer Objects)
# -----------------------------------------------------------------------------


class UserCreateRequest(BaseModel):
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="Valid email address")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """التحقق من صحة البريد الإلكتروني وتوحيد تنسيقه."""
        normalized = value.strip()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid email format")
        return normalized


class UserResponse(BaseModel):
    user_id: UUID
    name: str
    email: str


class UserCountResponse(BaseModel):
    count: int


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------


def _build_router(settings: UserServiceSettings) -> APIRouter:
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        """نقطة فحص الصحة لبيئات التشغيل والحاويات."""
        return build_health_payload(settings)

    @router.post(
        "/users",
        response_model=UserResponse,
        tags=["Users"],
        summary="إنشاء مستخدم جديد",
    )
    async def create_user(
        payload: UserCreateRequest, session: AsyncSession = Depends(get_session)
    ) -> UserResponse:
        """إنشاء مستخدم جديد مع تحقق صارم من البريد الإلكتروني."""
        logger.info("Creating user", extra={"email": payload.email})

        user = User(name=payload.name, email=payload.email)
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError as exc:
            await session.rollback()
            logger.warning("Email conflict", extra={"email": payload.email})
            raise ConflictError("Email already registered") from exc

        return UserResponse(user_id=user.id, name=user.name, email=user.email)

    @router.get(
        "/users/count",
        response_model=UserCountResponse,
        tags=["Users"],
        summary="إجمالي عدد المستخدمين",
    )
    async def count_users(session: AsyncSession = Depends(get_session)) -> UserCountResponse:
        """حساب إجمالي عدد المستخدمين."""
        logger.info("Counting users")
        statement = select(func.count(User.id))
        result = await session.execute(statement)
        count = result.scalar_one()
        return UserCountResponse(count=count)

    @router.get(
        "/users",
        response_model=list[UserResponse],
        tags=["Users"],
        summary="عرض المستخدمين",
    )
    async def list_users(session: AsyncSession = Depends(get_session)) -> list[UserResponse]:
        """سرد جميع المستخدمين."""
        logger.info("Listing users")
        statement = select(User)
        result = await session.execute(statement)
        users = result.scalars().all()
        return [UserResponse(user_id=u.id, name=u.name, email=u.email) for u in users]

    return router


# -----------------------------------------------------------------------------
# App Factory
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق (بدء/إيقاف)."""
    # Startup
    setup_logging(get_settings().SERVICE_NAME)
    logger.info("Service Starting...")
    await init_db()
    yield
    # Shutdown
    logger.info("Service Shutting Down...")


def create_app(settings: UserServiceSettings | None = None) -> FastAPI:
    """بناء تطبيق FastAPI لخدمة المستخدمين."""
    effective_settings = settings or get_settings()

    app = FastAPI(
        title=effective_settings.SERVICE_NAME,
        description="Isolated microservice for user management.",
        version=effective_settings.SERVICE_VERSION,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "System", "description": "System health and metrics"},
            {"name": "Users", "description": "User management operations"},
        ],
    )

    setup_exception_handlers(app)

    # تطبيق Zero Trust: التحقق من الهوية عند البوابة
    app.include_router(
        _build_router(effective_settings), dependencies=[Depends(verify_service_token)]
    )

    return app


app = create_app()
