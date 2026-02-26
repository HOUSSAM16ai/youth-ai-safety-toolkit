"""يتحقق أن عدد مسارات legacy يساوي صفرًا بعد إغلاق مرحلة الاستنزاف."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTES_FILE = REPO_ROOT / "config/routes_registry.json"
BASELINE_FILE = REPO_ROOT / "config/legacy_routes_baseline.txt"


def main() -> int:
    routes_data = json.loads(ROUTES_FILE.read_text(encoding="utf-8"))
    baseline = int(BASELINE_FILE.read_text(encoding="utf-8").strip())
    current = sum(1 for route in routes_data["routes"] if route.get("legacy_flag") is True)
    if baseline != 0:
        print(f"❌ Baseline must be zero after phase2: baseline={baseline}")
        return 1
    if current != 0:
        print(f"❌ Legacy routes must be zero: current={current}")
        return 1
    print("✅ Legacy route hard-zero check passed: current=0 baseline=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
