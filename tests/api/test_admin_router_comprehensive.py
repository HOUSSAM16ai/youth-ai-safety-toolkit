"""Comprehensive tests for Admin router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routers.admin import (
    get_current_user_id,
    get_db,
    router,
)
from app.core.domain.user import User


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_db():
    return AsyncMock()


def test_get_actor_user_not_found(client, mock_db):
    client.app.dependency_overrides[get_db] = lambda: mock_db
    client.app.dependency_overrides[get_current_user_id] = lambda: 999
    mock_db.get.return_value = None

    response = client.get("/admin/api/chat/latest")
    assert response.status_code == 401
    assert "User not found" in response.json()["detail"]


def test_get_actor_user_inactive(client, mock_db):
    client.app.dependency_overrides[get_db] = lambda: mock_db
    client.app.dependency_overrides[get_current_user_id] = lambda: 1

    user = MagicMock(spec=User)
    user.is_active = False
    mock_db.get.return_value = user

    response = client.get("/admin/api/chat/latest")
    assert response.status_code == 403
    assert "User inactive" in response.json()["detail"]


def test_get_latest_chat_not_admin(client, mock_db):
    client.app.dependency_overrides[get_db] = lambda: mock_db
    client.app.dependency_overrides[get_current_user_id] = lambda: 1

    user = MagicMock(spec=User)
    user.is_active = True
    user.is_admin = False
    mock_db.get.return_value = user
    # Mock refresh and expunge
    mock_db.refresh = AsyncMock()
    mock_db.expunge = MagicMock()

    response = client.get("/admin/api/chat/latest")
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


def test_chat_stream_ws_not_admin(app):
    client = TestClient(app)
    mock_actor = MagicMock(spec=User)
    mock_actor.is_active = True
    mock_actor.is_admin = False

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db
    # Mock extract_websocket_auth to return a token
    with patch(
        "app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")
    ):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            with client.websocket_connect("/admin/api/chat/ws") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Standard accounts" in data["payload"]["details"]


def test_chat_stream_ws_empty_question(app):
    client = TestClient(app)
    mock_actor = MagicMock(spec=User)
    mock_actor.is_active = True
    mock_actor.is_admin = True

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db
    with patch(
        "app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")
    ):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            with client.websocket_connect("/admin/api/chat/ws") as websocket:
                websocket.send_json({"question": ""})
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Question is required" in data["payload"]["details"]


def test_chat_stream_ws_orchestrator_error(app):
    client = TestClient(app)
    mock_actor = MagicMock(spec=User)
    mock_actor.is_active = True
    mock_actor.is_admin = True
    mock_actor.id = 1

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")
    ):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            # Patch the orchestrator_client.chat_with_agent method
            with patch(
                "app.api.routers.admin.orchestrator_client.chat_with_agent",
                side_effect=Exception("Connection failed"),
            ):
                with client.websocket_connect("/admin/api/chat/ws") as websocket:
                    websocket.send_json({"question": "test"})
                    # Receive status first (200)
                    status_data = websocket.receive_json()
                    assert status_data["type"] == "status"
                    assert status_data["payload"]["status_code"] == 200

                    data = websocket.receive_json()
                    # Expecting sanitized error response due to exception
                    assert data["type"] == "error"
                    assert "Service unavailable" in data["payload"]["details"]


async def mock_chat_stream(*args, **kwargs):
    yield {"type": "assistant_delta", "payload": {"content": "Hello"}}
    yield {"type": "assistant_final", "payload": {"content": "Hello"}}


def test_chat_stream_ws_success(app):
    client = TestClient(app)
    mock_actor = MagicMock(spec=User)
    mock_actor.is_active = True
    mock_actor.is_admin = True
    mock_actor.id = 1

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")
    ):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            with patch(
                "app.api.routers.admin.orchestrator_client.chat_with_agent",
                side_effect=mock_chat_stream,
            ) as mock_chat:
                with client.websocket_connect("/admin/api/chat/ws") as websocket:
                    websocket.send_json(
                        {"question": "Hello", "mission_type": "mission_complex", "conversation_id": 123}
                    )

                    # Receive status first (200)
                    status_data = websocket.receive_json()
                    assert status_data["type"] == "status"
                    assert status_data["payload"]["status_code"] == 200

                    # Receive delta
                    data1 = websocket.receive_json()
                    assert data1["type"] == "assistant_delta"
                    assert data1["payload"]["content"] == "Hello"

                    # Receive final
                    data2 = websocket.receive_json()
                    assert data2["type"] == "assistant_final"

                    # Verify call arguments
                    mock_chat.assert_called_once()
                    call_args = mock_chat.call_args
                    assert call_args.kwargs["question"] == "Hello"
                    assert call_args.kwargs["user_id"] == 1
                    assert call_args.kwargs["conversation_id"] == 123
                    assert call_args.kwargs["context"] == {"role": "admin", "intent": "mission_complex"}
