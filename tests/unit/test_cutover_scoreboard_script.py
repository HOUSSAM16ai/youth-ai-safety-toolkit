"""اختبارات سلوك لوحة التقدم لضمان اكتمال مؤشرات القطع المعمارية."""

from __future__ import annotations

import json

from scripts.fitness import generate_cutover_scoreboard


def test_owner_for_route_id_returns_unknown_when_missing() -> None:
    """يتحقق من أن دالة اكتشاف المالك تعيد unknown للمسارات غير المسجلة."""
    owner = generate_cutover_scoreboard._owner_for_route_id([], "missing-route")
    assert owner == "unknown"


def test_main_generates_required_scoreboard_keys() -> None:
    """يتأكد من أن الملف الناتج يتضمن جميع مؤشرات لوحة القطع الإلزامية."""
    exit_code = generate_cutover_scoreboard.main()
    assert exit_code == 0

    payload = json.loads(generate_cutover_scoreboard.SCOREBOARD_JSON.read_text(encoding="utf-8"))
    required_keys = {
        "legacy_routes_count",
        "legacy_ws_targets_count",
        "monolith_required_for_default_runtime",
        "normal_chat_owner",
        "super_agent_owner",
        "single_brain_architecture",
        "app_import_count_in_microservices",
        "active_overmind_duplication_metric",
        "stategraph_is_runtime_backbone",
        "contract_gate",
        "tracing_gate",
    }
    assert required_keys.issubset(payload.keys())
