"""يتحقق أن حركة legacy تساوي صفرًا لمدة نافذة لا تقل عن 30 يومًا قبل الإنهاء الكامل."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATUS_FILE = REPO_ROOT / "docs/architecture/LEGACY_TRAFFIC_30D_STATUS.json"


def main() -> int:
    if not STATUS_FILE.exists():
        print("❌ Missing legacy traffic evidence file.")
        return 1

    data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    window_days = int(data.get("window_days", 0))
    request_total = int(data.get("legacy_request_total_30d", -1))
    ws_total = int(data.get("legacy_ws_sessions_total_30d", -1))
    ratio = float(data.get("legacy_traffic_ratio_30d", -1.0))

    if window_days < 30:
        print(f"❌ Legacy traffic window too short: {window_days}d < 30d")
        return 1
    if request_total != 0:
        print(f"❌ Legacy HTTP traffic must be zero for 30d: {request_total}")
        return 1
    if ws_total != 0:
        print(f"❌ Legacy WS traffic must be zero for 30d: {ws_total}")
        return 1
    if ratio != 0.0:
        print(f"❌ Legacy traffic ratio must be 0.0 for 30d: {ratio}")
        return 1

    print("✅ Legacy traffic hard-zero verified for >=30 days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
