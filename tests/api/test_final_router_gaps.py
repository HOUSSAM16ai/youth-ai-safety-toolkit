"""Tests for final remaining gaps in API routers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.routers.customer_chat import get_customer_service, get_db
from app.api.routers.customer_chat import router as customer_router
from app.core.domain.user import User
from app.services.auth.ws_auth import (
    _extract_token_from_protocols,
    _parse_protocol_header,
    extract_websocket_auth,
)
from app.services.boundaries.customer_chat_boundary_service import CustomerChatBoundaryService


@pytest.fixture
def customer_app():
    app = FastAPI()
    app.include_router(customer_router)
    return app


# --- Customer Chat Tests ---
def test_customer_ws_auth_fail(customer_app):
    client = TestClient(customer_app)
    mock_service = AsyncMock(spec=CustomerChatBoundaryService)
    # Simulate auth failure
    mock_service.validate_ws_auth.side_effect = HTTPException(status_code=401, detail="Missing auth")
    customer_app.dependency_overrides[get_customer_service] = lambda: mock_service

    # Expect disconnection with 4401 (or 4403 based on code)
    # The router catches 401 and closes with 4401
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/chat/ws"):
            pass
    assert exc.value.code == 4401


def test_customer_ws_decode_fail(customer_app):
    # Same as auth fail, just different detail, but handled same by mock
    client = TestClient(customer_app)
    mock_service = AsyncMock(spec=CustomerChatBoundaryService)
    mock_service.validate_ws_auth.side_effect = HTTPException(status_code=401, detail="Invalid token")
    customer_app.dependency_overrides[get_customer_service] = lambda: mock_service

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/chat/ws"):
            pass
    assert exc.value.code == 4401


def test_customer_ws_admin(customer_app):
    # Should fail because admin is not allowed on customer chat
    client = TestClient(customer_app)
    mock_service = AsyncMock(spec=CustomerChatBoundaryService)
    # validate_ws_auth raises 403 for admin
    mock_service.validate_ws_auth.side_effect = HTTPException(status_code=403, detail="Admin not allowed")
    customer_app.dependency_overrides[get_customer_service] = lambda: mock_service

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/chat/ws"):
            pass
    assert exc.value.code == 4403


def test_customer_ws_empty_question(customer_app):
    client = TestClient(customer_app)
    mock_user = MagicMock(spec=User)
    mock_user.is_active = True
    mock_user.is_admin = False

    mock_service = AsyncMock(spec=CustomerChatBoundaryService)
    mock_service.validate_ws_auth.return_value = (mock_user, "jwt")

    customer_app.dependency_overrides[get_customer_service] = lambda: mock_service

    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_json({"question": ""})
        data = ws.receive_json()
        assert data["type"] == "error"
        # Adjusted assertion to match likely error message structure
        assert "required" in str(data["payload"])


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

    with patch("app.services.auth.ws_auth.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "production"
        token, _proto = extract_websocket_auth(mock_ws)
        assert token is None


def test_extract_websocket_auth_success():
    mock_ws = MagicMock()
    mock_ws.headers = {"sec-websocket-protocol": "jwt, my_secret_token"}

    token, proto = extract_websocket_auth(mock_ws)
    assert token == "my_secret_token"
    assert proto == "jwt"
