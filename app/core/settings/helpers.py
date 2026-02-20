"""
مساعدات إعدادات CogniForge.

يوفر هذا الملف توابع نقية وخفيفة لتطبيع القيم البيئية
وتحسين مسارات الإعدادات دون الاعتماد على مكتبات ثقيلة.
"""

from __future__ import annotations

import json
import logging
import secrets

logger = logging.getLogger("app.core.settings")

_DEV_SECRET_KEY_CACHE: str | None = None


def _get_or_create_dev_secret_key() -> str:
    """ينشئ مفتاحًا ثابتًا للتطوير لتجنّب إبطال الجلسات عند إعادة التشغيل."""
    global _DEV_SECRET_KEY_CACHE
    if _DEV_SECRET_KEY_CACHE is None:
        _DEV_SECRET_KEY_CACHE = secrets.token_urlsafe(64)
    return _DEV_SECRET_KEY_CACHE


def _ensure_database_url(value: str | None, environment: str) -> str:
    """يضمن وجود رابط قاعدة بيانات صالح مع بدائل آمنة للبيئات غير الإنتاجية."""
    if value:
        return value

    if environment == "production":
        raise ValueError("❌ CRITICAL: DATABASE_URL is missing in PRODUCTION!")

    if environment == "testing":
        return "sqlite+aiosqlite:///:memory:"

    raise ValueError(
        "❌ CRITICAL: DATABASE_URL is missing! You must configure the database connection explicitly."
    )


def _upgrade_postgres_protocol(url: str) -> str:
    """يرفع بروتوكولات قواعد البيانات إلى نسخ Async متوافقة مع asyncpg."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and "aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def _normalize_postgres_ssl(url: str) -> str:
    """يوحد معاملات SSL في روابط PostgreSQL إلى صيغة واحدة آمنة."""
    if not url.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
        return url

    from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

    parsed = urlparse(url)
    if not parsed.query:
        return url

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    sslmode_value: str | None = None
    filtered_items: list[tuple[str, str]] = []
    for key, value in query_items:
        if key == "sslmode":
            sslmode_value = value
            continue
        if key == "ssl":
            continue
        filtered_items.append((key, value))

    if sslmode_value is not None:
        filtered_items.append(("ssl", sslmode_value))

    new_query = urlencode(filtered_items, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _normalize_csv_or_list(value: list[str] | str | None) -> list[str]:
    """يطبع قيَم CSV أو JSON إلى قائمة نصية مرتبة دون تكرار."""
    if value is None:
        return []

    def _deduplicate(items: list[str]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                normalized.append(item)
        return normalized

    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return _deduplicate(cleaned)

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return []

        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    cleaned = [str(item).strip() for item in parsed if str(item).strip()]
                    return _deduplicate(cleaned)
            except json.JSONDecodeError:
                pass

        cleaned = [item.strip() for item in candidate.split(",") if item.strip()]
        return _deduplicate(cleaned)

    return []


def _is_valid_email(value: str) -> bool:
    """يتحقق من تنسيق بريد إلكتروني بسيط وآمن للاستخدام الإداري."""
    candidate = value.strip().lower()
    if not candidate or " " in candidate:
        return False
    if candidate.count("@") != 1:
        return False
    local, _, domain = candidate.partition("@")
    if not local or not domain:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if "." not in domain or domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    return len(domain.split(".")[-1]) >= 2


def _lenient_json_loads(value: str) -> object:
    """يفسر قيم البيئة كـ JSON مع السماح بالنصوص عند فشل التحليل."""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value
