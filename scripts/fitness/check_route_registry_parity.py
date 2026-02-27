"""يتحقق من اتساق سجلي المسارات لمنع تعدد مصادر الحقيقة أثناء الانتقال."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_REGISTRY = REPO_ROOT / "config/routes_registry.json"
OWNERSHIP_REGISTRY = REPO_ROOT / "config/route_ownership_registry.json"


def _normalize(path: str) -> str:
    """يوحّد صيغة المسار لضمان مقارنة دقيقة بين السجلين."""
    return path.strip()


def main() -> int:
    """يفشل عند اختلاف المسارات بين السجلين أو عدم تطابق خصائص legacy الأساسية."""
    routes_payload = json.loads(ROUTES_REGISTRY.read_text(encoding="utf-8"))
    ownership_payload = json.loads(OWNERSHIP_REGISTRY.read_text(encoding="utf-8"))

    routes_by_path = {
        _normalize(item["public_path"]): bool(item.get("legacy_flag", False))
        for item in routes_payload["routes"]
    }
    ownership_by_path = {
        _normalize(item["public_path"]): bool(item.get("legacy_target", False))
        for item in ownership_payload["routes"]
    }

    missing_in_ownership = sorted(set(routes_by_path) - set(ownership_by_path))
    missing_in_routes = sorted(set(ownership_by_path) - set(routes_by_path))

    if missing_in_ownership or missing_in_routes:
        print("❌ Route registry parity failed.")
        if missing_in_ownership:
            print(" - Missing in route_ownership_registry:")
            for route in missing_in_ownership:
                print(f"   * {route}")
        if missing_in_routes:
            print(" - Missing in routes_registry:")
            for route in missing_in_routes:
                print(f"   * {route}")
        return 1

    mismatches: list[str] = []
    for path, legacy_flag in routes_by_path.items():
        if ownership_by_path[path] != legacy_flag:
            mismatches.append(path)

    if mismatches:
        print("❌ Legacy flag parity failed between registries:")
        for path in mismatches:
            print(
                " - "
                f"{path}: routes_registry={routes_by_path[path]} "
                f"route_ownership_registry={ownership_by_path[path]}"
            )
        return 1

    print("✅ Route registry parity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
