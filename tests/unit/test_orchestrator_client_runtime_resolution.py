"""اختبارات سلوك حل عنوان orchestrator وفق بيئة التشغيل."""

from __future__ import annotations

from app.infrastructure.clients import orchestrator_client as module


def test_runtime_url_keeps_configured_when_host_is_not_docker_alias(monkeypatch) -> None:
    """يحافظ على العنوان كما هو إذا لم يكن اسم المضيف alias خاصًا بـ Docker."""

    monkeypatch.setattr(module, "_is_host_resolvable", lambda host: True)

    resolved = module._resolve_runtime_orchestrator_url("http://localhost:8006")

    assert resolved == "http://localhost:8006"


def test_runtime_url_falls_back_when_docker_alias_is_unresolvable(monkeypatch) -> None:
    """يحوّل العنوان إلى localhost عند تعذر حل orchestrator-service."""

    monkeypatch.setattr(module, "_is_host_resolvable", lambda host: False)

    resolved = module._resolve_runtime_orchestrator_url("http://orchestrator-service:8006")

    assert resolved == module.LOCAL_ORCHESTRATOR_URL


def test_runtime_url_keeps_docker_alias_when_resolvable(monkeypatch) -> None:
    """يبقي alias Docker عند توفر DNS داخل شبكة compose."""

    monkeypatch.setattr(module, "_is_host_resolvable", lambda host: True)

    resolved = module._resolve_runtime_orchestrator_url("http://orchestrator-service:8006")

    assert resolved == "http://orchestrator-service:8006"
