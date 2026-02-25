import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel

# Force SQLite before any imports
os.environ["ORCHESTRATOR_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


def test_create_mission_endpoint():
    """
    Test creating a mission via the Orchestrator Service API.
    Ensures the microservice is correctly wired up and handles requests.
    """
    # IMPORT DOMAIN MODELS TO REGISTER THEM WITH SQLALCHEMY METADATA
    # This fixes the "NoForeignKeysError" because both Mission and User must be
    # registered in the same metadata instance before create_all is called.
    import app.core.domain.mission
    import app.core.domain.user  # noqa: F401

    # Lazy import to ensure env vars take effect
    # Rename to avoid conflict with top-level 'app' package
    from microservices.orchestrator_service.main import app as fastapi_app
    from microservices.orchestrator_service.src.core.database import engine, get_db

    # Create tables in the SQLite memory DB
    async def init_tables():
        # Deduplicate indexes to handle potential accumulation from multiple test runs
        for table in SQLModel.metadata.tables.values():
            unique_indexes = {}
            if hasattr(table, "indexes"):
                for index in table.indexes:
                    if index.name not in unique_indexes:
                        unique_indexes[index.name] = index
                table.indexes = set(unique_indexes.values())

        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(init_tables())

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    test_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Mock EventBus
    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    mock_event_bus.subscribe.return_value = AsyncMock()
    mock_event_bus.close = AsyncMock()

    # Mock Redis Client
    mock_redis_client = AsyncMock()
    # IMPORTANT: client.lock(...) is NOT async. It returns a Lock object synchronously.
    # The Lock object itself has async methods (acquire/release).
    mock_lock = AsyncMock()
    mock_lock.acquire.return_value = True
    mock_lock.release = AsyncMock()
    mock_lock.__aenter__.return_value = mock_lock
    mock_lock.__aexit__.return_value = None

    # Configure lock to be a MagicMock (sync) that returns the async mock_lock
    mock_redis_client.lock = MagicMock(return_value=mock_lock)
    mock_redis_client.close = AsyncMock()

    # Patch redis.asyncio.from_url
    with (
        patch(
            "microservices.orchestrator_service.src.core.database.init_db",
            new_callable=AsyncMock,
        ) as _,
        patch(
            "microservices.orchestrator_service.src.core.event_bus.event_bus",
            mock_event_bus,
        ),
        patch(
            "redis.asyncio.from_url",
            return_value=mock_redis_client,
        ),
        # Ensure we don't try to connect to real Redis during app startup/shutdown events if any
        patch("microservices.orchestrator_service.main.event_bus", mock_event_bus),
    ):
        with TestClient(fastapi_app) as client:
            payload = {
                "objective": "Test Mission Objective",
                "context": {"env": "test"},
                "priority": 1,
            }

            headers = {"X-Correlation-ID": "test-idempotency-key-123"}

            response = client.post("/missions", json=payload, headers=headers)

            if response.status_code != 200:
                print(f"Response: {response.text}")

            assert response.status_code == 200
            data = response.json()

            assert data["objective"] == "Test Mission Objective"
            assert data["status"] == "pending"
            assert "id" in data

            mission_id = data["id"]
            response_get = client.get(f"/missions/{mission_id}")
            assert response_get.status_code == 200
            data_get = response_get.json()
            assert data_get["id"] == mission_id
            assert data_get["objective"] == "Test Mission Objective"
