## PR Roadmap

1. **PR 1: Single Control Plane Unification (Phase 1)**
   - **Objective:** Update API Gateway to route all chat traffic to the orchestrator/conversation service. Set `ROUTE_CHAT_HTTP_CONVERSATION_ROLLOUT_PERCENT` and `ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT` to 100 in `api_gateway/config.py`. Update tests in `tests/microservices/test_api_gateway_routing.py`.
   - **Metrics:** `ROUTE_CHAT_USE_LEGACY` should be fully deactivated. Scoreboard `normal_chat_owner` changes to `orchestrator-service` or `conversation-service`.
2. **PR 2: Phantom Limb Elimination (Phase 4)**
   - **Objective:** Delete the duplicate Overmind implementation in `app/services/overmind/` by renaming all execution modules to `.deprecated`. Ensure any dependent routes point to the single Orchestrator service.
   - **Metrics:** `active_overmind_duplication_metric` drops to 0. Scoreboard `single_brain_architecture` becomes true.
3. **PR 3: Default Runtime Modernization (Phase 5)**
   - **Objective:** Remove `core-kernel` and `postgres-core` from the primary `docker-compose.yml`. Set `CORE_KERNEL_URL` to None in Gateway config. Validate no legacy dependencies exist.
   - **Metrics:** `monolith_required_for_default_runtime` becomes false. Hard-zero monolith achieved.
