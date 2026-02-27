# Cutover Scoreboard

This document tracks the progress of the migration to 100% microservices. It is updated automatically or manually after each significant PR.

| Metric | Phase 0 (Baseline) | Target (Phase 3) | Status |
| :--- | :---: | :---: | :---: |
| **Legacy Routes Count** | 5 | 0 | 🟡 In Progress |
| **WS Legacy Targets Count** | 2 | 0 | 🟡 In Progress |
| **Core Kernel in Default Profile** | Yes | No | 🔴 Critical |
| **Emergency Legacy Expiry Enforced** | No | Yes | 🔴 Critical |
| **App Import Violations** | 0 | 0 | 🟢 Passing |
| **Copy-Coupling Overlap** | 0.0% | 0.0% | 🟢 Passing |
| **Docs/Runtime Parity** | No | Yes | 🟡 In Progress |
| **Contract Gate** | Yes | Yes | 🟢 Passing |
| **Tracing Gate** | Yes | Yes | 🟢 Passing |

## Metric Definitions

*   **Legacy Routes Count:** Number of routes in `api_gateway/main.py` marked with `deprecated=True`.
*   **WS Legacy Targets Count:** Number of `@app.websocket` endpoints proxying to legacy targets.
*   **Core Kernel in Default Profile:** Whether `core-kernel` service is present in `docker-compose.yml` (default profile).
*   **Emergency Legacy Expiry Enforced:** Whether the code enforces a time limit (TTL) on legacy fallback.
*   **App Import Violations:** Number of `from app ...` imports found inside `microservices/` (excluding allowed files).
*   **Copy-Coupling Overlap:** Percentage of files in `app/services/overmind` that have identical names/paths in `microservices/orchestrator_service`.
*   **Docs/Runtime Parity:** Whether `PORTS_SOURCE_OF_TRUTH.json` matches `docker-compose.yml`.

## Latest Snapshot

**Date:** Phase 0 Baseline (Current)
**PR:** #1

*   Legacy Routes: 5
*   WS Legacy Targets: 2
*   App Imports: 0
*   Copy-Coupling: 0 files
