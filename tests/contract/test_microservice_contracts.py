"""اختبارات عقود OpenAPI للخدمات المصغرة."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI

from app.core.openapi_contracts import compare_contract_to_runtime, detect_runtime_drift
from app.main import create_app as create_core_app
from microservices.memory_agent.main import create_app as create_memory_app
from microservices.observability_service.main import app as observability_app
from microservices.planning_agent.main import create_app as create_planning_app
from microservices.user_service.main import create_app as create_user_app

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi"


def _contract_path(filename: str) -> Path:
    return CONTRACTS_DIR / filename


def _build_cases() -> list[tuple[str, Callable[[], FastAPI] | FastAPI, str]]:
    return [
        ("core", lambda: create_core_app(enable_static_files=False), "core-api-v1.yaml"),
        ("planning", create_planning_app, "planning_agent-openapi.json"),
        ("memory", create_memory_app, "memory_agent-openapi.json"),
        ("user", create_user_app, "user_service-openapi.json"),
        ("observability", observability_app, "observability_service-openapi.json"),
    ]


@pytest.mark.parametrize("service_name, app_source, contract_file", _build_cases())
def test_contract_alignment_for_services(
    service_name: str,
    app_source: Callable[[], FastAPI] | FastAPI,
    contract_file: str,
) -> None:
    """يتحقق من تطابق مخطط التشغيل مع عقد OpenAPI لكل خدمة."""

    app = _resolve_app(app_source)
    contract_path = _contract_path(contract_file)
    contract_operations = compare_contract_to_runtime(
        contract_operations=_load_contract_operations(contract_path),
        runtime_schema=app.openapi(),
    )
    assert contract_operations.is_clean(), (
        f"عقد الخدمة {service_name} يحتوي على مسارات أو عمليات مفقودة: "
        f"paths={sorted(contract_operations.missing_paths)}, "
        f"operations={ {path: sorted(methods) for path, methods in contract_operations.missing_operations.items()} }"
    )


@pytest.mark.parametrize("service_name, app_source, contract_file", _build_cases())
def test_no_undocumented_paths_or_operations(
    service_name: str,
    app_source: Callable[[], FastAPI] | FastAPI,
    contract_file: str,
) -> None:
    """يتحقق من عدم وجود مسارات أو عمليات غير موثقة في التشغيل."""

    app = _resolve_app(app_source)
    contract_path = _contract_path(contract_file)
    contract_operations = _load_contract_operations(contract_path)
    drift_report = detect_runtime_drift(
        contract_operations=contract_operations,
        runtime_schema=app.openapi(),
    )
    assert drift_report.is_clean(), (
        f"الخدمة {service_name} تعرض مسارات أو عمليات غير موثقة: "
        f"paths={sorted(drift_report.unexpected_paths)}, "
        f"operations={ {path: sorted(methods) for path, methods in drift_report.unexpected_operations.items()} }"
    )


def _load_contract_operations(contract_path: Path) -> dict[str, set[str]]:
    """يحمل عمليات العقد مع ضمان وجودها قبل الفحص."""

    from app.core.openapi_contracts import load_contract_operations

    operations = load_contract_operations(contract_path)
    assert operations, f"عقد OpenAPI فارغ أو غير قابل للتحميل: {contract_path}"
    return operations


def _resolve_app(app_source: Callable[[], FastAPI] | FastAPI) -> FastAPI:
    """يعيد تطبيق FastAPI حتى لو كان الكائن قابلاً للاستدعاء."""
    if isinstance(app_source, FastAPI):
        return app_source
    return app_source()
