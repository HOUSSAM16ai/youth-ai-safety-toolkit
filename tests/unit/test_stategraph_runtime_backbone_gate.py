"""اختبارات بوابة العمود الفقري StateGraph لمسارات chat."""

from __future__ import annotations

from scripts.fitness import check_stategraph_runtime_backbone


def test_registry_chat_targets_are_complete() -> None:
    """يتأكد من اكتمال تعريفات chat الثلاثة في سجل الملكية الافتراضي."""
    routes = check_stategraph_runtime_backbone._registry_chat_targets()
    route_ids = {str(route["route_id"]) for route in routes}
    assert route_ids == {"chat_http", "chat_ws_customer", "chat_ws_admin"}


def test_backbone_gate_passes_current_state() -> None:
    """يتحقق من نجاح البوابة عند اكتمال شروط StateGraph الحالية."""
    assert check_stategraph_runtime_backbone.main() == 0
