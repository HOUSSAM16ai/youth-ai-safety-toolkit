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
def test_unknown_route_returns_404(mock_forward):
    """
    Verify that requests to unknown routes return 404 and are NOT forwarded.
    """
    # This test is expected to FAIL or PASS depending on current implementation.
    # Current implementation: forwarded to core_kernel (catch-all).
    # Desired implementation: 404.

    # Mock response for the catch-all case (if it runs)
    from fastapi.responses import JSONResponse

    mock_forward.return_value = JSONResponse(content={"status": "fallback"})

    response = client.get("/unknown/route")

    # If the catch-all route exists, this will be 200 (fallback)
    # If the catch-all route is removed, this will be 404.

    # We assert 404 because that is the Goal state.
    if response.status_code == 200:
        # Check if it was the fallback
        assert response.json() == {"status": "fallback"}
        print("\n[DEBUG] Caught fallback to core-kernel. This confirms the issue exists.")
        # Fail the test to indicate we haven't fixed it yet?
        # Or assert 404 and let it fail?
        # Let's assert 404.
        assert response.status_code == 404, "Route was forwarded to Monolith instead of 404!"

    assert response.status_code == 404
    assert not mock_forward.called
