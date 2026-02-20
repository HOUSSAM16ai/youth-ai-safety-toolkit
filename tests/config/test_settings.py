# tests/config/test_settings.py
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import AppSettings


def test_database_url_fixer_handles_duplicates_gracefully():
    """
    Tests that the DATABASE_URL validator doesn't create malformed URLs
    when 'sslmode' and 'ssl' parameters are both present or duplicated.
    """
    # This URL is designed to break the simple .replace() logic
    original_url = "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require&ssl=true"

    with patch.dict(os.environ, {"DATABASE_URL": original_url, "SECRET_KEY": "test"}):
        try:
            settings = AppSettings()
            # The corrected URL should have only one 'ssl' parameter.
            # The 'sslmode' should be removed.
            assert "sslmode" not in settings.DATABASE_URL
            assert "ssl=true" not in settings.DATABASE_URL
            assert settings.DATABASE_URL.count("ssl=require") == 1, (
                f"URL should contain 'ssl=require' exactly once. Got: {settings.DATABASE_URL}"
            )
        except ValidationError as e:
            pytest.fail(f"AppSettings validation failed unexpectedly: {e}")


def test_database_url_fixer_handles_simple_sslmode():
    """
    Tests that the DATABASE_URL validator correctly converts a simple 'sslmode=require'.
    """
    original_url = "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require"

    with patch.dict(os.environ, {"DATABASE_URL": original_url, "SECRET_KEY": "test"}):
        try:
            settings = AppSettings()
            assert "sslmode" not in settings.DATABASE_URL
            assert settings.DATABASE_URL.endswith("?ssl=require"), (
                f"URL should end with '?ssl=require'. Got: {settings.DATABASE_URL}"
            )
        except ValidationError as e:
            pytest.fail(f"AppSettings validation failed unexpectedly: {e}")


def test_database_url_defaults_to_sqlite_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """يوفر رابط SQLite احتياطي في بيئات الاختبار عند غياب المتغير."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Only testing allows implicit sqlite fallback now
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    settings = AppSettings()

    assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"


def test_database_url_must_exist_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """يرفض الإعدادات الإنتاجية التي لا تقدم رابط قاعدة بيانات صريح."""

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    with pytest.raises(ValidationError):
        AppSettings()


def test_database_url_upgrades_postgres_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    """يرفع بروتوكول postgres إلى postgresql+asyncpg لضمان التوافق غير المتزامن."""

    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/db")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = AppSettings()

    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")


def test_database_url_non_postgres_left_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    """يترك المعالج الروابط غير الخاصة بـ Postgres كما هي دون تعديل."""

    mysql_url = "mysql://user:pass@host:3306/db"
    monkeypatch.setenv("DATABASE_URL", mysql_url)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = AppSettings()

    assert mysql_url == settings.DATABASE_URL


def test_database_url_sslmode_disable_converts_to_ssl(monkeypatch: pytest.MonkeyPatch) -> None:
    """يحول sslmode=disable إلى معامل ssl موحد واحد لتبسيط التكوين."""

    original_url = "postgresql://user:pass@host:5432/db?sslmode=disable"
    monkeypatch.setenv("DATABASE_URL", original_url)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = AppSettings()

    assert "sslmode" not in settings.DATABASE_URL
    assert settings.DATABASE_URL.endswith("?ssl=disable")


def test_secret_key_defaults_to_secure_value_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generates a strong SECRET_KEY automatically when not provided in development."""

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    settings = AppSettings()

    assert len(settings.SECRET_KEY) >= 32


def test_secret_key_must_be_explicit_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejects implicit SECRET_KEY usage when running in production for safety."""

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError):
        AppSettings()


def test_secret_key_remains_stable_across_settings_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """يتأكد من ثبات المفتاح التلقائي بين إنشاءات الإعدادات ضمن نفس العملية التطويرية."""

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")

    first_instance = AppSettings()
    second_instance = AppSettings()

    assert first_instance.SECRET_KEY == second_instance.SECRET_KEY
    assert len(first_instance.SECRET_KEY) >= 32


def test_cors_origins_trim_and_deduplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    """يرتب نطاقات CORS مع إزالة الفراغات والتكرارات من الصيغ النصية المتنوعة."""

    settings = AppSettings(
        BACKEND_CORS_ORIGINS=" https://api.example.com , http://localhost:3000 , https://api.example.com ",
        SECRET_KEY="x" * 40,
    )

    assert settings.BACKEND_CORS_ORIGINS == ["https://api.example.com", "http://localhost:3000"]


def test_allowed_hosts_accepts_json_style_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """يفسر قائمة المضيفين بصيغة JSON النصية ويعيدها بدون فراغات أو عناصر فارغة."""

    monkeypatch.setenv("ALLOWED_HOSTS", '["example.com", " sub.example.com ", ""]')
    monkeypatch.setenv("SECRET_KEY", "x" * 40)

    settings = AppSettings()

    assert settings.ALLOWED_HOSTS == ["example.com", "sub.example.com"]
