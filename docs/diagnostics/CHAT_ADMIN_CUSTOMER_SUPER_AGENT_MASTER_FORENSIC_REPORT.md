# CHAT ADMIN CUSTOMER SUPER AGENT MASTER FORENSIC REPORT

## 1. Executive Summary

This master forensic report diagnoses the catastrophic split-brain architecture responsible for the diverging behavior in live chat and mission execution. The system currently exists in a hybrid state where the legacy monolith (`app.main`) acts as the practical control plane for major chat operations, while a microservices mesh (API Gateway, orchestrator-service, conversation-service) operates in parallel but is only partially integrated.

The core findings are:
1. **Admin normal chat succeeds** because it is processed entirely within the monolith (`app/api/routers/admin.py` -> `AdminChatStreamer` -> `ChatOrchestrator` -> `DefaultChatHandler`), which does not rely on external microservices for local completion.
2. **Customer normal chat fails** because its WebSocket endpoint (`app/api/routers/customer_chat.py`) explicitly bridges to `orchestrator_client.chat_with_agent(...)`. If the remote orchestrator service is unreachable (e.g., when running in a monolith-only dev profile), the chat stream collapses entirely.
3. **Super Agent (المهمة الخارقة) fails for both** because its dispatch mechanism in the monolith's `MissionComplexHandler` is strictly hard-coupled to the `orchestrator_client.create_mission` HTTP call. When the bridge call fails due to service unreachability or contract payload mismatch, the handler catches the exception and emits the fixed string: `"❌ **خطأ في النظام:** لم نتمكن من بدء المهمة (Dispatch Failed)."`.
4. The current system is **not truly 100% microservices** due to the monolith still owning critical WebSocket endpoints, local routing handlers, and maintaining over 100 duplicated "phantom-limb" files with the orchestrator service.
5. The system is **not truly API-first** because mission and chat interactions still bypass structured microservice APIs via direct internal function calls or tightly-coupled bridge logic within the legacy app layer.
6. The **StateGraph / multi-agent architecture** is split. The true, intended LangGraph orchestration runs in `orchestrator-service`, but the active legacy path bypasses it or sends mismatched metadata, isolating the live session from real graph execution progress.

To reach a single live control plane, one websocket authority, and true API-first microservices behavior, the monolith must be entirely decommissioned from the live execution path. All WebSocket ingress must terminate at the API Gateway and proxy cleanly to `orchestrator-service` or `conversation-service` with a unified payload contract.

---

## 2. Runtime Truth Map

The runtime reality depends entirely on the active environment configuration:

### 2.1 Default Runtime (Modern Compose)
- **Source:** `docker-compose.yml`
- Runs API Gateway (`:8000`), Orchestrator Service, Conversation Service, Planning Agent, Memory Agent, etc.
- Monolith (`app.main`) is excluded.
- The Gateway attempts to proxy chat/mission WS routes to backend microservices, but payload structure expectations (e.g., `mission_type` vs `metadata.mission_type`) create friction.

### 2.2 Legacy/Emergency Runtime
- **Source:** `docker-compose.legacy.yml`
- Runs the monolith `core-kernel` (`app.main`) and `postgres-core`.
- Monolith owns `:8000`.
- This environment actively executes local `AdminChatStreamer` but fails on customer chat and Super Agent because `orchestrator-service` is absent, causing `orchestrator_client` exceptions.

### 2.3 Dev/Local Runtime
- Commonly uses scripts (e.g., `scripts/start-backend.sh`, `Makefile`) that prioritize running the monolith directly via Uvicorn, simulating the Legacy runtime and reinforcing the split-brain problem.

### 2.4 Mermaid Diagram: The Split-Brain Flow
```mermaid
graph TD
    UI[Frontend Client] -->|WS: /admin/api/chat/ws| Gateway
    UI -->|WS: /api/chat/ws| Gateway

    Gateway -->|Proxy (if modern)| OrchService[Orchestrator Service]
    Gateway -.->|Bypass (if monolith runs on 8000)| CoreKernel[Monolith: Core Kernel]

    subgraph Monolith Runtime
        CoreKernel --> AdminRouter[app/api/routers/admin.py]
        AdminRouter --> DefaultHandler[DefaultChatHandler]
        DefaultHandler --> LocalDB[(Local DB)]

        CoreKernel --> CustomerRouter[app/api/routers/customer_chat.py]
        CustomerRouter --> OrchClient1[orchestrator_client.chat_with_agent]

        CoreKernel --> MissionHandler[MissionComplexHandler]
        MissionHandler --> OrchClient2[orchestrator_client.create_mission]
    end

    subgraph Microservices Runtime
        OrchClient1 -.-> OrchService
        OrchClient2 -.-> OrchService
        OrchService --> LangGraph[LangGraph State]
    end
```

### 2.5 Runtime Truth Table

| Capability | Legacy Profile (Monolith) | Modern Profile (Microservices) |
| :--- | :--- | :--- |
| **Admin Normal Chat** | Works (Local Execution) | Fails or Mismatched Contract |
| **Customer Normal Chat** | Fails (Bridge Exception) | Proxied (Contract Dependent) |
| **Super Agent** | Fails ("Dispatch Failed") | Fails (Payload Mismatch/Isolation) |

---

## 3. Full System Inventory

| Component | Status | Responsibility | Ingress/API | WS Ownership | Data Ownership | Architectural Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **api-gateway** | Active | Ingress routing, auth validation, proxying | `:8000` | Passthrough | None | Intended front door, but often bypassed in dev scripts. |
| **core-kernel (Monolith)** | Legacy / Split-Brain | Legacy logic, local admin chat | Internal handlers | Yes (in legacy run) | Legacy DB | Dangerous duplicate brain. Must be retired. |
| **orchestrator-service** | Active / Target | Single source of truth for missions & StateGraph | `:8006` | Intended | Mission DB | Target owner, but currently blocked by legacy bridges and payload mismatches. |
| **conversation-service** | Placeholder / Partial | Handling normal chat interactions | `:8010` | Intended | Convo DB | Needs completion or consolidation into orchestrator. |
| **planning-agent** | Active | Task planning via orchestrator | `:8001` | None | Agent State | Clean microservice, invoked by orchestrator. |
| **memory-agent** | Active | Memory/context management | `:8002` | None | Memory DB | Clean microservice. |
| **research-agent** | Active | Information retrieval | `:8007` | None | None | Clean microservice. |
| **reasoning-agent** | Active | Complex logic/deduction | `:8008` | None | None | Clean microservice. |
| **user-service** | Active | Identity & Auth | `:8003` | None | User DB | Foundation for auth boundary. |
| **observability-service**| Active | Tracing & telemetry | `:8005` | None | Logs | Governance enforcer. |

---

## 4. Agent Architecture Diagnosis

- **Relevant Agents:** Orchestrator, Planning, Memory, Research, Reasoning, Auditor.
- **How they actually work:** In the microservices layer, they communicate via internal HTTP/REST or AMQP. In the legacy layer, there are duplicated proxy clients and local handlers (e.g., `app/services/chat/agents/`).
- **Orchestration Authority:** Intended to live entirely in `orchestrator-service` via LangGraph. However, the monolith's `ChatOrchestrator` (`app/services/chat/orchestrator.py`) acts as a rogue secondary authority.
- **WebSocket/Chat Authority:** The API Gateway is supposed to proxy all WS traffic. Yet, the frontend often hits the monolith if run locally, and the monolith actively intercepts and processes WS frames.
- **Boundary Assessment:** Boundaries are fundamentally broken. The monolith bridges into microservices midway through a transaction (e.g., `MissionComplexHandler` calling `orchestrator_client`), violating API-first principles.

---

## 5. Monolith Residue Diagnosis

### 5.1 Runtime/control-plane residues
- **Evidence:** `app/main.py` still loads `app.api.routers.admin` and `customer_chat`.
- **Severity:** CRITICAL
- **Why it matters:** It intercepts live traffic, preventing true microservices routing.
- **Direction:** Remove chat/mission routers from the monolith completely.

### 5.2 Import contamination residues
- **Evidence:** While governance scripts block `from app import` in `microservices/`, the inverse happens implicitly through DB models and shared libraries not fully extracted.
- **Severity:** HIGH
- **Why it matters:** Prevents independent deployment and database isolation.
- **Direction:** Extract shared domain models to a standalone package or enforce strict duplicate segregation.

### 5.3 Phantom-limb copy-coupling residues
- **Evidence:** Over 100 duplicated files between `app/services/overmind` and `microservices/orchestrator_service/src/services/overmind`. Evaluated by `check_overmind_copy_coupling.py`.
- **Severity:** HIGH
- **Why it matters:** Bug fixes must be applied twice; creates massive cognitive load.
- **Direction:** Delete the `app/services/overmind` directory entirely.

### 5.4 State ownership residues
- **Evidence:** `app/core/domain/mission.py` still dictates DB schemas that the orchestrator service needs to own exclusively.
- **Severity:** HIGH
- **Why it matters:** Violates the "database per service" rule.
- **Direction:** Move database tables and migrations exclusively into the `orchestrator-service` repository/module.

### 5.5 Documentation/runtime split-brain residues
- **Evidence:** `ARCHITECTURE.md` describes the monolith as the "Single Source of Truth", while `MICROSERVICES_CONSTITUTION.md` mandates distributed ownership.
- **Severity:** MEDIUM
- **Why it matters:** Confuses developers and justifies adding code to the monolith.
- **Direction:** Archive legacy architecture docs and establish the constitution as the sole authority.

---

## 6. Admin Chat vs Customer Chat vs Super Agent Forensic Comparison

| Feature | Entrypoint | Route | Handler | State Owner | Target Service | Result | Exact Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin Chat** | UI Admin | `/admin/api/chat/ws` | Monolith `DefaultChatHandler` | Monolith DB | Local Monolith | **Works** | Handled completely locally inside the monolith. No microservice dependency. |
| **Customer Chat** | UI Chat | `/api/chat/ws` | Monolith `customer_chat.py` | Remote DB | `orchestrator_client` -> `orchestrator-service` | **Fails** | Hard remote dependency. If `orchestrator-service` is down (e.g. legacy runtime), the bridge call crashes. |
| **Super Agent** | UI Mission | `/api/chat/ws` | Monolith `MissionComplexHandler` | Remote DB | `orchestrator_client` -> `orchestrator-service` | **Fails** | Dispatch bridge strictly delegates `start_mission` to the HTTP client. If unreachable, emits "Dispatch Failed". Payload structure mismatches (`mission_type` vs `metadata`) also break it in modern runtimes. |

### Narrative
The three flows are fundamentally asymmetrical. Admin chat relies on local monolith logic, surviving isolated dev environments. Customer chat is a hollow shell that attempts to bridge to a microservice. Super Agent relies on a strict HTTP bridge (`orchestrator_client.create_mission`). This means the system has three entirely different architectural paradigms active simultaneously for the same fundamental capability.

---

## 7. Dispatch Failure Root Cause Analysis

### Ranked Hypotheses
1. **(Rank 1 - Highest Confidence): Monolith-to-Microservice HTTP Bridge Failure.** The monolith runs, receives the WS message, but the `orchestrator-service` is unreachable (DNS resolution fails, container down, or wrong port).
2. **(Rank 2 - High Confidence): Payload Contract Mismatch.** The UI sends `mission_type` at the root, but the microservice expects it inside a `metadata` dictionary. This causes validation/routing failure on the orchestrator side, bubbling an error back across the bridge.
3. **(Rank 3 - Medium Confidence): WebSocket State Timeout.** The synchronous bridge call blocks the async event loop, causing the WS connection to timeout and drop before the mission run starts.

### Highest-Confidence Root Cause
The **exact** source of "Dispatch Failed" originates in `app/services/chat/handlers/strategy_handlers.py` within `MissionComplexHandler`.

When a user selects "المهمة الخارقة", the UI sends a WS message. The monolith intercepts this, routes it to `MissionComplexHandler`, and calls `start_mission()` in `app/services/overmind/entrypoint.py`. This function immediately calls `orchestrator_client.create_mission()`. If this HTTP call fails (network error, 500 from service, DNS failure), the exception is caught in the handler, which yields the hardcoded string:
`"❌ **خطأ في النظام:** لم نتمكن من بدء المهمة (Dispatch Failed)."`

This is a classic legacy bridge breakage exacerbated by a split-brain deployment model.

---

## 8. StateGraph Diagnosis

### Current Graph/State Model
The intended LangGraph implementation lives in `orchestrator-service`. However, the live monolith system uses a dummy/proxy representation of the graph (`app/services/overmind/langgraph/service.py`) that merely wraps API calls to the real microservice.

### Live Path Usage
The live system frequently bypasses the graph entirely. Admin normal chat completely circumvents LangGraph by using local intent handlers. Super Agent attempts to use the graph but fails at the bridge dispatch layer before the graph can ever initialize or stream state.

### State Ownership Problems
Because the monolith intercepts the WebSocket, it technically owns the connection state, while the orchestrator service is expected to own the graph state. This split ownership means live graph progress events cannot natively stream back to the UI without complex, error-prone proxy translation.

---

## 9. Target StateGraph Architecture for 100% API-First Microservices

To fix this catastrophe, the architecture must transition to:
1. **Correct WebSocket Ownership:** The API Gateway terminates the WS connection and directly proxies the raw TCP/WS stream to the `orchestrator-service` (or `conversation-service`). The monolith is bypassed entirely.
2. **Correct Orchestration Ownership:** `orchestrator-service` exclusively handles intent detection, mission creation, and graph execution.
3. **Correct Mission/Conversation State Ownership:** The Orchestrator/Conversation microservices write directly to their respective databases. The monolith is blind to this data.
4. **Correct Route Ownership:** `/api/chat/ws` and `/admin/api/chat/ws` must route identically at the gateway layer to the designated microservice. Role validation (Admin vs Customer) happens via JWT policy inside the microservice, not by splitting the network path.
5. **Streaming/Event Model:** LangGraph events (`RUN_STARTED`, `assistant_delta`, etc.) are yielded directly from the microservice graph nodes to the open WebSocket proxy, guaranteeing real-time sync without bridging logic.

---

## 10. Definition of “100% Microservices” for THIS Repository

This repository achieves 100% microservices ONLY when:
- **[PASS/FAIL GATE 1]:** No monolith container (`core-kernel`) is required on the default execution path for any chat or mission feature.
- **[PASS/FAIL GATE 2]:** Admin and Customer chat use the exact same backend microservice endpoint; divergence occurs only at the RBAC/policy layer.
- **[PASS/FAIL GATE 3]:** Super Agent dispatch does not use `orchestrator_client` via a monolith handler. The UI communicates directly with the orchestrator service through the gateway.
- **[PASS/FAIL GATE 4]:** `check_overmind_copy_coupling.py` returns exactly `0` overlap files.
- **[PASS/FAIL GATE 5]:** All WebSocket payload contracts are strictly typed and identical between frontend emission and microservice ingestion (no translation bridges).

---

## 11. Deep Modernization Blueprint

### Phase 0: Containment & Truth
- **Goals:** Stop the bleeding. Align local dev with production reality.
- **Deliverables:** Deprecate `docker-compose.legacy.yml` for active development. Force all dev scripts to use gateway + microservices.
- **Exit criteria:** Developers cannot accidentally run the monolith as the primary backend.

### Phase 1: Single WebSocket / Control Plane
- **Goals:** Route all WS traffic strictly to microservices.
- **Deliverables:** API Gateway configured to forward `/api/chat/ws` and `/admin/api/chat/ws` to `orchestrator-service` with 100% rollout. Delete monolithic WS routers (`app/api/routers/admin.py`, etc).
- **Exit criteria:** Monolith no longer intercepts any WS traffic.

### Phase 2: Dispatch / StateGraph Normalization
- **Goals:** Ensure payload contract matches and the StateGraph natively handles the WS stream.
- **Deliverables:** Fix frontend payload (`mission_type` vs `metadata`), verify LangGraph yields direct WS JSON, eliminate `orchestrator_client` usage in chat flows.
- **Exit criteria:** "Dispatch Failed" is mathematically impossible because the bridge is removed.

### Phase 3: Phantom-Limb Elimination
- **Goals:** Remove duplicated legacy logic.
- **Deliverables:** Delete `app/services/overmind` and `app/services/chat`.
- **Exit criteria:** Zero copy-coupling overlap.

### Phase 4: Hard-Zero Monolith Retirement
- **Goals:** Completely isolate or delete the monolith.
- **Deliverables:** `app.main` is retired. Legacy DB is migrated.
- **Exit criteria:** CogniForge operates purely on independent microservices.

---

## 12. Top 30 Structural Problems

*(Ranked by severity and architectural impact)*

1.  **CRITICAL**: Split control-plane between monolith and orchestrator.
2.  **CRITICAL**: Admin and customer normal chat route to completely different backend authorities.
3.  **CRITICAL**: Super-agent dispatch is coupled to a fragile, synchronous HTTP bridge call inside a WS stream.
4.  **CRITICAL**: The error `Dispatch Failed` masks all underlying failure classes (network, auth, timeout).
5.  **HIGH**: Dev runtime scripts default to the monolith legacy mode instead of the modern compose stack.
6.  **HIGH**: The legacy monolith profile remains fully operational and intercepts traffic.
7.  **HIGH**: `ARCHITECTURE.md` contradicts the `MICROSERVICES_CONSTITUTION.md`.
8.  **HIGH**: Phantom-limb copy-coupling overlap between `app/overmind` and microservice is massive.
9.  **HIGH**: Database state models are duplicated across app and microservice directories.
10. **HIGH**: The customer router in the monolith has a hard dependency on the orchestrator client.
11. **HIGH**: Monolith configuration lacks explicit, typed validation for microservice URLs.
12. **HIGH**: `orchestrator_client` falls back to Docker internal hostnames, failing immediately in local shell runtimes.
13. **HIGH**: Frontend payload schema for Super Agent mismatches microservice expectations (`mission_type` vs `metadata.mission_type`).
14. **HIGH**: WebSocket event contract (deltas, errors, summaries) is inconsistently applied across services.
15. **MEDIUM**: `conversation-service` is present in routing decisions but acts as a partial placeholder.
16. **MEDIUM**: Gateway canary routing lacks strict contract parity testing.
17. **MEDIUM**: User service is bypassed by local monolith auth extraction.
18. **MEDIUM**: Route ownership is fragmented across monolith, gateway, and multiple services.
19. **MEDIUM**: No single programmatic source of truth exists for live route catalogs.
20. **MEDIUM**: StateGraph usage is highly route-dependent rather than a universal orchestration pattern.
21. **MEDIUM**: Frontend contains legacy static code mixed with Next.js, complicating contract alignment.
22. **MEDIUM**: Insufficient path-level health probes in the gateway.
23. **MEDIUM**: Mission and chat lifecycle events are not normalized end-to-end.
24. **MEDIUM**: Implicit assumptions exist regarding WebSocket protocol header forwarding in the proxy.
25. **MEDIUM**: Mission dispatch lacks a distinct, structured failure taxonomy.
26. **MEDIUM**: Conversation persistence logic is split by user role.
27. **MEDIUM**: CI gates track decrease of copy-coupling, not strict elimination to zero.
28. **MEDIUM**: Outdated diagnostic files persist, conflicting with current code reality.
29. **MEDIUM**: Emergency break-glass procedures are ambiguously defined in standard flow.
30. **MEDIUM**: Architecture governance is fragmented across multiple overlapping markdown documents.

---

## 13. Top 30 Architecture Backlog Items

*(Ranked by urgency and risk reduction)*

1.  **Objective**: Deprecate monolithic WS endpoints. **DoD**: Delete `app/api/routers/admin.py` WS route.
2.  **Objective**: Fix Dev Startup Scripts. **DoD**: `scripts/start-backend.sh` launches modern compose.
3.  **Objective**: Remove Monolith Dispatch Bridge. **DoD**: Delete `MissionComplexHandler`.
4.  **Objective**: Align WS Payload Contract. **DoD**: Frontend and Microservice use identical `metadata` schema.
5.  **Objective**: Enforce Gateway WS Proxy. **DoD**: Gateway handles 100% of `/api/chat/ws` traffic natively.
6.  **Objective**: Unify Admin/Customer Chat. **DoD**: Both hit the exact same backend service endpoint.
7.  **Objective**: Purge Phantom Limb. **DoD**: `rm -rf app/services/overmind`.
8.  **Objective**: Update Constitution. **DoD**: Mark `ARCHITECTURE.md` as deprecated.
9.  **Objective**: Implement Dispatch Taxonomy. **DoD**: Errors categorized (Auth, Network, Payload).
10. **Objective**: Stream LangGraph Natively. **DoD**: Graph nodes yield directly to WS socket wrapper.
11. **Objective**: Isolate DB Models. **DoD**: Microservices do not import `app.core.domain`.
12. **Objective**: Retire `orchestrator_client`. **DoD**: HTTP client removed from monolith completely.
13. **Objective**: Canary Test Conversation Service. **DoD**: Synthetic load test validates contract.
14. **Objective**: Standardize Event Deltas. **DoD**: `assistant_delta` schema enforced by Pydantic.
15. **Objective**: Remove Local Dev Fallback URLs. **DoD**: Explicit failure if orchestration URL is unset.
16. **Objective**: Enforce Route Registry. **DoD**: CI script verifies no duplicated endpoints across services.
17. **Objective**: Role-based Validation in Microservice. **DoD**: Orchestrator verifies admin JWT natively.
18. **Objective**: Delete Monolithic Chat Orchestrator. **DoD**: `app/services/chat/orchestrator.py` removed.
19. **Objective**: End-to-End Synthetic Tests. **DoD**: Playwright test for Super Agent WS lifecycle.
20. **Objective**: Consolidate State Management. **DoD**: All mission state written exclusively by orchestrator.
21. **Objective**: Update Frontend Chat Hook. **DoD**: `useAgentSocket` aligns with orchestrator event types.
22. **Objective**: Hard-disable Monolith Port 8000. **DoD**: Monolith moved to internal unused port.
23. **Objective**: Setup Telemetry for WS Drops. **DoD**: Grafana dashboard for WS connection lifecycles.
24. **Objective**: Implement Saga for Missions. **DoD**: Distributed failures trigger correct compensating events.
25. **Objective**: Remove Legacy Profiles. **DoD**: `docker-compose.legacy.yml` deleted.
26. **Objective**: Audit Service Mesh. **DoD**: Verify inter-service HTTP calls use service discovery.
27. **Objective**: Standardize Error Emission. **DoD**: All backend errors yield standard JSON problem details.
28. **Objective**: Implement API Versioning. **DoD**: `/v1/chat/ws` enforced at gateway.
29. **Objective**: CI Governance for Imports. **DoD**: Fail CI on any `from app` in `microservices`.
30. **Objective**: Final Cutover. **DoD**: Monolith completely removed from production deployments.

---

## 14. Appendix: Evidence Index

- **Files Inspected:**
  - `app/api/routers/admin.py`: Proof of local admin chat execution.
  - `app/api/routers/customer_chat.py`: Proof of remote customer chat delegation.
  - `app/services/chat/handlers/strategy_handlers.py`: Source of the exact "Dispatch Failed" string in `MissionComplexHandler`.
  - `app/services/overmind/entrypoint.py`: Proof of the `start_mission` proxy pattern.
  - `app/infrastructure/clients/orchestrator_client.py`: The fragile HTTP bridge.
  - `docs/architecture/MICROSERVICES_CONSTITUTION.md`: The guiding microservices ruleset.
  - `scripts/fitness/check_overmind_copy_coupling.py`: Proof of massive codebase duplication.

- **Search Patterns Used:**
  - `rg "Dispatch Failed|MissionComplexHandler|DefaultChatHandler|create_mission|orchestrator_client"`
  - `rg "from app" microservices/`
  - `cat app/services/chat/handlers/strategy_handlers.py | grep -B 20 "Dispatch Failed"`

- **Key Findings by Directory:**
  - `app/`: Contains active, monolithic bridge logic that actively intercepts and fails mission requests.
  - `microservices/orchestrator_service/`: Contains the correct, intended logic but is starved of traffic or fed mismatched payloads by the gateway/monolith.
