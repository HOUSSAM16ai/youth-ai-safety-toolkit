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

    # Import modules to ensure they are loaded before patching

    # Clear metadata to allow re-definition of tables for the microservice context
    SQLModel.metadata.clear()

    # Setup DB override using the shared test session factory (SQLite in-memory)
    # We DO NOT call _ensure_schema() because it loads Monolith models!
    # Instead we manually create the schema for the models we just loaded/cleared.
    # We need to make sure the engine is bound to the metadata?
    # SQLModel.metadata.create_all(engine) should work if engine is configured.
    # We need to make sure we use the same engine as the session factory?
    # _get_session_factory creates an engine.
    # Let's verify if we need to reload models?
    # If they were loaded by previous tests, they are in sys.modules.
    # clearing metadata removes them from metadata.
    # We need to re-register them?
    # Only way is to reload the module.
    import importlib

    import microservices.orchestrator_service.src.core.database
    import microservices.orchestrator_service.src.models.mission
    from microservices.orchestrator_service.main import app
    from microservices.orchestrator_service.src.core.database import engine, get_db
    importlib.reload(microservices.orchestrator_service.src.models.mission)

    # Now Mission is in metadata.

    # We need an event loop for async engine
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def init_tables():
        # Use the engine from core.database which is used by the app
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    loop.run_until_complete(init_tables())

    # Reuse session factory from conftest but bind to our engine?
    # Actually core.database.engine is what we want.
    # But get_db uses session_factory from conftest?
    # app.dependency_overrides[get_db] needs to yield a session.

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with TestSession() as session:
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
