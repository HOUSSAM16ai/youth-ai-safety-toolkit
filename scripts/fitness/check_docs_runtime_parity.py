"""يتحقق من اتساق مصدر الحقيقة للمسارات مع خدمات runtime وتعريف المنافذ."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"
COMPOSE_DEFAULT = REPO_ROOT / "docker-compose.yml"
PORTS_SOURCE = REPO_ROOT / "docs/architecture/PORTS_SOURCE_OF_TRUTH.json"


def _compose_services() -> set[str]:
    services: set[str] = set()
    in_services = False
    for raw_line in COMPOSE_DEFAULT.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("services:"):
            in_services = True
            continue
        if in_services and raw_line and not raw_line.startswith(" "):
            break
        if in_services and raw_line.startswith("  ") and raw_line.strip().endswith(":"):
            key = raw_line.strip().removesuffix(":")
            if key and not key.startswith("#"):
                services.add(key)
    return services


def main() -> int:
    ports = json.loads(PORTS_SOURCE.read_text(encoding="utf-8"))
    if "api_gateway" not in ports or "core_kernel" not in ports:
        print("❌ Ports source-of-truth missing required keys: api_gateway/core_kernel")
        return 1

    routes_data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    services_in_compose = _compose_services()
    missing_services: list[str] = []

    for route in routes_data["routes"]:
        if not bool(route.get("default_profile", False)):
            continue
        target = str(route.get("target_service", ""))
        if target and target not in services_in_compose:
            missing_services.append(target)

    if missing_services:
        unique_missing = sorted(set(missing_services))
        print("❌ Route registry targets missing from default docker-compose services:")
        for service in unique_missing:
            print(f" - {service}")
        return 1

    print("✅ Docs/runtime parity passed for ports + default route ownership targets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
