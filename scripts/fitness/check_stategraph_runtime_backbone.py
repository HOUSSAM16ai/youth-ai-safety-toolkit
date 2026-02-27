"""يتحقق من أن مسارات chat في orchestrator تستخدم عمود StateGraph بشكل قابل للرصد."""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"
ORCHESTRATOR_ROUTES = REPO_ROOT / "microservices/orchestrator_service/src/api/routes.py"

REQUIRED_CHAT_PATHS: tuple[str, ...] = (
    "/api/chat/messages",
    "/api/chat/ws",
    "/admin/api/chat/ws",
)


def _registry_chat_targets() -> list[dict[str, object]]:
    """يعيد تعريفات chat من سجل الملكية الافتراضي للتحقق من السلطة التشغيلية."""
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    routes = []
    for route in payload["routes"]:
        route_id = str(route.get("route_id", ""))
        if route_id in {"chat_http", "chat_ws_customer", "chat_ws_admin"} and bool(
            route.get("default_profile", False)
        ):
            routes.append(route)
    return routes


def _extract_declared_paths() -> set[str]:
    """يستخرج المسارات المعلنة داخل orchestrator عبر decorators."""
    tree = ast.parse(ORCHESTRATOR_ROUTES.read_text(encoding="utf-8"))
    paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            if deco.func.attr not in {"get", "post", "websocket", "api_route"}:
                continue
            if not deco.args:
                continue
            arg0 = deco.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                paths.add(arg0.value)
    return paths


def main() -> int:
    """يفشل إذا كانت ملكية chat أو مسارات stategraph ناقصة في orchestrator."""
    chat_routes = _registry_chat_targets()
    if len(chat_routes) != 3:
        print("❌ StateGraph backbone gate failed: missing chat routes in registry.")
        return 1

    violations: list[str] = []
    for route in chat_routes:
        owner = str(route.get("owner", ""))
        target = str(route.get("target_service", ""))
        if owner != "orchestrator-service":
            violations.append(f"{route.get('route_id')}:owner={owner}")
        if target != "orchestrator-service":
            violations.append(f"{route.get('route_id')}:target={target}")

    declared_paths = _extract_declared_paths()
    for path in REQUIRED_CHAT_PATHS:
        if path not in declared_paths:
            violations.append(f"missing_orchestrator_path:{path}")

    if violations:
        print("❌ StateGraph backbone gate failed.")
        for violation in violations:
            print(f" - {violation}")
        return 1

    print("✅ StateGraph runtime backbone gate passed for chat HTTP+WS orchestrator paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
