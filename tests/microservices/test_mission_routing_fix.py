import os
import jwt
from unittest.mock import AsyncMock, patch

# Set required environment variable before importing settings
os.environ["SECRET_KEY"] = "test_secret_key"

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from microservices.api_gateway.config import settings
from microservices.api_gateway.main import app, proxy_handler
from microservices.api_gateway.security import verify_gateway_request

client = TestClient(app)

# Helper to generate token
def get_valid_token():
    return jwt.encode({"sub": "test-user"}, settings.SECRET_KEY, algorithm="HS256")

def get_auth_headers():
    return {"Authorization": f"Bearer {get_valid_token()}"}


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_mission_route_proxies_to_orchestrator(mock_forward):
    """
    Verify that requests to /api/v1/missions/* are correctly forwarded to the Orchestrator Service.
    This test verifies the fix for the 'Distributed Monolith' issue.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    # Test the root listing endpoint
    response = client.get("/api/v1/missions", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify forward was called with correct args
    assert mock_forward.called
    args, _ = mock_forward.call_args
    # TARGET: Should be Orchestrator, NOT Core Kernel
    assert settings.ORCHESTRATOR_SERVICE_URL in args
    # PATH: Should include 'missions' prefix
    assert "missions" in args


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_mission_detail_route_proxies_to_orchestrator(mock_forward):
    """
    Verify that requests to /api/v1/missions/{id} are correctly forwarded to the Orchestrator Service.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/v1/missions/123", headers=get_auth_headers())

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.ORCHESTRATOR_SERVICE_URL in args
    # PATH: Should be 'missions/123'
    assert "missions/123" in args
