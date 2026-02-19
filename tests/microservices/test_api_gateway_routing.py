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
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert str(settings.PLANNING_AGENT_URL) in str(args[1])  # target_url
    assert "test" in args[2]  # path (stripped prefix)


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_unknown_route_returns_404(mock_forward):
    """
    Verify that requests to unknown routes return a 404 from the Gateway, NOT the Monolith.
    """
    response = client.get("/unknown/route")

    # Verify response
    assert response.status_code == 404
    assert response.json()["error"] == "Microservice not found"

    # Verify forward was NOT called (we should not hit the monolith)
    assert not mock_forward.called


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_legacy_security_route_proxies_to_monolith(mock_forward):
    """
    Verify that legacy security routes (/api/security/*) are proxied to the Monolith.
    """
    mock_forward.return_value = JSONResponse(content={"status": "auth_ok"})

    response = client.post("/api/security/login")

    assert response.status_code == 200
    assert response.json() == {"status": "auth_ok"}

    # Verify forward was called with CORE_KERNEL_URL and full path
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert str(settings.CORE_KERNEL_URL) in str(args[1])
    # The path passed to forward should reconstruct the full legacy path
    # My implementation: f"api/security/{path}" -> api/security/login
    assert args[2] == "api/security/login"


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_legacy_admin_route_proxies_to_monolith(mock_forward):
    """
    Verify that legacy admin routes (/admin/*) are proxied to the Monolith.
    """
    mock_forward.return_value = JSONResponse(content={"status": "admin_ok"})

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert response.json() == {"status": "admin_ok"}

    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert str(settings.CORE_KERNEL_URL) in str(args[1])
    assert args[2] == "admin/dashboard"
