"""اختبارات سلوكية لمسار /agent/chat لضمان العمود الفقري StateGraph."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from microservices.orchestrator_service.main import app
from microservices.orchestrator_service.src.api import routes


class _FakeTimelineEvent:
    """حدث زمني مبسط يدعم التصدير بصيغة JSON."""

    def __init__(self, agent: str) -> None:
        self._agent = agent

    def model_dump(self, mode: str = "json") -> dict[str, str]:
        """يعيد تمثيل الحدث بصيغة قاموس."""
        return {"agent": self._agent, "mode": mode}


class _FakeRunData:
    """بيانات تشغيل LangGraph مزيفة لاختبار مسار البث."""

    def __init__(self) -> None:
        self.run_id = "run-agent-stream"
        self.execution = {"summary": "stategraph-stream-response"}
        self.timeline = [_FakeTimelineEvent("supervisor")]


class _FakeLangGraphService:
    """خدمة LangGraph مزيفة تعيد بيانات ثابتة."""

    def __init__(self) -> None:
        self.last_payload: object | None = None

    async def run(self, payload: object) -> _FakeRunData:
        """تنفذ الطلب بشكل صوري وتعيد نتيجة ثابتة."""
        self.last_payload = payload
        return _FakeRunData()


def _parse_ndjson(text: str) -> list[dict[str, object]]:
    """يحلّل استجابة NDJSON إلى قائمة أحداث."""

    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_agent_chat_stream_uses_stategraph_payload(monkeypatch) -> None:
    """يتحقق من أن /agent/chat يبث أحداثًا مشتقة من StateGraph للمحادثة العادية."""

    fake_service = _FakeLangGraphService()
    monkeypatch.setattr(routes, "create_langgraph_service", lambda: fake_service)

    client = TestClient(app)
    response = client.post(
        "/agent/chat",
        json={
            "question": "hello",
            "user_id": 1,
            "context": {"intent": "DEFAULT", "course": "cs50", "meta": {"bad": "value"}},
        },
    )

    assert response.status_code == 200
    events = _parse_ndjson(response.text)
    assert len(events) == 2
    assert events[0]["type"] == "assistant_delta"
    assert events[1]["type"] == "assistant_final"

    payload = events[1]["payload"]
    assert payload["content"] == "stategraph-stream-response"
    assert payload["graph_mode"] == "stategraph"
    assert payload["run_id"] == "run-agent-stream"

    request_payload = fake_service.last_payload
    assert request_payload is not None
    assert getattr(request_payload, "context", {}).get("course") == "cs50"
    assert "meta" not in getattr(request_payload, "context", {})


def test_agent_chat_stream_routes_mission_complex(monkeypatch) -> None:
    """يتحقق من أن intent=MISSION_COMPLEX يفعّل مسار المهمة الخارقة المباشر."""

    captured_context: dict[str, object] = {}

    async def _fake_mission_stream(question: str, context: dict, user_id: int):
        _ = (question, user_id)
        captured_context.update(context)
        yield json.dumps({"type": "RUN_STARTED", "payload": {"mode": "standard"}}) + "\n"

    monkeypatch.setattr(routes, "handle_mission_complex_stream", _fake_mission_stream)

    client = TestClient(app)
    response = client.post(
        "/agent/chat",
        json={"question": "run", "user_id": 2, "context": {"intent": "mission_complex"}},
    )

    assert response.status_code == 200
    events = _parse_ndjson(response.text)
    assert events[0]["type"] == "RUN_STARTED"
    assert captured_context.get("intent") == "mission_complex".upper()
