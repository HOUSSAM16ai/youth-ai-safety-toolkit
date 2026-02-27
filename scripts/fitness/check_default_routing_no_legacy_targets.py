"""يتحقق من أن مسارات default profile لا تحتوي أهداف legacy سواء HTTP أو WebSocket."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"


def main() -> int:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    routes: list[dict[str, object]] = data["routes"]

    default_routes = [r for r in routes if bool(r.get("default_profile", False))]
    legacy_routes = [r for r in default_routes if bool(r.get("legacy_target", False))]
    legacy_ws = [r for r in legacy_routes if r.get("protocol") == "websocket"]

    if legacy_routes:
        print("❌ Legacy targets found in default routing registry:")
        for route in legacy_routes:
            print(
                f" - {route.get('route_id')} {route.get('public_path')} protocol={route.get('protocol')}"
            )
        return 1

    print(
        "✅ Default routing has zero legacy targets "
        f"(http+ws): routes={len(default_routes)} ws_legacy={len(legacy_ws)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
