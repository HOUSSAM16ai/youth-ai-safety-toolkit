from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from microservices.orchestrator_service.main import app
from microservices.orchestrator_service.src.services.tools.registry import get_registry


@patch("microservices.orchestrator_service.main.init_db", new_callable=AsyncMock)
@patch("microservices.orchestrator_service.main.event_bus.close", new_callable=AsyncMock)
def test_tool_registration_on_startup(mock_close, mock_init):
    """
    Verify that tools are automatically registered when the application starts via lifespan.
    Mocks DB initialization to run in isolation.
    """
    # Trigger startup events by using the client as a context manager (lifespan)
    with TestClient(app) as client:
        registry = get_registry()

        # Check if registry is populated
        assert "search_content" in registry
        assert "search_educational_content" in registry
        assert "get_content_raw" in registry
        assert "get_curriculum_structure" in registry

        # Verify callables
        assert callable(registry["search_content"])
        assert callable(registry["search_educational_content"])

        # Health check to ensure app didn't crash
        response = client.get("/health")
        assert response.status_code == 200
