from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.pool import StaticPool

from microservices.user_service.main import app
from microservices.user_service.models import User
from microservices.user_service.security import get_auth_service, verify_service_token
from microservices.user_service.settings import get_settings
from microservices.user_service.src.services.auth.service import AuthService


# Use in-memory SQLite for testing
@pytest.fixture(name="session", scope="function")
async def fixture_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    from sqlalchemy.orm import sessionmaker

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture(name="client")
async def fixture_client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    # Override dependency to use test session
    async def get_auth_service_override():
        return AuthService(session)

    # Bypass service token check
    async def verify_service_token_override():
        return True

    app.dependency_overrides[get_auth_service] = get_auth_service_override
    app.dependency_overrides[verify_service_token] = verify_service_token_override

    settings = get_settings()
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    settings.ENVIRONMENT = "testing"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(session: AsyncSession) -> User:
    service = AuthService(session)
    # Ensure role seed
    await service.rbac.ensure_seed()

    user = await service.register_user(
        full_name="Admin User",
        email="admin@example.com",
        password="password123",
    )
    await service.promote_to_admin(user=user)
    return user


@pytest.fixture
async def admin_token(admin_user: User, session: AsyncSession) -> str:
    service = AuthService(session)
    tokens = await service.issue_tokens(admin_user)
    return tokens["access_token"]
