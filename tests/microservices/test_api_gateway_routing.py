import os
from unittest.mock import AsyncMock, patch

# Set required environment variable before importing settings
os.environ["SECRET_KEY"] = "test_secret_key"

from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from microservices.api_gateway.config import settings
from microservices.api_gateway.main import app, proxy_handler
from microservices.api_gateway.security import verify_gateway_request

client = TestClient(app)


# Override security dependency
async def override_verify_gateway_request():
    return {"sub": "test-user"}


app.dependency_overrides[verify_gateway_request] = override_verify_gateway_request


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_planning_route_proxies_correctly(mock_forward):
    """
    Verify that requests to /api/v1/planning/* are correctly forwarded to the planning agent.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/v1/planning/test")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify forward was called with correct args
    # args: request, target_url, path, service_token
    # We can check target_url
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert "http://planning-agent:8001" in args or settings.PLANNING_AGENT_URL in args  # target_url
    assert "test" in args  # path (stripped prefix)


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_unknown_route_returns_404(mock_forward):
    """
    Verify that requests to unknown routes return 404 and are NOT forwarded.
    This confirms the removal of the catch-all proxy.
    """
    response = client.get("/unknown/route")

    assert response.status_code == 404
    assert not mock_forward.called


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_admin_route_proxies_to_user_service(mock_forward):
    """
    Verify that requests to /admin/* are forwarded to the User Service.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.USER_SERVICE_URL in args  # target_url
    # The path passed to forward should include the prefix for legacy routes as we construct it manually
    assert "api/v1/admin/users" in args  # path


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_chat_route_proxies_to_monolith(mock_forward):
    """
    Verify that requests to /api/chat/* are forwarded to the Core Kernel.
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/chat/history")

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.CORE_KERNEL_URL in args
    assert "api/chat/history" in args


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_legacy_v1_fallback(mock_forward):
    """
    Verify that unmatched /api/v1/* requests fall back to the Monolith (e.g. CRUD).
    """
    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    # /api/v1/planning is matched by specific route, so try something else
    response = client.get("/api/v1/random-crud/item")

    assert response.status_code == 200
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.CORE_KERNEL_URL in args
    assert "api/v1/random-crud/item" in args
