"""Tests for final remaining gaps in API routers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.routers.customer_chat import get_db
from app.api.routers.customer_chat import router as customer_router
from app.api.routers.overmind import router as overmind_router
from app.api.routers.ws_auth import (
    _extract_token_from_protocols,
    _parse_protocol_header,
    extract_websocket_auth,
)
from app.core.domain.user import User


@pytest.fixture
def overmind_app():
    app = FastAPI()
    app.include_router(overmind_router)
    return app


@pytest.fixture
def customer_app():
    app = FastAPI()
    app.include_router(customer_router)
    return app


# --- Overmind Tests ---
def test_create_mission_error(overmind_app):
    client = TestClient(overmind_app)
    # Patch start_mission directly as it is used in the router
    with patch("app.api.routers.overmind.start_mission", side_effect=Exception("DB error")):
        response = client.post(
            "/api/v1/overmind/missions", json={"objective": "valid objective length"}
        )
        assert response.status_code == 500


def test_get_mission_not_found(overmind_app):
    client = TestClient(overmind_app)
    # Patch MissionStateManager.get_mission used in the router
    with patch(
        "app.api.routers.overmind.MissionStateManager.get_mission", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None
        response = client.get("/api/v1/overmind/missions/999")
        assert response.status_code == 404


def test_stream_mission_not_found(overmind_app):
    client = TestClient(overmind_app)
    # Mocking session within stream is harder via overrides,
    # but we can mock MissionStateManager.get_mission
    with patch(
        "app.api.routers.overmind.MissionStateManager.get_mission", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None
        # The endpoint /stream seems to be deprecated/removed in favor of /ws.
        # We confirm that it returns 404.
        response = client.get("/api/v1/overmind/missions/999/stream")
        assert response.status_code == 404


# --- Customer Chat Tests ---
def test_customer_ws_auth_fail(customer_app):
    client = TestClient(customer_app)
    with patch("app.api.routers.customer_chat.extract_websocket_auth", return_value=(None, None)):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/chat/ws"):
                pass  # Already closed by server


def test_customer_ws_decode_fail(customer_app):
    client = TestClient(customer_app)
    with patch(
        "app.api.routers.customer_chat.extract_websocket_auth", return_value=("token", "jwt")
    ):
        with patch("app.api.routers.customer_chat.decode_user_id", side_effect=HTTPException(401)):
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/api/chat/ws"):
                    pass


def test_customer_ws_admin(customer_app):
    client = TestClient(customer_app)
    mock_user = MagicMock(spec=User)
    mock_user.is_active = True
    mock_user.is_admin = True
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_user
    customer_app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.routers.customer_chat.extract_websocket_auth", return_value=("token", "jwt")
    ):
        with patch("app.api.routers.customer_chat.decode_user_id", return_value=1):
            with client.websocket_connect("/api/chat/ws") as ws:
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "Admin" in data["payload"]["details"]


def test_customer_ws_empty_question(customer_app):
    client = TestClient(customer_app)
    mock_user = MagicMock(spec=User)
    mock_user.is_active = True
    mock_user.is_admin = False
    mock_db = AsyncMock()
    mock_db.get.return_value = mock_user
    customer_app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.routers.customer_chat.extract_websocket_auth", return_value=("token", "jwt")
    ):
        with patch("app.api.routers.customer_chat.decode_user_id", return_value=1):
            with client.websocket_connect("/api/chat/ws") as ws:
                ws.send_json({"question": ""})
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "required" in data["payload"]["details"]


# --- WS Auth Tests ---
def test_parse_protocol_header():
    assert _parse_protocol_header("jwt, token") == ["jwt", "token"]
    assert _parse_protocol_header("") == []


def test_extract_token_from_protocols():
    assert _extract_token_from_protocols(["jwt"]) is None
    assert _extract_token_from_protocols(["other"]) is None


def test_extract_websocket_auth_fallback_prod():
    mock_ws = MagicMock()
    mock_ws.headers = {}
    mock_ws.query_params = {"token": "fallback"}

    with patch("app.api.routers.ws_auth.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "production"
        token, _proto = extract_websocket_auth(mock_ws)
        assert token is None


def test_extract_websocket_auth_success():
    mock_ws = MagicMock()
    mock_ws.headers = {"sec-websocket-protocol": "jwt, my_secret_token"}

    token, proto = extract_websocket_auth(mock_ws)
    assert token == "my_secret_token"
    assert proto == "jwt"
