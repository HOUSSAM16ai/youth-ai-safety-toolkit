from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.domain.chat import CustomerConversation
from app.core.domain.models import CustomerMessage, MessageRole
from app.core.domain.user import User
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


def _consume_stream_until_terminal(websocket: object) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for _ in range(8):
        payload = websocket.receive_json()
        messages.append(payload)
        event_type = str(payload.get("type", ""))
        if event_type in {"assistant_final", "assistant_error", "assistant_fallback", "error"}:
            break
    return messages


@pytest.mark.asyncio
async def test_customer_chat_stream_delivers_final_message(test_app, db_session) -> None:
    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        yield {"type": "assistant_delta", "payload": {"content": "Hello"}}
        yield {"type": "assistant_final", "payload": {"content": "Hello learner"}}

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    try:
        with patch.object(orchestrator_client, "chat_with_agent", side_effect=mock_chat_with_agent):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                token = await _register_and_login(ac, "student-chat@example.com")

                with TestClient(test_app) as client:
                    with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                        websocket.send_json({"question": "Explain math vectors"})
                        messages = _consume_stream_until_terminal(websocket)
    finally:
        test_app.dependency_overrides.clear()

    assert any(message.get("type") == "assistant_delta" for message in messages)
    assert any(message.get("type") == "assistant_final" for message in messages)


@pytest.mark.asyncio
async def test_customer_chat_enforces_ownership(test_app, db_session) -> None:
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            token_owner = await _register_and_login(ac, "owner@example.com")
            token_other = await _register_and_login(ac, "other@example.com")

            owner_user = (
                (await db_session.execute(select(User).where(User.email == "owner@example.com")))
                .scalars()
                .first()
            )
            assert owner_user is not None

            conversation = CustomerConversation(title="Vectors", user_id=owner_user.id)
            db_session.add(conversation)
            await db_session.flush()
            db_session.add(
                CustomerMessage(
                    conversation_id=conversation.id,
                    role=MessageRole.USER,
                    content="Explain vectors",
                )
            )
            await db_session.commit()

            detail_resp = await ac.get(
                f"/api/chat/conversations/{conversation.id}",
                headers={"Authorization": f"Bearer {token_other}"},
            )
            assert detail_resp.status_code == 404
            assert token_owner
    finally:
        test_app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_customer_chat_returns_error_on_stream_failure(test_app, db_session) -> None:
    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        if False:
            yield {"type": "assistant_final", "payload": {"content": "unused"}}
        raise RuntimeError("stream failed")

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    try:
        with patch.object(orchestrator_client, "chat_with_agent", side_effect=mock_chat_with_agent):
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                token = await _register_and_login(ac, "fallback@example.com")

                with TestClient(test_app) as client:
                    with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                        websocket.send_json({"question": "Explain math vectors"})
                        messages = _consume_stream_until_terminal(websocket)
    finally:
        test_app.dependency_overrides.clear()

    assert any(message.get("type") == "error" for message in messages)
