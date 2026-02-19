import os
from unittest.mock import AsyncMock, patch

# Set required environment variable before importing settings
os.environ["SECRET_KEY"] = "test_secret_key"

from fastapi.testclient import TestClient

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
    # Mock the return value to be a valid StreamingResponse-like object or just pass
    # Since forward returns a StreamingResponse, we need to mock that if the view uses it.
    # But the view just returns whatever forward returns.
    # Let's mock a simple response.
    from fastapi.responses import JSONResponse

    mock_forward.return_value = JSONResponse(content={"status": "ok"})

    response = client.get("/api/v1/planning/test")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify forward was called with correct args
    # args: request, target_url, path, service_token
    # We can check target_url
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert "http://planning-agent:8000" in args  # target_url
    assert "test" in args  # path (stripped prefix)


@patch.object(proxy_handler, "forward", new_callable=AsyncMock)
def test_unknown_route_proxies_to_monolith(mock_forward):
    """
    Verify that requests to unknown routes are forwarded to the Core Kernel (Monolith).
    """
    from fastapi.responses import JSONResponse
    from microservices.api_gateway.config import settings

    # Mock the return value from the Monolith
    mock_forward.return_value = JSONResponse(content={"status": "monolith_response"})

    response = client.get("/unknown/route")

    # Verify response
    assert response.status_code == 200
    assert response.json() == {"status": "monolith_response"}

    # Verify forward was called with CORE_KERNEL_URL
    assert mock_forward.called
    args, _ = mock_forward.call_args
    assert settings.CORE_KERNEL_URL in args  # target_url should be the kernel
    assert "unknown/route" in args  # path
