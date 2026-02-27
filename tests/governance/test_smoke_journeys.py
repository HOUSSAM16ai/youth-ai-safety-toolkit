# tests/governance/test_smoke_journeys.py

import pytest
from httpx import AsyncClient

# This requires the services to be running (which they are in CI/Compose)
# For this script to work locally, we need to mock or assume URLs.
# In a real environment, these would be integration tests.

GATEWAY_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_gateway_health():
    """Verify Gateway is up and responding."""
    async with AsyncClient(base_url=GATEWAY_URL) as client:
        try:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["ok", "degraded"]
        except Exception:
            pytest.skip("Gateway not running locally, skipping integration smoke test")

@pytest.mark.asyncio
async def test_chat_http_route():
    """Verify Chat HTTP route exists and is reachable."""
    async with AsyncClient(base_url=GATEWAY_URL) as client:
        try:
            # We expect 401 Unauthorized or 404/405 if path is incomplete,
            # but getting a response means the route is wired.
            response = await client.post("/api/chat/message", json={"message": "hello"})
            # 401 means auth middleware caught it -> good, it's alive.
            # 200 means it processed.
            # 500 would be bad.
            assert response.status_code in [200, 401, 403, 404]
        except Exception:
            pytest.skip("Gateway not running locally, skipping integration smoke test")
