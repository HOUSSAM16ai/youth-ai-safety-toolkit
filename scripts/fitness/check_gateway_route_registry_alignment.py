"""يتحقق من اتساق تعريفات مسارات البوابة مع سجل الملكية المعتمد آليًا."""

from __future__ import annotations

import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_MAIN = REPO_ROOT / "microservices/api_gateway/main.py"
OWNERSHIP_REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"


def _extract_gateway_paths() -> set[str]:
    """يستخرج مسارات API المعرفة عبر decorators في بوابة FastAPI."""
    tree = ast.parse(GATEWAY_MAIN.read_text(encoding="utf-8"), filename=GATEWAY_MAIN.as_posix())
    paths: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            if deco.func.attr not in {"api_route", "websocket"}:
                continue
            if not deco.args:
                continue
            first_arg = deco.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                paths.add(first_arg.value.strip())
    return paths


def _registry_paths() -> set[str]:
    """يعيد مجموعة المسارات المعرفة في سجل الملكية للوضع الافتراضي."""
    payload = json.loads(OWNERSHIP_REGISTRY.read_text(encoding="utf-8"))
    return {
        str(item["public_path"]).strip()
        for item in payload["routes"]
        if bool(item.get("default_profile", False))
    }


def main() -> int:
    """يفشل إذا فُقد مسار من السجل داخل تعريفات البوابة أو وُجد تكرار غير قانوني."""
    registry_paths = _registry_paths()
    gateway_paths = _extract_gateway_paths()

    missing_in_gateway = sorted(path for path in registry_paths if path not in gateway_paths)
    if missing_in_gateway:
        print("❌ Gateway route registry alignment failed (missing routes):")
        for path in missing_in_gateway:
            print(f" - {path}")
        return 1

    if len(registry_paths) != len(set(registry_paths)):
        print("❌ Registry has duplicate route paths.")
        return 1

    print("✅ Gateway route registry alignment passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
