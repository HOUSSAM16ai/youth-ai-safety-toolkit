"""Tests for final remaining gaps in API routers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.routers.customer_chat import get_db
from app.api.routers.customer_chat import router as customer_router
from app.api.routers.ws_auth import (
    _extract_token_from_protocols,
    _parse_protocol_header,
    extract_websocket_auth,
)
from app.core.domain.user import User


@pytest.fixture
def customer_app():
    app = FastAPI()
    app.include_router(customer_router)
    return app


# --- Customer Chat Tests ---


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
