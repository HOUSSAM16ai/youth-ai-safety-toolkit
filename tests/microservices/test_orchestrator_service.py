import asyncio
import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def mock_verify_token():
    return True


def test_create_mission_endpoint():
    """
    Test creating a mission via the Orchestrator Service API.
    Ensures the microservice is correctly wired up and handles requests.
    """
    # Force SQLite for testing to avoid asyncpg dependency and connection attempts
    os.environ["ORCHESTRATOR_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Import modules to ensure they are loaded before patching
    # We clear SQLModel metadata to avoid "Table 'missions' is already defined" error
    # This happens because conftest might load monolith models, and then we import microservice models
    # which try to define the same table name 'missions'.
    from sqlmodel import SQLModel

    # Clear metadata to allow re-definition of tables for the microservice context
    SQLModel.metadata.clear()

    import microservices.orchestrator_service.src.core.database  # noqa: F401

    from microservices.orchestrator_service.main import app
    from microservices.orchestrator_service.src.core.database import get_db
    from tests.conftest import _ensure_schema, _get_session_factory, _run_async

    # Setup DB override using the shared test session factory (SQLite in-memory)
    # This ensures we use the test database schema
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # We need to ensure schema is created AFTER we cleared metadata and imported microservice models?
    # Actually, importing `main` -> `routes` -> `...` -> `models` registers them.
    # So we should clear metadata BEFORE importing main.

    # Re-run schema creation for the new metadata
    # We need to bind the engine to this new metadata or just use create_all

    # We can reuse _get_session_factory but we need to make sure the tables are created.
    # _ensure_schema in conftest does create_all.

    _run_async(loop, _ensure_schema())
    session_factory = _get_session_factory()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Mock EventBus to avoid Redis connection attempts
    mock_event_bus = AsyncMock()
    mock_event_bus.publish = AsyncMock()
    # Mock subscribe to return an empty async iterator or similar if needed
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
