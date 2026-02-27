"""يتحقق من توحيد سلطة التحكم بين chat وmission داخل المسار الافتراضي."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"

CHAT_ROUTE_IDS: tuple[str, ...] = ("chat_http", "chat_ws_customer", "chat_ws_admin")
MISSION_ROUTE_IDS: tuple[str, ...] = ("missions_root", "missions_path")
EXPECTED_OWNER = "orchestrator-service"


def _default_routes_by_id() -> dict[str, dict[str, object]]:
    """يعيد فهرسًا لمسارات default profile حسب route_id لتسهيل التحقق الصريح."""
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    indexed: dict[str, dict[str, object]] = {}
    for route in payload["routes"]:
        if bool(route.get("default_profile", False)):
            indexed[str(route["route_id"])] = route
    return indexed


def main() -> int:
    """يفشل إذا لم تتوحّد ملكية/هدف chat وmission على orchestrator-service."""
    indexed_routes = _default_routes_by_id()
    required_ids = CHAT_ROUTE_IDS + MISSION_ROUTE_IDS

    missing = [route_id for route_id in required_ids if route_id not in indexed_routes]
    if missing:
        print("❌ Single-brain gate failed: missing route ids in default profile.")
        for route_id in missing:
            print(f" - {route_id}")
        return 1

    violations: list[str] = []
    for route_id in required_ids:
        route = indexed_routes[route_id]
        owner = str(route.get("owner", ""))
        target = str(route.get("target_service", ""))
        if owner != EXPECTED_OWNER:
            violations.append(f"{route_id}:owner={owner}")
        if target != EXPECTED_OWNER:
            violations.append(f"{route_id}:target_service={target}")

    if violations:
        print("❌ Single-brain gate failed: chat/mission control plane not unified.")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print("✅ Single-brain gate passed for chat+mission ownership and target service.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
