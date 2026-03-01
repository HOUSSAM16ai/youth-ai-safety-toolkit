from collections.abc import AsyncGenerator
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.domain.chat import CustomerConversation
from app.core.domain.models import CustomerMessage, MessageRole
from app.core.domain.user import User
from app.core.settings.base import get_settings
from app.infrastructure.clients.orchestrator_client import orchestrator_client


async def _create_user_and_token(db_session: AsyncSession, email: str) -> str:
    """ينشئ مستخدم اختبار مباشرةً ويعيد رمز JWT صالحًا دون الاعتماد على خدمات خارجية."""

    insert_statement = text(
        """
        INSERT INTO users (
            external_id,
            full_name,
            email,
            password_hash,
            is_admin,
            is_active,
            status
        )
        VALUES (:external_id, :full_name, :email, :password_hash, :is_admin, :is_active, :status)
        """
    )
    result = await db_session.execute(
        insert_statement,
        {
            "external_id": f"test-{email}",
            "full_name": "Student User",
            "email": email,
            "password_hash": "not-used-in-this-test",
            "is_admin": False,
            "is_active": True,
            "status": "active",
        },
    )
    await db_session.commit()

    user_id = int(result.lastrowid)
    return jwt.encode({"sub": str(user_id)}, get_settings().SECRET_KEY, algorithm="HS256")


def _consume_stream_until_terminal(websocket: object) -> list[dict[str, object]]:
    """يجمع أحداث البث حتى ظهور حدث نهائي أو رسالة خطأ."""

    messages: list[dict[str, object]] = []
    for _ in range(8):
        payload = websocket.receive_json()
        messages.append(payload)
        event_type = str(payload.get("type", ""))
        if event_type in {"assistant_final", "assistant_error", "assistant_fallback", "error"}:
            break
    return messages


@pytest.mark.asyncio
async def test_customer_chat_stream_delivers_final_message(
    test_app, db_session: AsyncSession
) -> None:
    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        yield {"type": "assistant_delta", "payload": {"content": "Hello"}}
        yield {"type": "assistant_final", "payload": {"content": "Hello learner"}}

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    try:
        with patch.object(orchestrator_client, "chat_with_agent", side_effect=mock_chat_with_agent):
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test"):
                token = await _create_user_and_token(db_session, "student-chat@example.com")

            with TestClient(test_app) as client:
                with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                    websocket.send_json({"question": "Explain math vectors"})
                    messages = _consume_stream_until_terminal(websocket)
    finally:
        test_app.dependency_overrides.clear()

    assert any(message.get("type") == "assistant_delta" for message in messages)
    assert any(message.get("type") == "assistant_final" for message in messages)


@pytest.mark.asyncio
async def test_customer_chat_enforces_ownership(test_app, db_session: AsyncSession) -> None:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
            token_owner = await _create_user_and_token(db_session, "owner@example.com")
            token_other = await _create_user_and_token(db_session, "other@example.com")

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
async def test_customer_chat_returns_error_on_stream_failure(
    test_app,
    db_session: AsyncSession,
) -> None:
    async def mock_chat_with_agent(**kwargs: object) -> AsyncGenerator[dict[str, object], None]:
        if False:
            yield {"type": "assistant_final", "payload": {"content": "unused"}}
        raise RuntimeError("stream failed")

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    try:
        with patch.object(orchestrator_client, "chat_with_agent", side_effect=mock_chat_with_agent):
            async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test"):
                token = await _create_user_and_token(db_session, "fallback@example.com")

            with TestClient(test_app) as client:
                with client.websocket_connect(f"/api/chat/ws?token={token}") as websocket:
                    websocket.send_json({"question": "Explain math vectors"})
                    messages = _consume_stream_until_terminal(websocket)
    finally:
        test_app.dependency_overrides.clear()

    assert any(message.get("type") == "error" for message in messages)
