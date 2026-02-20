import pytest

import app
from app.core.settings import __getattr__ as settings_getattr
from app.core.settings import helpers


def test_upgrade_postgres_protocol_handles_postgres_alias() -> None:
    url = "postgres://user:pass@localhost:5432/db"
    assert (
        helpers._upgrade_postgres_protocol(url)
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )


def test_upgrade_postgres_protocol_upgrades_plain_postgresql() -> None:
    url = "postgresql://user:pass@localhost:5432/db"
    assert (
        helpers._upgrade_postgres_protocol(url)
        == "postgresql+asyncpg://user:pass@localhost:5432/db"
    )


def test_upgrade_postgres_protocol_keeps_asyncpg() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert helpers._upgrade_postgres_protocol(url) == url


def test_upgrade_postgres_protocol_upgrades_sqlite() -> None:
    url = "sqlite:///./db.sqlite"
    assert helpers._upgrade_postgres_protocol(url) == "sqlite+aiosqlite:///./db.sqlite"


def test_normalize_postgres_ssl_no_query() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert helpers._normalize_postgres_ssl(url) == url


def test_normalize_postgres_ssl_rewrites_sslmode() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db?sslmode=require"
    assert (
        helpers._normalize_postgres_ssl(url)
        == "postgresql+asyncpg://user:pass@localhost:5432/db?ssl=require"
    )


def test_normalize_postgres_ssl_drops_ssl_param() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db?ssl=1&foo=bar"
    assert (
        helpers._normalize_postgres_ssl(url)
        == "postgresql+asyncpg://user:pass@localhost:5432/db?foo=bar"
    )


def test_normalize_postgres_ssl_prefers_sslmode() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db?ssl=1&sslmode=verify-full"
    assert (
        helpers._normalize_postgres_ssl(url)
        == "postgresql+asyncpg://user:pass@localhost:5432/db?ssl=verify-full"
    )


def test_normalize_csv_or_list_accepts_none() -> None:
    assert helpers._normalize_csv_or_list(None) == []


def test_normalize_csv_or_list_accepts_list() -> None:
    assert helpers._normalize_csv_or_list([" a ", "", "b", "a"]) == ["a", "b"]


def test_normalize_csv_or_list_accepts_csv() -> None:
    assert helpers._normalize_csv_or_list("a, b, a") == ["a", "b"]


def test_normalize_csv_or_list_accepts_json_list() -> None:
    assert helpers._normalize_csv_or_list('["a", "b", "a"]') == ["a", "b"]


def test_normalize_csv_or_list_accepts_invalid_json_as_csv() -> None:
    assert helpers._normalize_csv_or_list('["a",') == ['["a"']


def test_ensure_database_url_allows_explicit_value() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert helpers._ensure_database_url(url, "development") == url


def test_ensure_database_url_raises_in_production() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        helpers._ensure_database_url(None, "production")


def test_ensure_database_url_defaults_to_memory_in_testing() -> None:
    assert helpers._ensure_database_url(None, "testing") == "sqlite+aiosqlite:///:memory:"


def test_ensure_database_url_falls_back_in_development() -> None:
    # Development now requires explicit DATABASE_URL
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        helpers._ensure_database_url(None, "development")


def test_lenient_json_loads_parses_json() -> None:
    assert helpers._lenient_json_loads('{"k": "v"}') == {"k": "v"}


def test_lenient_json_loads_returns_raw_string() -> None:
    assert helpers._lenient_json_loads("{invalid") == "{invalid"


def test_is_valid_email_accepts_valid_address() -> None:
    assert helpers._is_valid_email("admin@example.com") is True


def test_is_valid_email_rejects_invalid_address() -> None:
    assert helpers._is_valid_email("admin..example.com") is False


def test_get_or_create_dev_secret_key_is_stable() -> None:
    first = helpers._get_or_create_dev_secret_key()
    second = helpers._get_or_create_dev_secret_key()
    assert first == second


def test_app_getattr_loads_models_lazily() -> None:
    pytest.importorskip("sqlmodel")
    assert app.__getattr__("models").__name__ == "app.core.domain.models"


def test_app_getattr_rejects_unknown_attribute() -> None:
    with pytest.raises(AttributeError):
        app.__getattr__("unknown_attribute")


def test_settings_getattr_loads_base_service_settings() -> None:
    pytest.importorskip("pydantic")
    pytest.importorskip("pydantic_settings")
    base_settings = settings_getattr("BaseServiceSettings")
    assert base_settings.__name__ == "BaseServiceSettings"


def test_settings_getattr_rejects_unknown_attribute() -> None:
    with pytest.raises(AttributeError):
        settings_getattr("unknown_attribute")
