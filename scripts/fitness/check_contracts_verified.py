"""يتحقق من وجود خط أساس لعقود توجيه البوابة واختباراته."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_FILE = REPO_ROOT / "docs/contracts/consumer/gateway_route_contracts.json"
TEST_FILE = REPO_ROOT / "tests/contracts/test_gateway_routing_contracts.py"


def main() -> int:
    if not CONTRACT_FILE.exists():
        print("❌ Missing gateway consumer contract file.")
        return 1
    if not TEST_FILE.exists():
        print("❌ Missing gateway routing contract test.")
        return 1

    data = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))
    contracts = data.get("contracts", [])
    required_routes = {
        "/api/chat/{path:path}",
        "/v1/content/{path:path}",
        "/api/v1/data-mesh/{path:path}",
        "/system/{path:path}",
    }
    current_routes = {item.get("route") for item in contracts}
    if not required_routes.issubset(current_routes):
        print("❌ Contract baseline incomplete for cutover routes (phase1/phase2).")
        return 1

    print("✅ Contract baseline exists for phase1/phase2 routes and has test coverage file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
