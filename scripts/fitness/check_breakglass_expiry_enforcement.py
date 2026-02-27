"""يتحقق من أن تمكين legacy الطارئ محكوم بتذكرة تغيير وصلاحية زمنية لا تتجاوز 24 ساعة."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_FILE = REPO_ROOT / "config/breakglass_legacy_policy.json"
LEGACY_ENV_FILE = REPO_ROOT / "config/breakglass_legacy.env"
LEGACY_COMPOSE = REPO_ROOT / "docker-compose.legacy.yml"


def _parse_env(text: str) -> dict[str, str]:
    """يحوّل نص env إلى قاموس بسيط مع تجاهل الأسطر الفارغة والتعليقات."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _parse_iso_datetime(value: str) -> datetime | None:
    """يحلّل التاريخ بصيغة ISO-8601 ويعيد None عند الفشل."""
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def main() -> int:
    """ينفّذ سياسات break-glass ويُرجع 0 عند الالتزام و1 عند أي مخالفة."""
    policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
    max_duration_hours = int(policy["max_duration_hours"])
    required_fields: list[str] = [str(item) for item in policy["required_fields"]]

    compose_text = LEGACY_COMPOSE.read_text(encoding="utf-8")
    required_compose_tokens = [
        "LEGACY_BREAKGLASS_ENABLED",
        "LEGACY_APPROVAL_TICKET",
        "LEGACY_EXPIRES_AT",
    ]
    for token in required_compose_tokens:
        if token not in compose_text:
            print(f"❌ Legacy compose is missing required token: {token}")
            return 1

    if not LEGACY_ENV_FILE.exists():
        print("✅ Break-glass policy baseline exists and feature is disabled by default.")
        return 0

    env_data = _parse_env(LEGACY_ENV_FILE.read_text(encoding="utf-8"))
    for field in required_fields:
        if field not in env_data:
            print(f"❌ Missing required break-glass env field: {field}")
            return 1

    enabled = env_data.get("LEGACY_BREAKGLASS_ENABLED", "false").lower() == "true"
    if not enabled:
        print("✅ Break-glass env file present and legacy mode is disabled.")
        return 0

    ticket = env_data.get("LEGACY_APPROVAL_TICKET", "")
    if not ticket or ticket == "CHG-REQUIRED":
        print("❌ Break-glass cannot be enabled without a valid approval ticket.")
        return 1

    expires_raw = env_data.get("LEGACY_EXPIRES_AT", "")
    expires_at = _parse_iso_datetime(expires_raw)
    if expires_at is None:
        print("❌ LEGACY_EXPIRES_AT must be a valid ISO-8601 datetime.")
        return 1

    now = datetime.now(UTC)
    if expires_at <= now:
        print("❌ Break-glass window already expired.")
        return 1

    duration_seconds = (expires_at - now).total_seconds()
    if duration_seconds > float(max_duration_hours * 3600):
        print(f"❌ Break-glass window exceeds policy max duration ({max_duration_hours}h).")
        return 1

    print(
        "✅ Break-glass is enabled with valid ticket and bounded expiry "
        f"({max_duration_hours}h max policy)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
