# tests/test_settings_smoke.py
import os
from unittest.mock import patch

import pytest

from app.core.config import get_settings


@pytest.fixture(scope="function", autouse=True)
def clear_lru_cache():
    """
    Fixture to clear the lru_cache for get_settings before each test function.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_validation_error_on_missing_required_fields():
    """
    SMOKE TEST: Verifies that default settings load with safe fallbacks when env is empty.
    """
    # Create an empty temporary .env file
    empty_env_path = os.path.join(os.path.dirname(__file__), "empty.env")
    with open(empty_env_path, "w") as f:
        f.write("")

    # Patch os.environ to be empty to ensure no env vars are picked up
    # But set ENVIRONMENT=testing to allow default sqlite fallback
    with (
        patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True),
        patch(
            "app.core.config.AppSettings.model_config",
            {"env_file": empty_env_path, "extra": "ignore"},
        ),
    ):
        settings = get_settings()
        assert settings.SECRET_KEY
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///:memory:"

    if os.path.exists(empty_env_path):
        os.remove(empty_env_path)
