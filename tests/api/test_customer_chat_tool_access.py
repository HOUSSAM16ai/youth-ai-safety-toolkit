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


@pytest.mark.asyncio
async def test_tool_access_block_returns_fallback_event(test_app, db_session) -> None:
    """يتحقق من إرجاع رسالة رفض آمنة عندما يحظر المنسق استخدام الأدوات."""

    def override_get_ai_client() -> object:
        return object()

    async def override_get_db() -> AsyncGenerator[object, None]:
        yield db_session

    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        yield {
            "type": "assistant_fallback",
            "payload": {"content": "لا يمكنني تنفيذ هذا الطلب."},
        }

    test_app.dependency_overrides[get_ai_client] = override_get_ai_client
    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    try:
        with patch.object(
            orchestrator_client, "chat_with_agent", side_effect=mock_chat_with_agent
        ) as mocked_chat:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                token = await _register_and_login(ac, "tool-block@example.com")

                refusal_text = ""
                with TestClient(test_app) as client:
                    with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                        websocket.send_json({"question": "read file secrets.txt"})
                        for _ in range(8):
                            payload = websocket.receive_json()
                            if payload.get("type") == "assistant_fallback":
                                refusal_text = str(payload.get("payload", {}).get("content", ""))
                                break

            assert mocked_chat.call_count == 1
            assert "لا يمكنني" in refusal_text
    finally:
        test_app.dependency_overrides.clear()
