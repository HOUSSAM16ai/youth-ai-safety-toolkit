"""يتحقق أن التشغيل الافتراضي بلا core-kernel وأنه محصور في ملف الطوارئ legacy."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"
LEGACY_COMPOSE = REPO_ROOT / "docker-compose.legacy.yml"


def main() -> int:
    default_text = DEFAULT_COMPOSE.read_text(encoding="utf-8")
    legacy_text = LEGACY_COMPOSE.read_text(encoding="utf-8")

    forbidden_tokens = ["core-kernel:", "postgres-core:", "CORE_KERNEL_URL"]
    for token in forbidden_tokens:
        if token in default_text:
            print(f"❌ Default compose must not contain '{token}'")
            return 1

    required_tokens = [
        "core-kernel:",
        "postgres-core:",
        'profiles: ["legacy", "emergency"]',
        "LEGACY_BREAKGLASS_ENABLED",
        "LEGACY_APPROVAL_TICKET: ${LEGACY_APPROVAL_TICKET:?LEGACY_APPROVAL_TICKET is required}",
        "LEGACY_EXPIRES_AT: ${LEGACY_EXPIRES_AT:?LEGACY_EXPIRES_AT is required (ISO-8601)}",
    ]
    for token in required_tokens:
        if token not in legacy_text:
            print(f"❌ Legacy compose missing required token: {token}")
            return 1

    print("✅ Default compose isolated from core-kernel; emergency legacy profile is enforced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
