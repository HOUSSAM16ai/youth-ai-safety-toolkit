"""Comprehensive tests for Admin router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routers.admin import (
    router,
    # The following are internal dependencies we need to override or mock
    get_db,
    get_current_user_id,
    # These were removed in refactor, so we don't import them anymore
    # get_ai_client,
    # get_chat_dispatcher,
)
from app.core.domain.user import User

# Import the orchestrator_client to patch it
from app.infrastructure.clients.orchestrator_client import orchestrator_client


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
    mock_session = AsyncMock()
    # Mocking get/refresh/expunge for standard session operations
    mock_session.get.return_value = None
    mock_session.refresh = AsyncMock()
    mock_session.expunge = MagicMock()
    return mock_session


def test_get_actor_user_not_found(client, mock_db):
    # Override the dependency to return our mock
    client.app.dependency_overrides[get_db] = lambda: mock_db

    # We must patch the dependency logic itself or ensuring the flow reaches db.get
    # 'get_actor_user' depends on 'get_current_user_id' and 'get_db'.
    # If we want to test 'get_actor_user', we should call the endpoint that uses it.
    # The endpoint '/admin/api/chat/latest' uses 'get_actor_user'.

    # We mock get_current_user_id to return a valid ID so it proceeds to get_actor_user
    client.app.dependency_overrides[get_current_user_id] = lambda: 999

    mock_db.get.return_value = None  # User not found in DB

    response = client.get("/admin/api/chat/latest")
    # The router raises 401 if user is None
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
    """
    Test that even if authentication passes, non-admin users are rejected
    at the endpoint level (require_roles/checks).
    """
    client.app.dependency_overrides[get_db] = lambda: mock_db
    client.app.dependency_overrides[get_current_user_id] = lambda: 1

    user = MagicMock(spec=User)
    user.is_active = True
    user.is_admin = False  # Not an admin
    mock_db.get.return_value = user

    # The 'get_latest_chat' endpoint checks 'if not actor.is_admin: raise 403'
    response = client.get("/admin/api/chat/latest")
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


def test_chat_stream_ws_not_admin(app):
    """
    Test WebSocket connection rejection for non-admin users.
    """
    client = TestClient(app)

    mock_actor = MagicMock(spec=User)
    mock_actor.id = 1
    mock_actor.is_active = True
    mock_actor.is_admin = False  # Not an admin

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock token extraction and decoding
    with patch("app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            with client.websocket_connect("/admin/api/chat/ws") as websocket:
                data = websocket.receive_json()
                # Expect error message
                assert data["type"] == "error"
                assert "Standard accounts" in data["payload"]["details"]
                # The socket calls close(code=4403), TestClient might raise or close


def test_chat_stream_ws_empty_question(app):
    """
    Test sending an empty question over WebSocket.
    """
    client = TestClient(app)

    mock_actor = MagicMock(spec=User)
    mock_actor.id = 1
    mock_actor.is_active = True
    mock_actor.is_admin = True

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            with client.websocket_connect("/admin/api/chat/ws") as websocket:
                websocket.send_json({"question": ""})
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "Question is required" in data["payload"]["details"]


def test_chat_stream_ws_orchestrator_error(app):
    """
    Test robust error handling when the Microservice Client fails.
    """
    client = TestClient(app)

    mock_actor = MagicMock(spec=User)
    mock_actor.id = 1
    mock_actor.is_active = True
    mock_actor.is_admin = True

    mock_db = AsyncMock()
    mock_db.get.return_value = mock_actor

    app.dependency_overrides[get_db] = lambda: mock_db

    # In the new architecture, we mock 'orchestrator_client.chat_with_agent'
    # instead of 'ChatOrchestrator.dispatch'.

    async def mock_chat_generator(*args, **kwargs):
        # Simulate an error during streaming
        raise Exception("Microservice unavailable")
        yield  # make it a generator

    with patch("app.api.routers.admin.extract_websocket_auth", return_value=("valid_token", "json")):
        with patch("app.api.routers.admin.decode_user_id", return_value=1):
            # Patch the singleton instance method
            with patch.object(orchestrator_client, "chat_with_agent", side_effect=mock_chat_generator):
                with client.websocket_connect("/admin/api/chat/ws") as websocket:
                    websocket.send_json({"question": "test"})

                    # receive_json should return the error caught by the try/except block in the router
                    data = websocket.receive_json()

                    assert data["type"] == "error"
                    assert "Microservice unavailable" in data["payload"]["details"]
