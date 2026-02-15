"""
المخطط المعماري للنواة (Kernel Blueprint).

يحوّل الإعدادات إلى مواصفات تشغيلية صريحة وفق مسار:
Config -> AppState -> WeavedApp
مع الالتزام بالجوهر الوظيفي والقشرة الإجرائية.
"""

import os
from dataclasses import dataclass

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routers.registry import RouterSpec, base_router_registry
from app.core.config import AppSettings
from app.middleware.remove_blocking_headers import RemoveBlockingHeadersMiddleware
from app.middleware.security.rate_limit_middleware import RateLimitMiddleware
from app.middleware.security.security_headers import SecurityHeadersMiddleware

__all__ = [
    "BASE_CORS_OPTIONS",
    "KernelConfig",
    "KernelSpec",
    "MiddlewareSpec",
    "RouterSpec",
    "StaticFilesSpec",
    "build_cors_options",
    "build_kernel_config",
    "build_kernel_spec",
    "build_middleware_stack",
    "build_router_registry",
    "build_static_files_spec",
    "is_dev_environment",
    "normalize_settings",
]


type MiddlewareSpec = tuple[type[BaseHTTPMiddleware] | type, dict[str, object]]

BASE_CORS_OPTIONS: dict[str, object] = {
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    "allow_headers": [
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
    "expose_headers": ["Content-Length", "Content-Range"],
}


@dataclass(frozen=True, slots=True)
class KernelConfig:
    """حاوية إعدادات النواة بشكل صريح وقابل للتمرير."""

    settings_obj: AppSettings
    settings_dict: dict[str, object]
    enable_static_files: bool


@dataclass(frozen=True, slots=True)
class KernelSpec:
    """مواصفات تشغيلية تُشتق من إعدادات النواة كبيانات."""

    config: KernelConfig
    middleware_stack: list[MiddlewareSpec]
    router_registry: list[RouterSpec]
    is_dev_environment: bool
    static_files_spec: "StaticFilesSpec"


@dataclass(frozen=True, slots=True)
class StaticFilesSpec:
    """مواصفات الملفات الثابتة كبيانات قابلة للتفسير."""

    enabled: bool
    serve_spa: bool


def normalize_settings(
    settings: AppSettings | dict[str, object],
) -> tuple[AppSettings, dict[str, object]]:
    """
    يطبع إعدادات التطبيق على شكل كائن وقاموس بطريقة موحدة.

    Args:
        settings: إعدادات التطبيق بصيغة كائن أو قاموس.

    Returns:
        tuple[AppSettings, dict[str, object]]: الكائن الكامل وقاموس القيم.
    """
    if isinstance(settings, dict):
        if "DATABASE_URL" not in settings and os.getenv("PYTEST_CURRENT_TEST"):
            settings = {**settings, "DATABASE_URL": "sqlite+aiosqlite:///:memory:"}
        settings_obj = AppSettings(**settings)
        settings_dict = settings_obj.model_dump()
        return settings_obj, settings_dict

    return settings, settings.model_dump()


def build_kernel_config(
    settings: AppSettings | dict[str, object],
    *,
    enable_static_files: bool,
) -> KernelConfig:
    """
    يبني حاوية إعدادات النواة ضمن مسار Config.

    Args:
        settings: إعدادات التطبيق بصيغة كائن أو قاموس.
        enable_static_files: تفعيل خدمة الملفات الثابتة.

    Returns:
        KernelConfig: حاوية الإعدادات.
    """
    settings_obj, settings_dict = normalize_settings(settings)
    return KernelConfig(
        settings_obj=settings_obj,
        settings_dict=settings_dict,
        enable_static_files=enable_static_files,
    )


def build_kernel_spec(
    config: KernelConfig,
) -> KernelSpec:
    """
    يبني مواصفات النواة التشغيلية وفق مسار AppState.

    Args:
        config: حاوية إعدادات النواة.

    Returns:
        KernelSpec: مواصفات التشغيل.
    """
    middleware_stack = build_middleware_stack(config.settings_obj)
    router_registry = build_router_registry()
    return KernelSpec(
        config=config,
        middleware_stack=middleware_stack,
        router_registry=router_registry,
        is_dev_environment=is_dev_environment(config.settings_dict),
        static_files_spec=build_static_files_spec(config),
    )


def build_middleware_stack(settings: AppSettings) -> list[MiddlewareSpec]:
    """
    تكوين قائمة البرمجيات الوسيطة كبيانات وصفية (Declarative Data).

    Args:
        settings: إعدادات التطبيق.

    Returns:
        list[MiddlewareSpec]: قائمة المواصفات.
    """
    cors_options = build_cors_options(settings.BACKEND_CORS_ORIGINS)

    stack: list[MiddlewareSpec] = [
        (TrustedHostMiddleware, {"allowed_hosts": settings.ALLOWED_HOSTS}),
        (CORSMiddleware, cors_options),
        (SecurityHeadersMiddleware, {}),
        (RemoveBlockingHeadersMiddleware, {}),
        (GZipMiddleware, {"minimum_size": 1000}),
    ]

    if settings.ENVIRONMENT != "testing":
        stack.insert(3, (RateLimitMiddleware, {}))

    return stack


def build_cors_options(origins: list[str]) -> dict[str, object]:
    """
    بناء خيارات CORS بشكل واضح ومتسق.

    Args:
        origins: قائمة الأصول المسموح بها.

    Returns:
        dict[str, object]: قاموس خيارات CORS الجاهز للاستخدام.
    """
    allow_origins = origins or ["*"]
    options = dict(BASE_CORS_OPTIONS)
    options["allow_origins"] = allow_origins
    return options


def build_router_registry() -> list[RouterSpec]:
    """
    سجل الموجهات (Router Registry) كبيانات.

    Returns:
        list[RouterSpec]: قائمة (الموجه، البادئة).
    """
    routers = base_router_registry()

    return routers


def build_static_files_spec(config: KernelConfig) -> StaticFilesSpec:
    """
    يبني مواصفات الملفات الثابتة ضمن سياق API-First.

    Args:
        config: حاوية إعدادات النواة.

    Returns:
        StaticFilesSpec: مواصفات الملفات الثابتة.
    """
    return StaticFilesSpec(
        enabled=config.enable_static_files,
        serve_spa=True,
    )


def is_dev_environment(settings_dict: dict[str, object]) -> bool:
    """يتحقق من أن البيئة تطويرية لتفعيل وثائق الـ API فقط حين الحاجة."""
    return settings_dict.get("ENVIRONMENT") == "development"
