"""اختبارات مواصفات التوجيه التعاقدي لمسارات chat/content في API Gateway."""

from __future__ import annotations

from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from microservices.api_gateway import main
from microservices.api_gateway.config import settings
from microservices.api_gateway.security import verify_gateway_request


def test_chat_route_defaults_to_orchestrator_when_legacy_flag_disabled(monkeypatch) -> None:
    """يتأكد أن /api/chat/* يذهب افتراضيًا للخدمة الجديدة عند تعطيل legacy."""
    calls: list[tuple[str, str]] = []

    async def fake_forward(request, target_url, path, **_kwargs):
        calls.append((target_url, path))
        return PlainTextResponse("ok")

    monkeypatch.setattr(main.proxy_handler, "forward", fake_forward)
    main.app.dependency_overrides[verify_gateway_request] = lambda: True

    response = TestClient(main.app).get("/api/chat/messages")
    main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == [(settings.ORCHESTRATOR_SERVICE_URL, "api/chat/messages")]


def test_content_route_defaults_to_research_when_legacy_flag_disabled(monkeypatch) -> None:
    """يتأكد أن /v1/content/* يذهب افتراضيًا للخدمة الجديدة عند تعطيل legacy."""
    calls: list[tuple[str, str]] = []

    async def fake_forward(request, target_url, path, **_kwargs):
        calls.append((target_url, path))
        return PlainTextResponse("ok")

    monkeypatch.setattr(main.proxy_handler, "forward", fake_forward)
    main.app.dependency_overrides[verify_gateway_request] = lambda: True

    response = TestClient(main.app).get("/v1/content/search")
    main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == [(settings.RESEARCH_AGENT_URL, "v1/content/search")]
