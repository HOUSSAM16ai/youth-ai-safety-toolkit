"""يتحقق من اتساق كتالوج الخدمات مع هيكل المجلدات وتعريفات compose الافتراضية."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = REPO_ROOT / "config/microservice_catalog.json"
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"
MICROSERVICES_ROOT = REPO_ROOT / "microservices"


def _load_catalog() -> list[dict[str, object]]:
    """يحمّل كتالوج الخدمات الرسمي ويرجع قائمة الخدمات المعرفة."""
    data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    return data["services"]


def main() -> int:
    """يفشل الفحص عند أي عدم اتساق بين الكتالوج والمجلدات وcompose الافتراضي."""
    services = _load_catalog()
    compose_text = DEFAULT_COMPOSE.read_text(encoding="utf-8")
    errors: list[str] = []

    for entry in services:
        service_dir = str(entry["service_dir"])
        compose_service = str(entry["compose_service"])
        dockerfile_required = bool(entry["dockerfile_required"])
        expected_in_default_compose = bool(entry["expected_in_default_compose"])

        service_path = MICROSERVICES_ROOT / service_dir
        if not service_path.exists() or not service_path.is_dir():
            errors.append(f"{service_dir}:missing_directory")
            continue

        if dockerfile_required and not (service_path / "Dockerfile").exists():
            errors.append(f"{service_dir}:missing_dockerfile")

        compose_token_present = f"{compose_service}:" in compose_text
        if expected_in_default_compose and not compose_token_present:
            errors.append(f"{service_dir}:missing_compose_registration")
        if not expected_in_default_compose and compose_token_present:
            errors.append(f"{service_dir}:unexpected_compose_registration")

    if errors:
        print("❌ Service catalog parity failed:")
        for item in errors:
            print(f" - {item}")
        return 1

    print("✅ Service catalog parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
