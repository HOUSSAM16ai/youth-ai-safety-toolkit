"""يتحقق من خفض التداخل المكرر بين overmind الحديث ولقطة legacy وفق سياسة المرحلة 2b."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = REPO_ROOT / "config/overmind_copy_coupling_baseline.json"
APP_OVERMIND = REPO_ROOT / "app/services/overmind"
MS_OVERMIND = REPO_ROOT / "microservices/orchestrator_service/src/services/overmind"


def _overlap_count() -> int:
    """يحسب عدد الملفات المشتركة نسخًا بالمسار النسبي بين الشجرتين."""
    app_files = {p.relative_to(APP_OVERMIND).as_posix() for p in APP_OVERMIND.rglob("*") if p.is_file()}
    ms_files = {p.relative_to(MS_OVERMIND).as_posix() for p in MS_OVERMIND.rglob("*") if p.is_file()}
    return len(app_files & ms_files)


def main() -> int:
    """يفشل الفحص إذا لم يتحقق شرط الانخفاض الصارم أو تم تجاوز السقف الحالي."""
    policy = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    current = _overlap_count()
    allowed_max = int(policy["active_copy_coupling_overlap_metric_max"])
    previous_max = int(policy["previous_max_overlap_metric"])
    mode = str(policy.get("policy", "no_increase"))

    if current > allowed_max:
        print(
            "❌ Overmind copy-coupling exceeds current phase ceiling: "
            f"current={current} allowed_max={allowed_max}"
        )
        return 1

    if mode == "strict_decrease" and current >= previous_max:
        print(
            "❌ Overmind copy-coupling did not decrease strictly versus previous phase: "
            f"current={current} previous_max={previous_max}"
        )
        return 1

    print(
        "✅ Overmind copy-coupling gate passed: "
        f"mode={mode} current={current} previous_max={previous_max} allowed_max={allowed_max}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
