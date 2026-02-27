"""اختبارات مواصفات حوكمة المرحلة صفر لقيود الانتقال إلى الميكروسيرفس."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    """ينفذ أمرًا فرعيًا ويعيد النتيجة للتحقق من نجاح بوابات الحوكمة."""
    return subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)


def test_f1_no_app_imports_strict_mode_passes() -> None:
    """يتأكد أن فحص F1 يعمل بالنمط الصارم ويحظر أي استيراد من app داخل microservices."""
    result = _run(
        ["python", "scripts/fitness/check_no_app_imports_in_microservices.py", "--strict"]
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_f2_default_routing_has_zero_legacy_targets() -> None:
    """يتأكد أن default routing لا يحتوي أي هدف legacy في السجل المعتمد."""
    result = _run(["python", "scripts/fitness/check_default_routing_no_legacy_targets.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f3_registry_parity_passes() -> None:
    """يتأكد أن سجلي المسارات متسقان لمنع تعدد مصادر الحقيقة."""
    result = _run(["python", "scripts/fitness/check_route_registry_parity.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f3_gateway_route_registry_alignment_passes() -> None:
    """يتأكد من اتساق مسارات البوابة البرمجية مع سجل الملكية المعتمد."""
    result = _run(["python", "scripts/fitness/check_gateway_route_registry_alignment.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f3_service_catalog_parity_passes() -> None:
    """يتأكد من اتساق كتالوج الخدمات مع compose وهيكل المجلدات."""
    result = _run(["python", "scripts/fitness/check_service_catalog_parity.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f3_tracing_gate_baseline_passes() -> None:
    """يتأكد من وجود عقد التتبع الأساسية عبر البوابة قبل تشديد القطع."""
    result = _run(["python", "scripts/fitness/check_tracing_gate.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f3_breakglass_expiry_enforcement_passes() -> None:
    """يتأكد أن سياسة break-glass مفروضة وأن الوضع الافتراضي آمن."""
    result = _run(["python", "scripts/fitness/check_breakglass_expiry_enforcement.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_f4_overmind_copy_coupling_no_increase() -> None:
    """يتأكد أن تداخل overmind المكرر يلتزم بالخفض الصارم في المرحلة 2b."""
    result = _run(["python", "scripts/fitness/check_overmind_copy_coupling.py"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_scoreboard_ignores_dunder_service_dirs() -> None:
    """يتأكد أن قياس lifecycle drift لا يفسر مجلدات __pycache__ كخدمات فعلية."""
    result = _run(["python", "scripts/fitness/generate_cutover_scoreboard.py"])
    assert result.returncode == 0, result.stdout + result.stderr
    scoreboard = (REPO_ROOT / "docs/diagnostics/CUTOVER_SCOREBOARD.md").read_text(encoding="utf-8")
    assert "__pycache__" not in scoreboard


def test_scoreboard_generation_succeeds() -> None:
    """يتأكد من إنتاج لوحة القياس وإتاحة نتائج baseline قبل أي قطع فعلي."""
    result = _run(["python", "scripts/fitness/generate_cutover_scoreboard.py"])
    assert result.returncode == 0, result.stdout + result.stderr
