import os
from unittest.mock import AsyncMock, patch

import jwt

# Set required environment variable before importing settings
os.environ["SECRET_KEY"] = "test-secret-key-that-is-very-long-and-secure-enough-for-tests-v4"

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from microservices.api_gateway.config import settings
from microservices.api_gateway.main import app, proxy_handler

client = TestClient(app)


# Helper to generate token
def get_valid_token():
    return jwt.encode({"sub": "test-user"}, settings.SECRET_KEY, algorithm="HS256")


def get_auth_headers():
    return {"Authorization": f"Bearer {get_valid_token()}"}


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_planning_route_proxies_correctly(mock_forward):
    """
    Verify that requests to /api/v1/planning/* are correctly forwarded to the planning agent.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/v1/planning/test", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify forward was called with correct args
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert "http://planning-agent:8001" in args or settings.PLANNING_AGENT_URL in args
    assert "test" in args


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_unknown_route_returns_404(mock_forward):
    """
    Verify that requests to unknown routes return 404 and are NOT forwarded.
    """
    response = client.get("/unknown/route", headers=get_auth_headers())

    assert response.status_code == 404
    assert not mock_forward.called


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_admin_route_proxies_to_user_service(mock_forward):
    """
    Verify that requests to /admin/* are forwarded to the User Service.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/admin/users", headers=get_auth_headers())

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.USER_SERVICE_URL in args
    assert "api/v1/admin/users" in args


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_chat_route_proxies_to_modern_service(mock_forward):
    """
    Verify that requests to /api/chat/* are forwarded to orchestrator/conversation (never monolith).
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/chat/history", headers=get_auth_headers())

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.ORCHESTRATOR_SERVICE_URL in args or settings.CONVERSATION_SERVICE_URL in args
    assert "api/chat/history" in args


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_legacy_v1_no_fallback(mock_forward):
    """
    Verify that unmatched /api/v1/* requests do NOT fall back to the Monolith.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/v1/random-crud/item", headers=get_auth_headers())

    assert response.status_code == 404
    assert not mock_forward.called
