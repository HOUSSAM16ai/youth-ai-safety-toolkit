"""اختبارات بوابة الدماغ الواحد لضمان توحيد chat وmission."""

from __future__ import annotations

import json

from scripts.fitness import check_single_brain_control_plane


def test_default_registry_has_unified_chat_and_mission_owner() -> None:
    """يتأكد من تطابق المالك والهدف لكل مسارات chat/mission مع orchestrator-service."""
    indexed = check_single_brain_control_plane._default_routes_by_id()
    required = (
        *check_single_brain_control_plane.CHAT_ROUTE_IDS,
        *check_single_brain_control_plane.MISSION_ROUTE_IDS,
    )

    for route_id in required:
        route = indexed[route_id]
        assert route["owner"] == check_single_brain_control_plane.EXPECTED_OWNER
        assert route["target_service"] == check_single_brain_control_plane.EXPECTED_OWNER


def test_gate_main_succeeds_for_current_registry() -> None:
    """يتحقق من أن تنفيذ البوابة يمرّ عندما يكون مسار التحكم موحّدًا."""
    assert check_single_brain_control_plane.main() == 0

    payload = json.loads(check_single_brain_control_plane.REGISTRY.read_text(encoding="utf-8"))
    route_ids = {route["route_id"] for route in payload["routes"]}
    for route_id in (
        *check_single_brain_control_plane.CHAT_ROUTE_IDS,
        *check_single_brain_control_plane.MISSION_ROUTE_IDS,
    ):
        assert route_id in route_ids
