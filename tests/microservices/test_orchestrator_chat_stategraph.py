"""اختبارات سلوكية لمسارات chat داخل orchestrator مع عمود StateGraph."""

from __future__ import annotations

from fastapi.testclient import TestClient

from microservices.orchestrator_service.main import app
from microservices.orchestrator_service.src.api import routes


class _FakeTimelineEvent:
    """يمثل حدثًا زمنيًا بسيطًا متوافقًا مع واجهة النموذج."""

    def __init__(self, agent: str) -> None:
        self._agent = agent

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        """يعيد تمثيل الحدث بصيغة قاموس JSON."""
        return {"agent": self._agent, "mode": mode}


class _FakeRunData:
    """يمثل نتيجة تشغيل مبسطة لمحاكاة LangGraph."""

    def __init__(self) -> None:
        self.run_id = "run-test"
        self.execution = {"summary": "stategraph-response"}
        self.timeline = [_FakeTimelineEvent("supervisor")]


class _FakeLangGraphService:
    """خدمة مزيفة تعيد نتيجة ثابتة للتحقق من سلوك المسارات."""

    def __init__(self) -> None:
        self.last_payload: object | None = None

    async def run(self, payload: object) -> _FakeRunData:
        """تشغّل محاكاة وتعيد بيانات ثابتة دون تبعيات خارجية."""
        self.last_payload = payload
        return _FakeRunData()


def test_chat_http_messages_uses_stategraph(monkeypatch) -> None:
    """يتأكد أن POST /api/chat/messages يعيد استجابة موحدة من مسار StateGraph."""
    monkeypatch.setattr(routes, "create_langgraph_service", _FakeLangGraphService)

    client = TestClient(app)
    response = client.post("/api/chat/messages", json={"question": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["response"] == "stategraph-response"
    assert payload["graph_mode"] == "stategraph"


import jwt

from microservices.orchestrator_service.src.core.config import get_settings


def get_auth_headers():
    return [
        (
            b"Authorization",
            f"Bearer {jwt.encode({'sub': 'test-user', 'user_id': 1}, get_settings().SECRET_KEY, algorithm='HS256')}".encode(),
        )
    ]


def test_chat_ws_customer_uses_stategraph(monkeypatch) -> None:
    """يتأكد أن WS العميل يمر عبر نفس مسار StateGraph ويرجع route_id الصحيح."""
    monkeypatch.setattr(routes, "create_langgraph_service", _FakeLangGraphService)

    token = jwt.encode({"sub": "1", "user_id": 1}, get_settings().SECRET_KEY, algorithm="HS256")
    with TestClient(app).websocket_connect(f"/api/chat/ws?token={token}") as ws:
        ws.send_json({"question": "hello"})
        payload = ws.receive_json()

    assert payload["status"] == "ok"
    assert payload["route_id"] == "chat_ws_customer"
    assert payload["graph_mode"] == "stategraph"


def test_chat_ws_admin_uses_stategraph(monkeypatch) -> None:
    """يتأكد أن WS الإداري يستخدم StateGraph ويرجع route_id الإداري."""
    monkeypatch.setattr(routes, "create_langgraph_service", _FakeLangGraphService)

    token = jwt.encode({"sub": "1", "user_id": 1}, get_settings().SECRET_KEY, algorithm="HS256")
    with TestClient(app).websocket_connect(f"/admin/api/chat/ws?token={token}") as ws:
        ws.send_json({"question": "hello"})
        payload = ws.receive_json()

    assert payload["status"] == "ok"
    assert payload["route_id"] == "chat_ws_admin"
    assert payload["graph_mode"] == "stategraph"


def test_chat_ws_customer_routes_mission_complex_from_metadata(monkeypatch) -> None:
    """يتأكد أن metadata.mission_type يفعّل مسار المهمة الخارقة في WS العميل."""

    async def _fake_mission_stream(question: str, context: dict[str, object], user_id: int):
        _ = (question, context, user_id)
        yield '{"type":"RUN_STARTED","payload":{"mode":"standard"}}\n'

    monkeypatch.setattr(routes, "handle_mission_complex_stream", _fake_mission_stream)

    token = jwt.encode({"sub": "1", "user_id": 1}, get_settings().SECRET_KEY, algorithm="HS256")
    with TestClient(app).websocket_connect(f"/api/chat/ws?token={token}") as ws:
        ws.send_json({"question": "hello", "metadata": {"mission_type": "mission_complex"}})
        payload = ws.receive_json()

    assert payload["type"] == "RUN_STARTED"


def test_chat_ws_admin_passes_sanitized_context(monkeypatch) -> None:
    """يتأكد أن WS الأدمن يمرر سياقًا منقحًا إلى StateGraph ويحذف القيم غير القابلة للتسلسل."""

    fake_service = _FakeLangGraphService()
    monkeypatch.setattr(routes, "create_langgraph_service", lambda: fake_service)

    token = jwt.encode({"sub": "1", "user_id": 1}, get_settings().SECRET_KEY, algorithm="HS256")
    with TestClient(app).websocket_connect(f"/admin/api/chat/ws?token={token}") as ws:
        ws.send_json(
            {
                "question": "hello",
                "context": {"course": "alg", "meta": {"nested": True}},
            }
        )
        payload = ws.receive_json()

    assert payload["status"] == "ok"
    request_payload = fake_service.last_payload
    assert request_payload is not None
    assert getattr(request_payload, "context", {}).get("course") == "alg"
    assert "meta" not in getattr(request_payload, "context", {})
