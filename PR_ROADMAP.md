# PR Roadmap: 100% Microservices Migration

This roadmap outlines the sequential Pull Requests required to safely migrate the CogniForge platform to a 100% microservices architecture, eliminating the legacy `core-kernel` monolith from the production runtime.

## Phase 0: Stop-Loss Governance & Baseline

### PR#1: Stop-Loss Governance & Baseline (Current)
*   **Scope:** Establish baseline metrics, freeze legacy routes, ban new monolith imports, and verify tracing.
*   **Tests:**
    *   `scripts/check_app_imports.sh` (must fail on new imports).
    *   `scripts/check_legacy_routes.sh` (must fail if routes > baseline).
    *   `tests/microservices/test_trace_propagation.py` (new).
*   **Rollback:** Revert PR (low risk, no runtime changes).
*   **Risk:** Low. Observability only.

### PR#2: CI Fitness Functions & Route Registry
*   **Scope:** Integrate governance scripts into `CI` workflow to block regressions. Canonicalize `config/routes_registry.json`.
*   **Tests:**
    *   CI pipeline execution (Red/Green test).
    *   Verify `routes_registry.json` matches `api_gateway/main.py`.
*   **Rollback:** Revert PR.
*   **Risk:** Low. CI changes only.

## Phase 1: Control Plane Singularity

### PR#3: Gateway Default Routing Cleanup
*   **Scope:** Remove `CORE_KERNEL_URL` from default `config.py` (set to None). Ensure no default traffic hits monolith.
*   **Tests:**
    *   `tests/microservices/test_api_gateway_routing.py` (verify 404 or modern target for all paths).
    *   Manual smoke test of critical paths.
*   **Rollback:** Revert `config.py` change.
*   **Risk:** Medium. Traffic redirection.

### PR#4: Emergency Legacy Break-Glass
*   **Scope:** Implement `EMERGENCY_LEGACY_ENABLED` flag (default False) with auto-expiry logic (TTL).
*   **Tests:**
    *   Unit test for `LegacyACL` enforcing expiry.
    *   Integration test enabling legacy mode and verifying it works, then expires.
*   **Rollback:** Disable flag / Revert PR.
*   **Risk:** Low. Feature flag implementation.

### PR#5: Devcontainer & Compose Profile Alignment
*   **Scope:** Update `devcontainer.json` and `docker-compose.yml` to use `microservices` profile by default. Move `core-kernel` to `legacy` profile strictly.
*   **Tests:**
    *   `make microservices-up` (verify no core-kernel container).
    *   `make test` (verify tests pass in microservices env).
*   **Rollback:** Revert compose files.
*   **Risk:** Low. Developer experience only.

## Phase 2: Phantom Limb Exorcism

### PR#6: Overmind Ownership Transfer (Step 1)
*   **Scope:** Identify and deprecate `app/services/overmind`. Point `microservices/orchestrator_service` to use local modules ONLY.
*   **Tests:**
    *   `scripts/measure_copy_coupling.py` (metric should decrease/stabilize).
    *   Orchestrator unit tests.
*   **Rollback:** Revert code pointers.
*   **Risk:** Medium. Code relocation.

### PR#7: Remove `from app` Imports (Orchestrator)
*   **Scope:** Refactor `orchestrator_service` to remove all `from app...` imports. Duplicate minimal shared logic if needed (or move to `app.core` if truly generic).
*   **Tests:**
    *   `scripts/check_app_imports.sh` (violations -> 0).
    *   Full regression suite for Orchestrator.
*   **Rollback:** Revert refactoring.
*   **Risk:** High. Logic changes.

## Phase 3: Hard Zero Legacy & Retirement

### PR#8: Route Cleanup & Final Cutover
*   **Scope:** Remove `legacy_flag=True` routes from Gateway. Remove `LegacyACL` adapter code (except break-glass).
*   **Tests:**
    *   `scripts/check_legacy_routes.sh` (count -> 0).
    *   E2E Critical Journey tests.
*   **Rollback:** Revert route deletion.
*   **Risk:** High. Public API surface change.

### PR#9: Documentation & Runbook Finalization
*   **Scope:** Update all docs to reflect Microservices-only architecture. Delete `docker-compose.legacy.yml` references from main docs.
*   **Tests:**
    *   Doc review.
*   **Rollback:** Revert docs.
*   **Risk:** Low.
