"""اختبارات رحلة تركيبية لخدمة Conversation عبر HTTP وWebSocket."""

from __future__ import annotations

from fastapi.testclient import TestClient

from microservices.conversation_service.main import app


def test_conversation_health_and_http_chat() -> None:
    """يتأكد أن الخدمة الجديدة تقدم health وHTTP chat بشكل متوافق مبدئيًا."""
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "conversation-service"

    chat = client.get("/api/chat/messages")
    assert chat.status_code == 200
    assert chat.json()["status"] == "ok"


def test_conversation_ws_synthetic_journey_customer() -> None:
    """يراقب رحلة WS: اتصال ثم إرسال question ثم استقبال response envelope."""
    with TestClient(app).websocket_connect("/api/chat/ws") as ws:
        ws.send_json({"question": "hello"})
        payload = ws.receive_json()

    assert payload["status"] == "ok"
    assert payload["response"] == "conversation-service:hello"
    assert payload["route_id"] == "chat_ws_customer"
