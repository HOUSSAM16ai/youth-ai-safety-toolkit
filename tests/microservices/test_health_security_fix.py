import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Set environment variables to avoid validation errors or side effects
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["PLANNING_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["MEMORY_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["USER_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


def test_planning_agent_health_security():
    """
    Verify that /health is public and other routes are protected in Planning Agent.
    """
    from microservices.planning_agent.main import create_app as create_planning_app

    # Mock init_db to prevent database connection attempts during startup
    with patch("microservices.planning_agent.main.init_db", new_callable=MagicMock):
        # Create app with default settings (DEBUG=False by default)
        app = create_planning_app()
        client = TestClient(app)

        # 1. Health check - Should be PUBLIC (200 OK)
        # If this fails with 401/403, the fix is needed.
        response_health = client.get("/health")

        # 2. Protected route - Should be PROTECTED (401 Unauthorized or 403 Forbidden)
        response_protected = client.get("/plans")

        print(f"Planning Agent - /health status: {response_health.status_code}")
        print(f"Planning Agent - /plans status: {response_protected.status_code}")

        # Assertions
        # The goal is for health to be 200.
        # Currently (before fix), it is likely 401.
        # We assert what we WANT (200). If it fails, it confirms the bug exists (or the fix is verified).
        assert response_health.status_code == 200, (
            f"Planning Agent /health should be public (200), but got {response_health.status_code}"
        )

        assert response_protected.status_code in [401, 403], (
            f"Planning Agent /plans should be protected (401/403), but got {response_protected.status_code}"
        )


def test_memory_agent_health_security():
    """
    Verify that /health is public and other routes are protected in Memory Agent.
    """
    from microservices.memory_agent.main import create_app as create_memory_app

    with patch("microservices.memory_agent.main.init_db", new_callable=MagicMock):
        app = create_memory_app()
        client = TestClient(app)

        response_health = client.get("/health")
        # Try a protected route (search requires query params usually, but auth fails first)
        response_protected = client.get("/memories/search")

        print(f"Memory Agent - /health status: {response_health.status_code}")

        assert response_health.status_code == 200, (
            f"Memory Agent /health should be public (200), but got {response_health.status_code}"
        )

        assert response_protected.status_code in [401, 403], (
            f"Memory Agent /memories/search should be protected (401/403), but got {response_protected.status_code}"
        )


def test_user_service_health_security():
    """
    Verify that /health is public and other routes are protected in User Service.
    """
    from microservices.user_service.main import create_app as create_user_app

    with patch("microservices.user_service.main.init_db", new_callable=MagicMock):
        app = create_user_app()
        client = TestClient(app)

        response_health = client.get("/health")
        response_protected = client.get("/users")

        print(f"User Service - /health status: {response_health.status_code}")

        assert response_health.status_code == 200, (
            f"User Service /health should be public (200), but got {response_health.status_code}"
        )

        assert response_protected.status_code in [401, 403], (
            f"User Service /users should be protected (401/403), but got {response_protected.status_code}"
        )
