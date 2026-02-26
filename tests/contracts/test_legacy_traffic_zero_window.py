"""اختبارات مواصفة بوابة التحقق من انعدام حركة legacy لمدة 30 يومًا."""

from __future__ import annotations

from scripts.fitness.check_legacy_traffic_zero_window import main as verify_legacy_zero_window


def test_legacy_traffic_30d_gate_passes_with_zero_metrics() -> None:
    """يتأكد أن الفحص يمر عندما تكون كل مؤشرات legacy صفرية ضمن نافذة 30 يومًا."""
    assert verify_legacy_zero_window() == 0
