"""اختبارات مواصفات التوجيه لعائلات data-mesh وsystem ضمن مرحلة الاستنزاف الثانية."""

from __future__ import annotations

from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from microservices.api_gateway import main
from microservices.api_gateway.config import settings
from microservices.api_gateway.security import verify_gateway_request


def test_datamesh_defaults_to_observability_when_legacy_disabled(monkeypatch) -> None:
    """يتأكد أن data-mesh يمر للخدمة الجديدة افتراضيًا عند تعطيل fallback legacy."""
    calls: list[tuple[str, str]] = []

    async def fake_forward(request, target_url, path, **_kwargs):
        calls.append((target_url, path))
        return PlainTextResponse("ok")

    monkeypatch.setattr(main.proxy_handler, "forward", fake_forward)
    main.app.dependency_overrides[verify_gateway_request] = lambda: True

    response = TestClient(main.app).get("/api/v1/data-mesh/health")
    main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == [(settings.OBSERVABILITY_SERVICE_URL, "api/v1/data-mesh/health")]


def test_system_defaults_to_orchestrator_when_legacy_disabled(monkeypatch) -> None:
    """يتأكد أن system يمر للخدمة الجديدة افتراضيًا عند تعطيل fallback legacy."""
    calls: list[tuple[str, str]] = []

    async def fake_forward(request, target_url, path, **_kwargs):
        calls.append((target_url, path))
        return PlainTextResponse("ok")

    monkeypatch.setattr(main.proxy_handler, "forward", fake_forward)
    main.app.dependency_overrides[verify_gateway_request] = lambda: True

    response = TestClient(main.app).get("/system/status")
    main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == [(settings.ORCHESTRATOR_SERVICE_URL, "system/status")]
