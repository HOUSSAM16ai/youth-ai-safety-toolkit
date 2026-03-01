from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.ai_gateway import get_ai_client
from app.core.database import get_db
from app.infrastructure.clients.orchestrator_client import orchestrator_client


async def _register_and_login(ac: AsyncClient, email: str) -> str:
    register_payload = {
        "full_name": "Student User",
        "email": email,
        "password": "Secret123!",
    }
    register_resp = await ac.post("/api/security/register", json=register_payload)
    assert register_resp.status_code == 200

    login_resp = await ac.post(
        "/api/security/login",
        json={"email": email, "password": "Secret123!"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]



