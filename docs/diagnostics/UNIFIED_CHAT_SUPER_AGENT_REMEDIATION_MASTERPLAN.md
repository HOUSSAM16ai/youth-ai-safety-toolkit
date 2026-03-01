# 1. Executive Summary

The system is currently suffering from a severe "split-brain" architecture where the live conversational paths and mission execution logic are divided between the legacy monolith (`app/`) and the modern microservices mesh (`microservices/`).

- **Why admin chat works:** The admin WebSocket route (`/admin/api/chat/ws`) falls back to a locally-hosted, legacy implementation inside the monolith (`app.api.routers.admin.py`). It uses the monolith's `ChatOrchestrator` and `DefaultChatHandler`, bypassing the need for a live modern orchestrator service.
- **Why customer chat fails:** The customer WebSocket route (`/api/chat/ws`) has been partially migrated to be a remote-dependent client. It relies heavily on `orchestrator_client.chat_with_agent` which makes internal network calls to the modern `orchestrator-service`. When this service is unreachable or when there is a mismatch in expected state, the customer path fails.
- **Why Super Agent fails:** When attempting to launch a "Super Agent" (a mission), both admin and customer paths use `MissionComplexHandler`. This legacy monolith handler acts as a fragile bridge, making an HTTP POST (`orchestrator_client.create_mission`) to the `orchestrator-service` to dispatch the mission. If this network boundary call fails, the monolith handler catches the exception and emits the explicit string `Dispatch Failed` to the user.
- **Is the system API-first?** No. While the API Gateway routes requests, the true logic and execution for chat and mission dispatch is still tightly coupled to the monolith runtime path rather than being fully API-driven from the microservices.
- **The single most dangerous architectural residue:** The `MissionComplexHandler` bridging logic in the monolith. It intercepts mission intents locally and attempts a synchronous HTTP handoff to the remote orchestrator, masking actual failures (auth, network, timeouts) with a generic `Dispatch Failed` error. It also relies on polling-like mechanisms rather than direct WebSocket streams.
- **The shortest safe correction path:** We must redirect all WebSocket traffic (both customer and admin) natively through the API Gateway to the `orchestrator-service`'s modern `stategraph`-based WebSocket endpoints (`/api/chat/ws` and `/admin/api/chat/ws`). This eliminates the monolith's `MissionComplexHandler` and HTTP bridge from the live execution path.

# 2. Runtime Truth Map

## Real Runtime Modes

- **Default compose runtime:** Uses `docker-compose.yml`, which starts the `api-gateway` and the modern microservices (`orchestrator-service`, `conversation-service`, etc.). The monolith (`app.main`) is NOT actively serving traffic here, meaning routes mapped to the monolith will fail.
- **Legacy/emergency runtime:** Uses `docker-compose.legacy.yml`, running `core-kernel` (the monolith) and its dependencies. This allows the monolith to handle admin chat locally, but relies on brittle bridge calls for customer chat and missions.
- **Dev/local runtime:** Often developers run `uvicorn app.main:app` locally, experiencing the legacy path and thinking it represents the final microservices architecture.
- **Gateway path:** API Gateway routes `/api/chat/ws` and `/admin/api/chat/ws` to modern microservices based on `ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT` configuration.
- **Direct monolith path:** Endpoints in `app.api.routers.admin` and `app.api.routers.customer_chat`.
- **WebSocket termination points:** Currently fragmented. The monolith accepts WS connections directly in some environments, while the gateway proxies them to `orchestrator-service` in others.
- **Actual Owners:**
  - Admin chat: Monolith (`app/api/routers/admin.py`) in legacy, `orchestrator-service` in modern.
  - Customer chat: Monolith bridge in legacy, `orchestrator-service` in modern.
  - Super Agent: Monolith `MissionComplexHandler` bridge in legacy, `orchestrator-service` via `start_mission` in modern.
  - StateGraph: Fully implemented natively in `orchestrator-service`, but heavily duplicated in monolith.
  - Conversation state: Split across role-specific boundary services in the monolith.
  - Mission state: `orchestrator-service` owns the true state, but the monolith holds transient bridged state.

## Mermaid Runtime Diagram

```mermaid
flowchart TD
    Client[Frontend Client] --> Gateway[API Gateway :8000]
    Gateway -->|Legacy Fallback (Dev/Legacy)| Monolith[Monolith app.main :8004]
    Gateway -->|Modern Path (Default)| Orchestrator[Orchestrator Service :8006]

    Monolith -->|Admin Chat| LocalChatHandler[Monolith DefaultChatHandler]
    Monolith -->|Customer Chat| OrchestratorClient1[Monolith orchestrator_client]
    Monolith -->|Super Agent| MissionComplexHandler[Monolith MissionComplexHandler]

    MissionComplexHandler -->|Dispatch| OrchestratorClient2[Monolith orchestrator_client.create_mission]
    OrchestratorClient1 --> Orchestrator
    OrchestratorClient2 --> Orchestrator

    Orchestrator --> StateGraph[Modern StateGraph Execution]
    Orchestrator --> EventBus[Redis Event Bus]
```

## Component Truth Table

| Component | Default Runtime | Dev/Legacy Runtime | Active Owner |
|---|---|---|---|
| Monolith Chat Routers | Inactive (supposedly) | Active | Admin Chat (Local) |
| Monolith `MissionComplexHandler` | Inactive | Active | Super Agent Bridge |
| API Gateway | Active | Inactive | Ingress |
| `orchestrator-service` | Active | Active (Required) | True StateGraph/Mission |

# 3. Full System Inventory

- **API Gateway (`microservices/api_gateway/main.py`)**: Active ingress. Handles WS proxying. Depends on downstream services.
- **Monolith (`app/`)**: Contains legacy routers (`admin.py`, `customer_chat.py`), boundary services, and legacy execution handlers (`strategy_handlers.py`).
- **Orchestrator Service (`microservices/orchestrator_service/`)**: The target modern owner for missions and chat. Contains the true `LangGraph` StateGraph implementation, event bus, and mission state management.
- **Conversation Service (`microservices/conversation_service/`)**: Candidate target for WS cutover, but currently acts as a partial/stub service according to architectural notes.
- **User Service (`microservices/user_service/`)**: Owns auth and roles.
- **Supporting Agent Services**: Planning, memory, research, reasoning. Active and API-driven.
- **Frontend WS Hooks**: Next.js hooks pointing to gateway endpoints. Payload shape mismatches exist (e.g., `mission_type` vs `metadata.mission_type`).
- **Bridge Clients**: `app.infrastructure.clients.orchestrator_client` which makes synchronous HTTP calls from the monolith to the orchestrator.
- **Router Files**:
  - Monolith: `app/api/routers/admin.py`, `app/api/routers/customer_chat.py`.
  - Microservice: `microservices/orchestrator_service/src/api/routes.py`.
- **Event/State Managers**: Monolith `chat_streamer.py`, orchestrator `state.py`.

# 4. Agent Architecture Diagnosis

- **True Brain:** The actual, modern agentic brain lives in `microservices/orchestrator_service/src/services/overmind/langgraph/service.py` and its factory. This is where `LangGraph` is actively managed.
- **Fake/Legacy Brain:** Lives in `app/services/overmind/` and `app/services/chat/handlers/`. There are around 105 files of copy-coupling between these two brains.
- **Is StateGraph on the live path?** Yes, but ONLY if the traffic actually reaches the native `orchestrator-service` endpoints (`/api/chat/ws` and `/admin/api/chat/ws`). If it hits the monolith first, it relies on the brittle bridge.
- **Duplicate agent trees:** Yes, `app/services/overmind` vs `microservices/orchestrator_service/src/services/overmind`.
- **Admin vs Customer vs Super Agent:** They currently use multiple authorities due to the fallback bridging mechanisms.

# 5. Monolith Residue Diagnosis

1. **Runtime/control-plane residues:**
   - **Evidence:** `app/api/routers/admin.py` and `app/api/routers/customer_chat.py` actively accepting WebSocket connections in local/dev runtimes.
   - **Severity:** Critical.
   - **Why it matters:** Sustains the split-brain and masks migration failures.
   - **Direction:** Delete these legacy WebSocket routers and strictly use the gateway proxies.

2. **Phantom-limb copy-coupling residues:**
   - **Evidence:** ~105 files shared between `app/services/overmind` and `microservices/orchestrator_service/src/services/overmind`.
   - **Severity:** High.
   - **Why it matters:** Causes logic drift.
   - **Direction:** Deprecate and remove `app/services/overmind` execution logic from the live path.

3. **Documentation/runtime split-brain residues:**
   - **Evidence:** `docker-compose.legacy.yml` vs `docker-compose.yml`.
   - **Severity:** Medium.
   - **Why it matters:** Developer confusion.
   - **Direction:** Standardize on microservices default path.

# 6. Admin Chat vs Customer Chat vs Super Agent Forensic Comparison

| Journey | Entrypoint | Gateway Route | WS Owner | Execution Owner | State Owner | Works/Fails | Reason |
|---|---|---|---|---|---|---|---|
| Admin Chat | UI -> `/admin/api/chat/ws` | Proxies to Orchestrator (if gateway used) | Monolith (legacy mode) / Orchestrator (modern) | Monolith `DefaultChatHandler` (local fallback) | Monolith DB | Works | Local monolith execution doesn't depend on remote orchestrator stability. |
| Customer Chat | UI -> `/api/chat/ws` | Proxies to Orchestrator | Monolith (legacy mode) / Orchestrator (modern) | `orchestrator_client.chat_with_agent` | Mixed | Fails | Hard dependency on remote orchestrator via the monolith bridge. Network/Auth fails. |
| Super Agent | UI (mission select) | Same as above | Monolith | `MissionComplexHandler` via `orchestrator_client` | Orchestrator | Fails | Bridging call `create_mission` fails synchronously, emitting "Dispatch Failed". |

**Narrative:** Admin chat survives because it executes locally in the monolith without bridging. Customer chat and Super Agent fail because they heavily rely on bridging HTTP calls from the monolith to the `orchestrator-service`, which break due to network configuration (`orchestrator-service:8006` hostname) or auth drops.

# 7. Root Cause Analysis

**Ranked Hypotheses:**
1. **Highest Confidence:** The `MissionComplexHandler` in the monolith catches exceptions when making HTTP calls (`orchestrator_client.create_mission`) to the orchestrator service, returning the explicit string `Dispatch Failed`. This happens because the monolith is acting as an intermediary instead of the client connecting natively to the orchestrator's WebSocket.
2. **Medium Confidence:** Auth token drops or subprotocol mismatch during the gateway WebSocket proxying.
3. **Lowest Confidence:** Contract mismatch (`mission_type` vs `metadata.mission_type`).

**Single Highest-Confidence Root Cause:**
The presence of the active monolith `app/api/routers/admin.py` and `app/api/routers/customer_chat.py` WebSocket endpoints. These endpoints intercept the traffic in legacy/local environments and route missions through the `MissionComplexHandler.execute` -> `orchestrator_client.create_mission` HTTP bridge. When this internal HTTP call fails (e.g. unreachable Docker hostname `http://orchestrator-service:8006`), it emits `Dispatch Failed`.

**Exact Evidence proving "Dispatch Failed":**
- `app/services/chat/handlers/strategy_handlers.py:243`: `"content": "❌ **خطأ في النظام:** لم نتمكن من بدء المهمة (Dispatch Failed)."`

# 8. StateGraph Diagnosis

- **Does StateGraph exist?** Yes, in `orchestrator-service`.
- **Is it live?** Yes, but only when traffic hits the native `orchestrator-service` endpoints (`/api/chat/ws` and `/admin/api/chat/ws`).
- **Does it stream directly?** Yes, the native implementation handles streams.
- **Payload shape mismatch:** The native endpoint handles `mission_complex` routing if `metadata.get("mission_type") == "mission_complex"`, whereas the frontend might send `mission_type` at the root. The orchestrator WS handler extracts this correctly.
- **Duplicate state owners:** Yes, the monolith has `AdminChatBoundaryService` and `CustomerChatBoundaryService` that duplicate conversation logic.

# 9. Target Architecture

The final architecture must enforce strict API-first microservices:
- **One WebSocket Authority:** `orchestrator-service` natively handles all `/api/chat/ws` and `/admin/api/chat/ws` connections, proxied purely by the API Gateway.
- **One Orchestration Authority:** The `LangGraph` service inside `orchestrator-service`.
- **No Monolith on Default Path:** The monolith legacy WS routers must be completely removed so they cannot intercept traffic.
- **Role Policy at Edge:** Admin vs Customer logic should be handled by RBAC checks in the `orchestrator-service` WebSocket handler, not by deploying completely divergent backend services.

# 10. Definition of “DONE”

- [ ] `app/api/routers/admin.py` and `app/api/routers/customer_chat.py` no longer define WebSocket endpoints.
- [ ] API Gateway correctly proxies all WS connections to `orchestrator-service`.
- [ ] No occurrences of the `Dispatch Failed` string can be reached by a live conversational path.
- [ ] Monolith `MissionComplexHandler` is decoupled from the live WS stream.
- [ ] Admin and customer WS streams utilize the exact same `orchestrator-service` native StateGraph implementation.

# 11. Modernization Blueprint

- **Phase 0: Truth + Containment**
  - Verify that the API Gateway can successfully route WS to `orchestrator-service`.
- **Phase 1: Unify WebSocket Authority**
  - **Goal:** Eliminate the split-brain at the edge.
  - **Deliverable:** Delete the legacy WS endpoints (`@router.websocket("/ws")` and `@router.websocket("/api/chat/ws")`) from `app/api/routers/customer_chat.py` and `app/api/routers/admin.py`.
  - **Exit Criteria:** All WS connections inherently fail over to or natively hit the gateway proxy -> orchestrator service.
- **Phase 2: Normalize dispatch and StateGraph**
  - **Goal:** Ensure the native `orchestrator-service` WS stream correctly parses `mission_type` from frontend and spawns the mission without a HTTP bridge.
- **Phase 3: Eliminate duplicate brain**
  - Deprecate `app/services/overmind` and `strategy_handlers.py` in the monolith.
- **Phase 4: Hard-zero monolith retirement**
  - Fully disable the legacy runtime profile.

# 12. Top Structural Problems

1. **Severity Critical:** Monolith WS routes (`customer_chat.py`, `admin.py`) still exist and intercept traffic in dev/legacy runtimes, forcing the brittle `MissionComplexHandler` bridge to activate.
2. **Severity Critical:** Admin and Customer have split backend architectures (local vs remote).
3. **Severity High:** 105 files of copy-coupling between monolith and orchestrator overmind implementations.

# 13. Ordered Backlog

1. **Delete legacy Monolith WS endpoints**
   - **Objective:** Force all WS traffic to use the modern API gateway proxy path.
   - **DoD:** `@router.websocket` decorators removed from `app/api/routers/admin.py` and `app/api/routers/customer_chat.py`.
   - **Risk Reduction:** Eliminates the "Dispatch Failed" path entirely by killing the entrypoint to the `MissionComplexHandler` bridge.
2. **Rename Monolith execution modules to `.deprecated`**
   - **Objective:** Remove phantom-limb legacy handlers to avoid confusion.
   - **DoD:** `app/services/chat/handlers/strategy_handlers.py` removed or disabled.
3. **Verify Orchestrator WS payload contracts**
   - **Objective:** Ensure the orchestrator WS endpoints (`/api/chat/ws` and `/admin/api/chat/ws`) correctly handle the frontend payload.

# 14. Evidence Index

- `app/services/chat/handlers/strategy_handlers.py:243` - Origin of the "Dispatch Failed" error message.
- `app/api/routers/customer_chat.py:136` - Customer WS endpoint using the `orchestrator_client.chat_with_agent` bridge.
- `app/api/routers/admin.py:164` - Admin WS endpoint executing locally via `ChatOrchestrator.dispatch`.
- `microservices/orchestrator_service/src/api/routes.py:120, 163` - NATIVE and correct WS implementations.
- `docs/diagnostics/CHAT_CUSTOMER_SUPER_AGENT_FORENSIC_MASTER_REPORT.md` - Forensic evidence of the split-brain catastrophe.
