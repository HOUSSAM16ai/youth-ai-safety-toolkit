"""اختبارات توحيد سلطة WebSocket بين مساري الأدمن والعملاء."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient


async def _streaming_success(*args, **kwargs):
    yield {"type": "assistant_delta", "payload": {"content": "مرحبا"}}
    yield {"type": "assistant_final", "payload": {"content": "تم"}}


def test_customer_and_admin_use_same_modern_streaming_path(client: TestClient) -> None:
    """يتحقق من أن المسارين يرسلان نفس نمط الأحداث عبر السلطة الموحدة."""

    customer_actor = SimpleNamespace(id=101, is_admin=False, is_active=True)
    admin_actor = SimpleNamespace(id=202, is_admin=True, is_active=True)

    with patch(
        "app.services.chat.websocket_authority._resolve_actor",
        side_effect=[(customer_actor, "jwt"), (admin_actor, "jwt")],
    ), patch(
        "app.services.chat.websocket_authority.orchestrator_client.chat_with_agent",
        side_effect=[_streaming_success(), _streaming_success()],
    ):
        with client.websocket_connect("/api/chat/ws") as customer_ws:
            customer_ws.send_json({"question": "hello"})
            assert customer_ws.receive_json()["type"] == "assistant_delta"
            assert customer_ws.receive_json()["type"] == "assistant_final"

        with client.websocket_connect("/admin/api/chat/ws") as admin_ws:
            admin_ws.send_json({"question": "hello"})
            assert admin_ws.receive_json()["type"] == "assistant_delta"
            assert admin_ws.receive_json()["type"] == "assistant_final"


def test_customer_route_rejects_admin_accounts(client: TestClient) -> None:
    """يتحقق من حدود الدور لمسار العميل بعد التوحيد."""

    admin_actor = SimpleNamespace(id=303, is_admin=True, is_active=True)

    with patch(
        "app.services.chat.websocket_authority._resolve_actor",
        return_value=(admin_actor, "jwt"),
    ):
        with client.websocket_connect("/api/chat/ws") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "error"
            assert message["payload"]["status_code"] == 403


def test_admin_route_rejects_standard_accounts(client: TestClient) -> None:
    """يتحقق من حدود الدور لمسار الأدمن بعد التوحيد."""

    customer_actor = SimpleNamespace(id=404, is_admin=False, is_active=True)

    with patch(
        "app.services.chat.websocket_authority._resolve_actor",
        return_value=(customer_actor, "jwt"),
    ):
        with client.websocket_connect("/admin/api/chat/ws") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "error"
            assert message["payload"]["status_code"] == 403


def test_mission_complex_intent_is_normalized_for_orchestrator(client: TestClient) -> None:
    """يتحقق من تحويل mission_type القادم من الواجهة إلى صيغة intent المعتمدة."""

    admin_actor = SimpleNamespace(id=505, is_admin=True, is_active=True)
    captured_context: dict[str, object] = {}

    async def _capture_stream(*args, **kwargs):
        nonlocal captured_context
        context_payload = kwargs.get("context")
        if isinstance(context_payload, dict):
            captured_context = context_payload.copy()
        yield {"type": "assistant_delta", "payload": {"content": "ok"}}

    with patch(
        "app.services.chat.websocket_authority._resolve_actor",
        return_value=(admin_actor, "jwt"),
    ), patch(
        "app.services.chat.websocket_authority.orchestrator_client.chat_with_agent",
        side_effect=_capture_stream,
    ):
        with client.websocket_connect("/admin/api/chat/ws") as websocket:
            websocket.send_json({"question": "execute", "mission_type": "mission_complex"})
            assert websocket.receive_json()["type"] == "assistant_delta"

    assert captured_context.get("intent") == "MISSION_COMPLEX"
