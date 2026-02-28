import json

data = {
    "admin_chat_owner": "modern_orchestrator",
    "customer_chat_owner": "modern_orchestrator",
    "super_agent_owner": "modern_orchestrator",
    "websocket_owner": "modern_orchestrator",
    "single_brain_architecture": False,
    "stategraph_is_live_runtime": False,
    "monolith_required_for_default_runtime": True,
    "legacy_route_count": 0,
    "legacy_ws_target_count": 0,
    "active_overmind_duplication_metric": 1,
    "app_runtime_chat_logic_remaining": True,
    "contract_gate": False,
    "tracing_gate": False,
}

print(json.dumps(data, indent=2))
