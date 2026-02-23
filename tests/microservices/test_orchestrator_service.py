import asyncio
import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import SQLModel


def mock_verify_token():
    return True


def test_create_mission_endpoint():
    """
    Test creating a mission via the Orchestrator Service API.
    Ensures the microservice is correctly wired up and handles requests.
    """
    # Force SQLite for testing to avoid asyncpg dependency and connection attempts
    os.environ["ORCHESTRATOR_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Clear metadata to allow re-definition of tables for the microservice context
    SQLModel.metadata.clear()

    import importlib

    import microservices.orchestrator_service.src.core.database
    import microservices.orchestrator_service.src.models.mission
    from microservices.orchestrator_service.main import app
    from microservices.orchestrator_service.src.core.database import engine, get_db

    # Reload model to ensure it registers with the cleared metadata
    importlib.reload(microservices.orchestrator_service.src.models.mission)

    # We need an event loop for async engine
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def init_tables():
        async with engine.begin() as conn:
            # Drop all to ensure clean slate in case of reused engine/DB
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

    loop.run_until_complete(init_tables())

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    # Fix N806: Use lowercase variable name
    test_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Mock EventBus to avoid Redis connection attempts
    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    # Mock subscribe to return an empty async iterator
    mock_event_bus.subscribe.return_value = AsyncMock()

    # Patch init_db and event_bus
    # We use _ to indicate unused variable to satisfy ruff F841
    with patch(
        "microservices.orchestrator_service.src.core.database.init_db",
        new_callable=AsyncMock,
    ) as _:
        with patch(
            "microservices.orchestrator_service.src.core.event_bus.event_bus",
            mock_event_bus,
        ):
            with TestClient(app) as client:
                payload = {
                    "objective": "Test Mission Objective",
                    "context": {"env": "test"},
                    "priority": 1,
                }

                # Use X-Correlation-ID header as idempotency key
                headers = {"X-Correlation-ID": "test-idempotency-key-123"}

                response = client.post("/missions", json=payload, headers=headers)

                # Debugging if it fails
                if response.status_code != 200:
                    print(f"Response: {response.text}")

                assert response.status_code == 200
                data = response.json()

                assert data["objective"] == "Test Mission Objective"
                assert data["status"] == "pending"
                assert "id" in data

                # Verify mission can be retrieved
                mission_id = data["id"]
                response_get = client.get(f"/missions/{mission_id}")
                assert response_get.status_code == 200
                data_get = response_get.json()
                assert data_get["id"] == mission_id
                assert data_get["objective"] == "Test Mission Objective"
