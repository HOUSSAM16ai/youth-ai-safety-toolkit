"""اختبارات تكامل لتوجيه WebSocket في API Gateway مع حارس legacy + TTL."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from microservices.api_gateway import main
from microservices.api_gateway.config import settings


def test_chat_ws_uses_legacy_target_when_flag_enabled(monkeypatch) -> None:
    """يتأكد أن WS chat يستهدف legacy عندما يكون العلم مفعّلًا."""
    routed_targets: list[str] = []

    async def fake_ws_proxy(websocket, target_url: str) -> None:
        await websocket.accept()
        routed_targets.append(target_url)
        await websocket.send_text("ok")
        await websocket.close()

    monkeypatch.setattr(main, "websocket_proxy", fake_ws_proxy)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_USE_LEGACY", True)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_LEGACY_TTL", "2099-12-31T23:59:59+00:00")

    with TestClient(main.app).websocket_connect("/api/chat/ws") as ws:
        assert ws.receive_text() == "ok"

    assert routed_targets
    assert routed_targets[0].startswith("ws://core-kernel:8000/")


def test_chat_ws_avoids_legacy_target_when_flag_disabled(monkeypatch) -> None:
    """يتأكد أن WS chat لا يذهب للنواة القديمة عند تعطيل العلم واستخدام الهدف المرشح."""
    routed_targets: list[str] = []

    async def fake_ws_proxy(websocket, target_url: str) -> None:
        await websocket.accept()
        routed_targets.append(target_url)
        await websocket.send_text("ok")
        await websocket.close()

    monkeypatch.setattr(main, "websocket_proxy", fake_ws_proxy)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_USE_LEGACY", False)
    monkeypatch.setattr(settings, "CONVERSATION_WS_URL", "ws://conversation-service:8010")
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT", 100)

    with TestClient(main.app).websocket_connect("/api/chat/ws") as ws:
        assert ws.receive_text() == "ok"

    assert routed_targets == ["ws://conversation-service:8010/api/chat/ws"]


def test_chat_ws_legacy_flag_requires_valid_ttl(monkeypatch) -> None:
    """يتأكد أن تفعيل legacy مع TTL منتهي يفشل سريعًا لحماية الإنتاج من fallback دائم."""

    async def fake_ws_proxy(websocket, target_url: str) -> None:
        await websocket.accept()
        await websocket.close()

    monkeypatch.setattr(main, "websocket_proxy", fake_ws_proxy)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_USE_LEGACY", True)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_LEGACY_TTL", "2001-01-01T00:00:00+00:00")

    with pytest.raises(RuntimeError, match="expired"):
        with TestClient(main.app).websocket_connect("/api/chat/ws"):
            pass


def test_chat_ws_routes_to_orchestrator_when_rollout_zero(monkeypatch) -> None:
    """يتأكد أن canary بنسبة 0% يوجّه إلى orchestrator مع تعطيل legacy."""
    routed_targets: list[str] = []

    async def fake_ws_proxy(websocket, target_url: str) -> None:
        await websocket.accept()
        routed_targets.append(target_url)
        await websocket.send_text("ok")
        await websocket.close()

    monkeypatch.setattr(main, "websocket_proxy", fake_ws_proxy)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_USE_LEGACY", False)
    monkeypatch.setattr(settings, "ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT", 0)
    monkeypatch.setattr(settings, "ORCHESTRATOR_SERVICE_URL", "http://orchestrator-service:8006")

    with TestClient(main.app).websocket_connect("/api/chat/ws") as ws:
        assert ws.receive_text() == "ok"

    assert routed_targets == ["ws://orchestrator-service:8006/api/chat/ws"]
