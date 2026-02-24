import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.core.domain.models import AdminConversation, AdminMessage, MessageRole, User
from app.services.boundaries.admin_chat_boundary_service import AdminChatBoundaryService


# Mock settings
@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.SECRET_KEY = "test_secret"
    return settings


@pytest.fixture
def service(mock_settings):
    db_session = AsyncMock()
    with patch(
        "app.services.boundaries.admin_chat_boundary_service.get_settings",
        return_value=mock_settings,
    ):
        service = AdminChatBoundaryService(db_session)
        service.settings = mock_settings  # Ensure settings are set
        return service


@pytest.mark.asyncio
async def test_validate_auth_header_valid(service, mock_settings):
    token = jwt.encode({"sub": "123"}, mock_settings.SECRET_KEY, algorithm="HS256")
    auth_header = f"Bearer {token}"

    user_id = service.validate_auth_header(auth_header)
    assert user_id == 123


@pytest.mark.asyncio
async def test_validate_auth_header_missing(service):
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header(None)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Authorization header missing"


@pytest.mark.asyncio
async def test_validate_auth_header_invalid_format(service):
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header("InvalidFormat")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid Authorization header format"


@pytest.mark.asyncio
async def test_validate_auth_header_not_bearer(service):
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header("Basic token")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid Authorization header format"


@pytest.mark.asyncio
async def test_validate_auth_header_invalid_token(service):
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header("Bearer invalid_token")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_validate_auth_header_missing_sub(service, mock_settings):
    token = jwt.encode({"foo": "bar"}, mock_settings.SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header(f"Bearer {token}")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token payload"


@pytest.mark.asyncio
async def test_validate_auth_header_invalid_user_id_type(service, mock_settings):
    token = jwt.encode({"sub": "not_an_int"}, mock_settings.SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        service.validate_auth_header(f"Bearer {token}")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid user ID in token"


@pytest.mark.asyncio
async def test_get_or_create_conversation_create_new(service):
    # Need to mock sync method add on AsyncMock
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()
    service.db.refresh = AsyncMock()

    actor = User(id=1, email="u@example.com", full_name="Test", is_admin=True)
    conversation = await service.get_or_create_conversation(user=actor, question="Hello")

    assert conversation.user_id == 1
    assert conversation.title == "Hello"
    service.db.add.assert_called_once()
    service.db.commit.assert_called_once()
    service.db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_conversation_existing(service):
    existing_conv = AdminConversation(id=10, user_id=1, title="Test")
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.is_admin = True

    # Mock database result for sequential calls
    service.db.get = AsyncMock(side_effect=[mock_user, existing_conv])

    conversation = await service.get_or_create_conversation(
        user=mock_user, question="New Q", conversation_id="10"
    )

    assert conversation.id == 10
    assert conversation.title == "Test"


@pytest.mark.asyncio
async def test_get_or_create_conversation_not_found(service):
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.is_admin = True

    # 1. User found, 2. Conversation NOT found
    service.db.get = AsyncMock(side_effect=[mock_user, None])

    with pytest.raises(HTTPException) as exc:
        await service.get_or_create_conversation(
            user=mock_user, question="Q", conversation_id="999"
        )

    assert exc.value.status_code == 404
    # The actual implementation raises "Invalid conversation ID" wrapping the ValueError
    assert exc.value.detail == "Invalid conversation ID"


@pytest.mark.asyncio
async def test_get_or_create_conversation_invalid_id(service):
    with pytest.raises(HTTPException) as exc:
        actor = User(id=1, email="u@example.com", full_name="Test", is_admin=True)
        await service.get_or_create_conversation(
            user=actor, question="Q", conversation_id="invalid"
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid conversation ID format"


@pytest.mark.asyncio
async def test_save_message(service):
    service.db.add = MagicMock()
    service.db.commit = AsyncMock()

    msg = await service.save_message(conversation_id=1, role=MessageRole.USER, content="Hello")

    assert msg.conversation_id == 1
    assert msg.role == MessageRole.USER
    assert msg.content == "Hello"
    service.db.add.assert_called_once()
    service.db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_chat_history(service):
    # Mock messages
    msg1 = AdminMessage(id=1, role=MessageRole.USER, content="Hi")
    msg2 = AdminMessage(id=2, role=MessageRole.ASSISTANT, content="Hello")

    mock_result = MagicMock()
    # History service reverses the list retrieved from DB (which is ordered by desc)
    mock_result.scalars.return_value.all.return_value = [msg2, msg1]
    service.db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.services.admin.chat_persistence.get_system_prompt", new_callable=AsyncMock
    ) as mock_prompt:
        mock_prompt.return_value = "System Prompt"
        history = await service.get_chat_history(conversation_id=1)

    assert len(history) == 3
    assert history[0]["role"] == "system"
    assert history[0]["content"] == "System Prompt"
    assert history[1]["role"] == "user"
    assert history[1]["content"] == "Hi"
    assert history[2]["role"] == "assistant"
    assert history[2]["content"] == "Hello"


@pytest.mark.asyncio
async def test_stream_chat_response_flow(service):
    actor = User(id=1, email="user@example.com", full_name="User", is_admin=True)
    conversation = AdminConversation(id=1, title="Test", user_id=actor.id)
    question = "Hello"
    history = [{"role": "user", "content": "Hi"}]

    # Do NOT use spec=AIClient because it messes up mocking async generator methods
    ai_client = MagicMock()

    # Mock session factory for persistence
    mock_session = AsyncMock()
    # Important: Mock add as synchronous
    mock_session.add = MagicMock()

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    # Mock orchestrator client
    with patch("app.services.admin.chat_streamer.orchestrator_client") as mock_client:
        # The streamer calls orchestrator_client.chat_with_agent, which returns an async generator
        async def mock_chat(*args, **kwargs):
            # Simulate NDJSON events
            yield {"type": "assistant_delta", "payload": {"content": "World"}}
            yield {"type": "assistant_delta", "payload": {"content": "!"}}

        mock_client.chat_with_agent.side_effect = mock_chat

        generator = service.stream_chat_response(
            actor, conversation, question, history, ai_client, mock_session_factory
        )

        events = []
        async for event in generator:
            events.append(event)

        # Verify events
        assert any(event.get("type") == "conversation_init" for event in events)
        # The new streamer passes through "assistant_delta" events but maps them to "delta"
        assert any(
            event.get("type") == "delta" and event.get("payload", {}).get("content") == "World"
            for event in events
        )
        assert any(
            event.get("type") == "delta" and event.get("payload", {}).get("content") == "!"
            for event in events
        )

        # Verify history update (Streamer no longer updates history object in place, it creates clean copy)
        # But we passed history list reference, check if it was modified?
        # Actually streamer method `stream_response` calls `_update_history_with_question` at start.
        # So history reference passed in should be updated.
        # Let's check `AdminChatStreamer.stream_response` implementation.
        # Yes, `self._update_history_with_question(history, question)` is called.
        assert history[-1]["content"] == "Hello"

        # Verify persistence
        await asyncio.sleep(0.1)

        mock_session.add.assert_called()
        args, _ = mock_session.add.call_args
        saved_msg = args[0]
        assert saved_msg.content == "World!"
        assert saved_msg.role == MessageRole.ASSISTANT


@pytest.mark.asyncio
async def test_stream_chat_response_error_handling(service):
    actor = User(id=1, email="user@example.com", full_name="User", is_admin=True)
    conversation = AdminConversation(id=1, title="Test", user_id=actor.id)
    question = "Hello"
    history = []
    ai_client = MagicMock()

    # Mock session factory with proper async mocks
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    with patch("app.services.admin.chat_streamer.orchestrator_client") as mock_client:
        mock_client.chat_with_agent.side_effect = Exception("Orchestrator Failure")

        generator = service.stream_chat_response(
            actor, conversation, question, history, ai_client, mock_session_factory
        )

        events = []
        async for event in generator:
            events.append(event)

        assert any(
            event.get("type") == "error"
            and "Orchestrator Failure" in str(event.get("payload", {}).get("details"))
            for event in events
        )
