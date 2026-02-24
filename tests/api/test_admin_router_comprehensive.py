"""Comprehensive tests for Admin router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.routers.admin import (
    get_admin_service,
    get_ai_client,
    get_chat_dispatcher,
    get_current_user_id,
    get_db,
    get_session_factory,
    router,
)
from app.core.domain.user import User
from app.services.boundaries.admin_chat_boundary_service import AdminChatBoundaryService


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

    # Mock the boundary service
    mock_service = AsyncMock(spec=AdminChatBoundaryService)
    # validate_ws_auth should raise HTTPException 403 or similar if not admin,
    # OR return the user and the router checks it.
    # In my implementation, validate_ws_auth RAISES exception if not admin.
    mock_service.validate_ws_auth.side_effect = HTTPException(
        status_code=403, detail="Admin access required"
    )

    app.dependency_overrides[get_admin_service] = lambda: mock_service

    # Expect immediate disconnection with code 4403
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/admin/api/chat/ws") as websocket:
            websocket.receive_json()
    assert exc.value.code == 4403


def test_chat_stream_ws_empty_question(app):
    client = TestClient(app)
    mock_actor = MagicMock(spec=User)
    mock_actor.is_active = True
    mock_actor.is_admin = True

    # Mock the boundary service
    mock_service = AsyncMock(spec=AdminChatBoundaryService)
    mock_service.validate_ws_auth.return_value = (mock_actor, "json")

    app.dependency_overrides[get_admin_service] = lambda: mock_service

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

    # Mock the boundary service
    mock_service = AsyncMock(spec=AdminChatBoundaryService)
    mock_service.validate_ws_auth.return_value = (mock_actor, "json")

    app.dependency_overrides[get_admin_service] = lambda: mock_service

    def mock_dependency_factory():
        return MagicMock()

    app.dependency_overrides[get_ai_client] = mock_dependency_factory
    app.dependency_overrides[get_chat_dispatcher] = mock_dependency_factory
    app.dependency_overrides[get_session_factory] = lambda: AsyncMock

    with patch(
        "app.services.chat.orchestrator.ChatOrchestrator.dispatch",
        side_effect=HTTPException(status_code=400, detail="Orchestrator error"),
    ):
        with client.websocket_connect("/admin/api/chat/ws") as websocket:
            websocket.send_json({"question": "test"})
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Orchestrator error" in data["payload"]["details"]
