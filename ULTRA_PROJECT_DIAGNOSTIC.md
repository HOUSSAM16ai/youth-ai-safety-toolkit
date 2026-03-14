WARNING:
This report is a forensic diagnostic audit only.
No source code was modified.
No fixes were implemented.
No files were created except this rewritten diagnostic report.
Every major claim in this report is intended to be evidence-based.
Where proof is incomplete, the report marks the claim as Likely Risk or Insufficient Evidence rather than treating it as fact.

## 1. Title
Forensic-Grade Architecture and Systems Audit — HOUSSAM16ai/NAAS-Agentic-Core

## 2. Scope and Audit Method
- **Scope audited:** repository structure, runtime entrypoints, gateway/proxy paths, websocket lifecycle, outbox/eventing path, AI orchestration graph/tool surfaces, settings/security defaults, test/CI evidence.
- **Hard method used:**
  1) Extract claimed architecture from docs/config (`docs/API_FIRST_SUMMARY.md`, `docs/ARCHITECTURE.md`, `docs/architecture/MICROSERVICES_CONSTITUTION.md`, route ownership registry).
  2) Trace actual runtime entrypoints (`app/main.py`, `app/kernel.py`, `microservices/api_gateway/main.py`, orchestrator routes/graph/state).
  3) Compare claims vs runtime behavior and classify each gap as **CONFIRMED DEFECT / CONFIRMED WEAKNESS / LIKELY RISK / INSUFFICIENT EVIDENCE**.
  4) Evaluate against elite 3–5 year standards (determinism, bounded complexity, failure semantics, auditability).
- **Evidence discipline:** all major findings include file paths + symbols + line anchors.
- **No runtime execution claims:** this report is repository-forensic, not production-traffic verification.

## 3. Executive Verdict
- **Final verdict:** **NOT ELITE**.
- **Primary reason:** multiple **Elite Disqualifiers** are confirmed in code, not just inferred from docs.
- **Architecture truth:** this repository is a **transitional hybrid with distributed-monolith characteristics**, not a clean finished microservice architecture.
- **AI stack truth:** LangGraph/DSPy/MCP/Kagent are present, but core governance and typing boundaries are too permissive and partially mocked for elite reliability.

## 4. Elite Gate Matrix (Pass/Fail)
| Elite Gate | Result | Evidence | Elite-Disqualifying if failed? |
|---|---|---|---|
| Single authoritative architecture | **FAIL** | `app/main.py` boots `RealityKernel`; `docker-compose.yml` routes primary traffic through `api-gateway`; both expose chat/runtime surfaces. (`app/main.py`, `docker-compose.yml`, `microservices/api_gateway/main.py`) | **Yes** |
| Clean bounded contexts | **FAIL** | Copy-coupling baseline explicitly tracks overlap between `app/services/overmind` and `microservices/.../overmind` (`config/overmind_copy_coupling_baseline.json`). | **Yes** |
| Deterministic event correctness | **FAIL** | Redis bridge contains unresolved contract-break commentary and forwards dict payloads with missing IDs (`app/core/redis_bus.py`); outbox publish is best-effort immediate push (`.../state.py`). | **Yes** |
| Secure-by-default posture | **FAIL** | Defaults include wildcard CORS/hosts and default admin password in app settings (`app/core/settings/base.py`), dev-secret defaults in orchestrator (`.../src/core/config.py`), default weak-ish shared secret string in user service (`microservices/user_service/settings.py`). | **Yes** |
| Hardened realtime lifecycle | **FAIL** | No explicit heartbeat, queue bounds, or backpressure in gateway WS proxy and frontend reconnect queue (`microservices/api_gateway/websockets.py`, `frontend/app/hooks/useRealtimeConnection.js`). | **Yes** |
| Strict type contracts at orchestration boundaries | **FAIL** | pervasive `Any` in integration kernel and orchestrator graph state (`app/core/integration_kernel/runtime.py`, `microservices/.../graph/main.py`) despite strict-governance claims (`app/core/governance/contracts.py`). | **Yes** |
| Observable distributed execution | **PARTIAL** | CI guardrails and health checks exist (`.github/workflows/ci.yml`, gateway `/health`); telemetry core relies on in-memory buffers + background sync (`app/telemetry/unified_observability.py`). | No |
| Risk-based test depth | **PARTIAL** | Broad CI and coverage exists (`.github/workflows/ci.yml`), but no clear load/chaos WS/eventing verification path found in active test suites. | No |
| Auditable AI graph/tool boundaries | **FAIL** | Dynamic admin-tool invocation with broad payload dicts and exception string return (`.../src/api/routes.py`), mocked TLM trust score (`.../graph/admin.py`). | **Yes** |
| Long-horizon maintainability | **FAIL** | Parallel legacy+new ownership plus overlap metric indicates unresolved migration debt (`config/overmind_copy_coupling_baseline.json`, route/runtime duplication). | **Yes** |

## 5. System Reality Inferred From Code
1. **Two concurrent runtime narratives exist**:
   - Monolithic kernel runtime in `app/` (`app/main.py`, `app/kernel.py`, `app/api/routers/registry.py`).
   - Gateway-first microservices runtime in `microservices/` + `docker-compose.yml` (`api-gateway` on `:8000`).
2. **Chat and orchestration are not singularly owned**:
   - App provides `/api/chat/ws` via `customer_chat.py` and also admin WS at `/api/chat/ws` via `admin.py`.
   - Gateway proxies `/api/chat/ws` and `/admin/api/chat/ws` to orchestrator/conversation targets.
3. **Eventing correctness is mixed-mode**:
   - Transactional outbox entities exist.
   - Publish path is still immediate best-effort Redis Pub/Sub with fallback comments and shape conversion workarounds.
4. **AI stack is component-rich but control-plane integrity is inconsistent**:
   - LangGraph state graph present.
   - State schema and tool invocation boundaries are permissive (`Any`, dynamic payloads, mocks).

## 6. Claimed Architecture vs Actual Runtime
| Claimed | Runtime Evidence | Mismatch Severity | Consequence |
|---|---|---|---|
| “100% API-First” (`docs/API_FIRST_SUMMARY.md`) | Kernel + monolith routers still active runtime code (`app/main.py`, `app/kernel.py`, `app/api/routers/registry.py`) alongside gateway/microservices runtime (`docker-compose.yml`). | **High** | Ambiguous operational truth, incident routing ambiguity. |
| “Strict service boundaries” (`docs/ARCHITECTURE.md`) | Overmind overlap tracked explicitly: owner + legacy snapshot and overlap metric (`config/overmind_copy_coupling_baseline.json`). | **Critical** | Duplicated authority, drift risk, inconsistent bugfix propagation. |
| “Contract-first deterministic interfaces” | Redis bridge and mission stream contain contract mismatch workaround comments and dict-to-model reconstruction (`app/core/redis_bus.py`, `.../services/overmind/state.py`). | **Critical** | Event shape drift under failure/replay; consumer correctness fragile. |
| “Secure defaults” (`app/core/settings/base.py` docstring) | Runtime defaults include `BACKEND_CORS_ORIGINS=['*']`, `ALLOWED_HOSTS=['*']`, default admin password, dev-secret defaults elsewhere. | **High** | Deployment misconfiguration can carry dangerous defaults to real environments. |

## 7. Overall Weighted Score
- **Overall score:** **49/100**.
- **Elite threshold used:** **90/100**.
- **Confidence:** High for architecture/type/eventing/security-default findings; medium for operational SLO maturity where runtime deployment evidence is absent.

## 8. Category Scores With Evidence
| Category | Score /10 | Why this score (evidence) |
|---|---:|---|
| Computer science rigor | 5.0 | Good abstractions exist (`Config -> AppState -> WeavedApp` in `app/core/app_blueprint.py`), but contract discipline is violated by `Any` in core orchestration interfaces. |
| Software architecture | 4.0 | Simultaneous monolith kernel and microservices gateway topology with overlapping domains. |
| Distributed systems | 4.0 | Outbox present but delivery semantics are best-effort + Redis Pub/Sub non-durable path and adapter hacks. |
| Backend engineering | 6.0 | Structured FastAPI composition and DI patterns exist; failure semantics and boundary ownership are inconsistent. |
| Frontend/realtime engineering | 4.0 | Reconnect logic exists; no bounded queue, heartbeat, or explicit backpressure in WS paths. |
| Data engineering | 5.0 | Service-specific databases declared in compose; insufficient hard evidence of indexing/RLS enforcement governance at runtime boundaries. |
| Security | 4.0 | Production validators exist, but insecure defaults and broad tool invocation surfaces remain. |
| Reliability/SRE | 5.0 | CI gates are good; distributed telemetry and incident-grade observability are partial/in-memory-centered. |
| AI systems engineering | 4.0 | LangGraph integration exists; typed state and trust enforcement are weak/partially mocked. |
| Agentic orchestration | 4.0 | Orchestration graph exists; deterministic controls coexist with permissive dynamic tool execution and loose payload typing. |
| Future-proof maintainability | 4.0 | Explicit copy-coupling + dual ownership indicates ongoing structural debt with compounding risk. |

## 9. Elite Disqualifiers
1. **Duplicated domain authority across legacy/app and microservices/orchestrator paths**.
2. **Deterministic event correctness not proven; bridge/outbox contract drift explicitly documented in code comments.**
3. **Realtime lifecycle lacks explicit hardening for slow consumers and bounded buffering.**
4. **Strict typing claims contradicted by `Any` in AI/orchestration boundaries.**
5. **Secure-by-default posture fails due to permissive defaults that can escape via environment misconfiguration.**

## 10. Critical Findings
### CF-1 — Split Runtime Authority (Monolith + Microservices)
- **Classification:** CONFIRMED DEFECT
- **Severity:** Elite Disqualifier
- **Evidence:**
  - `app/main.py` -> `RealityKernel` boot (`settings`, `_kernel`, `app`).
  - `app/api/routers/registry.py` includes chat/admin/system/content routers.
  - `docker-compose.yml` exposes `api-gateway` on `8000` as primary external edge.
  - `microservices/api_gateway/main.py` defines edge WS and HTTP proxy routes.
- **Technical interpretation:** The repository keeps two active runtime authorities for API behavior.
- **Why it matters:** Operational ownership, incident triage, and contract evolution become ambiguous.
- **Failure mode:** bug fixed in one runtime path but not the other; production behavior depends on deploy topology.
- **Blast radius:** API contracts, auth behavior, websocket behavior, and observability correlations.
- **Competent implementation:** temporary dual-path behind explicit kill-switches + deprecation timetable.
- **Elite implementation:** one authoritative runtime topology enforced by CI gate and release policy.

### CF-2 — Event Contract Drift in Redis Bridge / Mission Stream Path
- **Classification:** CONFIRMED DEFECT
- **Severity:** Elite Disqualifier
- **Evidence:**
  - `app/core/redis_bus.py` comments (lines around payload mismatch, missing event id, “BREAKING CHANGE”, “fix later”).
  - `microservices/orchestrator_service/src/services/overmind/state.py` reconstructs transient `MissionEvent` from dict in `monitor_mission_events`.
  - Same file logs outbox as transactional intention, then immediate best-effort publish.
- **Technical interpretation:** Event consumers rely on mixed object/dict payloads with ad hoc repair logic.
- **Why it matters:** replay, ordering, dedupe, and idempotency semantics cannot be trusted under failure.
- **Failure mode:** lost/duplicated/malformed events causing UI state divergence or stuck workflows.
- **Blast radius:** mission timeline, websocket streaming, downstream consumers, audit trail integrity.
- **Competent implementation:** versioned event schema + immutable event IDs + strict parser.
- **Elite implementation:** durable stream semantics, idempotent consumer offsets, formally tested failure matrix.

### CF-3 — Type Discipline Collapse at AI/Orchestration Boundaries
- **Classification:** CONFIRMED DEFECT
- **Severity:** Elite Disqualifier
- **Evidence:**
  - `app/core/governance/contracts.py` claims forbidding loose contracts.
  - `app/core/integration_kernel/runtime.py` uses `Any` for driver registration and return payloads.
  - `microservices/orchestrator_service/src/services/overmind/graph/main.py` defines `AgentState` with multiple `Any` fields.
- **Technical interpretation:** critical boundaries are dynamically typed where determinism is required.
- **Why it matters:** contract drift becomes runtime-only failure; static analysis value is sharply reduced.
- **Failure mode:** latent schema mismatch and unsafe tool payload propagation.
- **Blast radius:** AI orchestration correctness, tool routing, audit logs, API responses.
- **Competent implementation:** typed DTOs at every external/internal boundary.
- **Elite implementation:** schema evolution governance + typed contracts with compatibility tests.

## 11. High Severity Findings
### HF-1 — Realtime Lifecycle Not Production-Hardened
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** High
- **Evidence:**
  - `microservices/api_gateway/websockets.py` loops forward messages with no queue bounds, no heartbeat, no explicit rate/backpressure policy.
  - `frontend/app/hooks/useRealtimeConnection.js` has unbounded `pendingQueue` and reconnection loop with no max queue size.
- **Technical interpretation:** functional websocket transport exists but stress behavior is uncontrolled.
- **Failure mode:** memory growth, fanout collapse, reconnect storm amplification.
- **Blast radius:** chat UX, gateway stability, orchestrator load.
- **Competent:** bounded queues + drop/priority policy + ping/pong health.
- **Elite:** protocol contract + per-connection budgets + load-tested reconnect/fanout behavior.

### HF-2 — Security Defaults Unsafe Outside Strict Production Validation
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** High
- **Evidence:**
  - `app/core/settings/base.py`: defaults `BACKEND_CORS_ORIGINS=['*']`, `ALLOWED_HOSTS=['*']`, default `ADMIN_PASSWORD`.
  - `microservices/orchestrator_service/src/core/config.py`: `SECRET_KEY='dev_secret_key'`, CORS `['*']` until env gated.
  - `microservices/user_service/settings.py`: fallback secret string values.
- **Technical interpretation:** security is policy-enforced only in production/staging branches; defaults remain permissive.
- **Failure mode:** staging-like or mis-tagged production deployment runs with permissive trust surfaces.
- **Blast radius:** auth/session abuse, cross-origin exposure, admin account compromise risk.
- **Competent:** secure defaults + explicit local-dev override mechanism.
- **Elite:** deny-by-default in all environments, policy-as-code for exception scopes.

### HF-3 — Dynamic Admin Tool Invocation Returns Raw Exception Text
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** High
- **Evidence:** `microservices/orchestrator_service/src/api/routes.py` dynamic `/api/v1/tools/{tool}/invoke` handlers accept `dict[str, Any]` payload and return `{"message": str(e)}` on exceptions.
- **Technical interpretation:** tool invocation surface is broad and error output is directly propagated.
- **Failure mode:** internal details leakage + weak input boundary control.
- **Blast radius:** admin interface, internal tool ecosystem, security posture.
- **Competent:** explicit typed request models per tool with sanitized error taxonomy.
- **Elite:** policy-guarded tool broker, signed capability tokens, full audit trail and red-team tests.

## 12. Medium Severity Findings
### MF-1 — Outbox Relay Is Optional While Immediate Publish Is Preferred
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** Medium
- **Evidence:** `.../src/core/config.py` `OUTBOX_RELAY_ENABLED=False` by default; `.../state.py` immediately attempts publish after commit and marks outbox states.
- **Interpretation:** reliability path exists but default operational path remains best-effort latency path.
- **Failure mode:** transient Redis failure yields delayed/partial dissemination until manual/system relay action.
- **Blast radius:** mission event delivery and user-visible progress streams.

### MF-2 — Docs Claiming Deterministic Contracts Conflict with Runtime Envelope Diversity
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** Medium
- **Evidence:** `docs/contracts/consumer/gateway_chat_content_contracts.json` outgoing required fields `status,response`; runtime WS handlers send `type/payload` envelopes (`app/api/routers/customer_chat.py`, `app/api/routers/admin.py`).
- **Interpretation:** contract docs and runtime message schemas are not clearly converged.
- **Failure mode:** client parser mismatch and brittle compatibility handling.
- **Blast radius:** frontend clients, gateway transformations, contract testing accuracy.

### MF-3 — Observability Core Uses In-Memory Buffers + Background Sync
- **Classification:** CONFIRMED WEAKNESS
- **Severity:** Medium
- **Evidence:** `app/telemetry/unified_observability.py` uses deque buffers and periodic flush loops.
- **Interpretation:** this is workable but not equivalent to guaranteed end-to-end distributed telemetry durability.
- **Failure mode:** signal loss on process crash/restart before flush.
- **Blast radius:** post-incident forensic quality.

## 13. Confirmed Weaknesses
- Runtime topology ambiguity between app kernel and microservice gateway paths.
- Realtime transport without explicit bounded memory/backpressure contracts.
- Security posture depends heavily on correct environment tagging.
- Tool governance uses dynamic payload dicts at sensitive boundaries.
- Observability pipeline partially custom/in-memory.

## 14. Likely Risks
- **Retry storm risk under partial failures** in websocket reconnect flows due exponential retries + no global coordination (`frontend/.../useRealtimeConnection.js`).
- **Contract drift risk** between docs and runtime where envelope schemas differ.
- **Operational drift risk** because legacy and modern copies of overmind code remain tracked with high overlap metric (`config/overmind_copy_coupling_baseline.json`).

## 15. Insufficient Evidence Areas
- **RLS enforcement truth for Supabase:** references to Supabase vector store exist, but repo evidence here does not prove active RLS policies in deployed DB.
- **Chaos/load validation depth:** CI and tests are broad, but definitive sustained-load websocket/eventing chaos harness evidence was not confirmed in active workflows.
- **mTLS/zero-trust internal service enforcement at runtime:** infra manifests exist, but repository evidence here does not prove active enforcement in running environments.

## 16. Architecture Forensics
### A. Architecture Truth Answers
- **Microservices vs distributed monolith vs hybrid:** **Hybrid with distributed-monolith traits**.
- **Duplicated domain ownership between `app/` and `microservices/`:** **Confirmed** (chat/orchestration surfaces and overmind copy-coupling baseline).
- **Gateway as clean edge boundary or migration crutch:** currently **migration crutch + edge**; includes rollout/parity guard logic targeting conversation/orchestrator switching.
- **Single authoritative topology:** **No**; multiple overlapping truths exist.

## 17. Backend Forensics
### B. FastAPI / Backend Truth Answers
- **Business logic in routers:** mixed; some routers delegate properly, others host dynamic tool dispatch and direct SQL operations (`.../src/api/routes.py`).
- **DI/lifespan discipline:** present but inconsistent fail-fast behavior (`app/kernel.py` catches and logs startup failures then continues for several components).
- **Transport/domain boundaries:** partially clean; breached by broad dict payloads and raw exception responses in tool APIs.
- **Failure semantics deterministic?:** not fully deterministic across startup and eventing paths.

## 18. Realtime / WebSocket Forensics
### D. Realtime Truth Answers
- **Protocol contract or just functional passing?** Functional passing with partial contract docs; runtime envelopes vary (`type/payload`), doc contract expects different required fields.
- **Heartbeat/auth lifecycle/cancellation/backpressure/limits:**
  - Auth lifecycle exists (JWT subprotocol + fallback query token restrictions by env).
  - Heartbeat/backpressure/queue bounds: **not explicitly enforced** in observed code.
- **Stress behavior:** slow consumers and reconnect storms can accumulate queued messages on client and unbounded forwarding tasks on proxy.

## 19. Data / Cache / Eventing Forensics
### C + E Truth Answers
- **Data layer engineered vs merely wired:** engineered in parts (dedicated DB services in compose, model schemas), but event correctness surfaces remain partially wired/adaptive.
- **Outbox correctness under failure:** implementation exists but semantics are mixed (best-effort publish + optional relay + conversion hacks).
- **Redis role:** used as pub/sub transport where durability is not intrinsic.
- **Retries/timeouts/idempotency rigor:** idempotency fields exist, but end-to-end proof of exactly-once/at-least-once contract is absent.
- **First correctness break point in partial failure:** event dissemination path (Redis publish/bridge/consumer shape handling).

## 20. AI / Agents / Reasoning Forensics
### G Truth Answers
- **LangGraph real state machine or branding?** Real `StateGraph` usage is present (`graph/main.py`, `graph/admin.py`).
- **Graph state schemas explicit/enforceable?** Partially explicit via `TypedDict`, but diluted by `Any` fields.
- **Node transitions controlled?** Explicit edges/conditional edges exist, but fallback pass-through nodes on import failure reduce guarantees (`_load_search_nodes`).
- **Multi-agent boundaries justified?** Partially; overlap between legacy and microservice overmind paths weakens boundary authority.
- **Tool routing typed/bounded/auditable?** Not sufficiently; dynamic dict payload invoke routes, permissive schema `extra='ignore'`, and mock wrappers.
- **Retrieval/reranking placement:** present architecturally in graph chain, but reliability and evaluation evidence insufficient for elite confidence.
- **DSPy usage meaningful/evaluation-backed?** DSPy classifier invoked; rigorous evaluation framework proof is insufficient in reviewed runtime paths.
- **MCP exposure necessary/safe?** MCP metadata and tool contracts exist; safety boundary is partial due to dynamic invocation and broad exception handling.
- **TLM/Kagent coherent?** `MockTLM` returns constant score 0.95; this is explicit placeholder, not operational trust system.
- **Can loops recurse/drift/fail opaquely?** conditional loops exist (`validator` can route to supervisor on fail), and failures can degrade into generic errors without strict typed remediation.
- **Any usage impact in AI-critical paths:** materially degrades contract integrity.

## 21. Security Forensics
### F Truth Answers
- **Defaults secure or conditionally secure?** conditionally secure.
- **Secrets/CORS/hosts/tool execution/WS auth hardened?** partially; production validators are strong, defaults remain permissive, and tool invoke path is broad.
- **Non-prod laxness escaping to deployment risk?** confirmed risk due default permissive values and environment-dependent gates.
- **Exception leakage paths?** yes, tool invocation returns `str(e)`.

## 22. Reliability / Observability Forensics
### H Truth Answers
- **Do we have incident-grade observability?** partial.
- **Evidence:** CI guardrails and health checks are substantial; telemetry implementation includes custom in-memory buffers and periodic flush.
- **Gap:** clear evidence of fully durable distributed trace correlation across services/tool calls is insufficient.

## 23. Testing / Verification Forensics
- CI pipeline runs lint, contracts, guardrails, and pytest with coverage (`.github/workflows/ci.yml`).
- Contract scripts and architectural guardrails exist.
- **Gap:** explicit load/chaos/security-abuse/AI-eval depth is not conclusively demonstrated in audited active workflows.
- **Conclusion:** safety to evolve is **partial**, not elite-assured.

## 24. Performance / Scalability Forensics
- Good signals: dedicated service databases and compose topology for separation.
- Weak signals: websocket and eventing paths lack explicit bounded-resource controls.
- No confirmed evidence here of sustained high-load benchmark discipline in repository workflows.

## 25. Future-Proofing Forensics
- **Will this survive team/product/AI complexity growth?** not in current shape without boundary consolidation.
- **Design choices that age badly first:** duplicated overmind authority, permissive typing in orchestration interfaces, and mixed event contracts.
- **Compounding weaknesses:** each added agent/tool increases drift and operational ambiguity unless canonical control-plane contracts are enforced.

## 26. Top 10 Gaps Blocking Elite Status
1. Dual runtime authority (app kernel + gateway/microservices).
2. Duplicated overmind ownership with measured overlap.
3. Event bus contract drift and dict/model duality.
4. Redis pub/sub used as critical path without durable semantics proof.
5. Unbounded WS queueing/backpressure controls absent.
6. `Any` in AI-critical orchestration schemas and drivers.
7. Dynamic admin tool invocation with broad payloads + exception leakage.
8. Security defaults permissive until environment gates are correctly set.
9. TLM trust gate is mocked, not operational.
10. Docs overclaim certainty beyond runtime proof.

## 27. What a Truly Elite Version Would Require
- Single executable architecture truth, enforced in CI and deployment manifests.
- Hard decommission of duplicate authority paths with compatibility proxy sunset plan.
- Versioned, typed event contracts with deterministic idempotency and replay-safe semantics.
- WS protocol spec with explicit heartbeat, bounded queues, backpressure, and load tests.
- Typed tool contracts per capability with policy guardrails, audit logs, and sanitized errors.
- Replace `Any` at orchestration boundaries with strict schemas and compatibility tests.
- Real trust gate replacing mock TLM, with measurable evaluation and rollback policies.
- Security defaults deny-by-default in all environments with explicit development exemptions.

## 28. Final Answer: Is This Repository Elite?
**No.**

This repository demonstrates serious intent and substantial engineering effort, but it does not meet elite long-horizon standards because multiple elite-disqualifying conditions are materially confirmed in the codebase.

## 29. Appendix A: Evidence Index by File Path
| File Path | Key Symbols Reviewed | Why It Matters |
|---|---|---|
| `app/main.py` | `_kernel`, `app`, `create_app` | Confirms monolith kernel runtime entrypoint still active. |
| `app/kernel.py` | `RealityKernel`, `_handle_lifespan_events`, `_validate_contract_alignment` | Startup behavior, fail-fast vs warn-and-continue, contract checks. |
| `app/core/app_blueprint.py` | `build_kernel_spec`, `build_middleware_stack` | Declarative kernel composition and middleware/router assembly. |
| `app/api/routers/registry.py` | `base_router_registry` | Confirms active app router ownership including chat/admin/content. |
| `app/api/routers/customer_chat.py` | `chat_stream_ws` | Runtime WS envelope shape and event normalization behavior. |
| `app/api/routers/admin.py` | `chat_stream_ws` | Admin chat WS path in app runtime (overlap with gateway narrative). |
| `app/api/routers/ws_auth.py` | `extract_websocket_auth` | Auth lifecycle and query-token fallback rules. |
| `app/core/settings/base.py` | `AppSettings`, production validators, defaults | Security defaults vs conditional hardening. |
| `app/core/redis_bus.py` | `RedisEventBridge._listen_loop` | Explicit event contract mismatch commentary and forwarding behavior. |
| `app/core/event_bus.py` | `EventBus.publish/subscribe_queue` | In-memory queue semantics and unbounded queue creation.
| `app/core/integration_kernel/runtime.py` | `register_driver`, `run_workflow`, `act` | `Any` usage at orchestration boundaries. |
| `app/core/governance/contracts.py` | `GovernanceModel` | Stated strict contract governance baseline. |
| `microservices/api_gateway/main.py` | `chat_ws_proxy`, `admin_chat_ws_proxy`, lifespan | Gateway edge routing and websocket proxy role. |
| `microservices/api_gateway/websockets.py` | `websocket_proxy` | WS lifecycle controls and absence of bounds/backpressure.
| `microservices/orchestrator_service/src/api/routes.py` | dynamic tool invoke endpoints, outbox relay endpoint | Tool-safety boundary and operational control APIs. |
| `microservices/orchestrator_service/src/services/overmind/state.py` | `log_event`, `monitor_mission_events` | Outbox + publish semantics and dict-to-model repair path. |
| `microservices/orchestrator_service/src/services/overmind/graph/main.py` | `AgentState`, `_load_search_nodes`, graph edges | LangGraph orchestration and `Any` in state schema. |
| `microservices/orchestrator_service/src/services/overmind/graph/admin.py` | `MockTLM`, `ValidateAccessNode`, `ExecuteToolNode` | AI trust and admin-tool control realism. |
| `microservices/orchestrator_service/src/services/overmind/graph/mcp_mock.py` | `kagent_tool` | MCP/Kagent wrapping reality. |
| `microservices/orchestrator_service/src/core/config.py` | `Settings` defaults + validators | Orchestrator security and outbox-relay default posture. |
| `microservices/orchestrator_service/src/core/event_bus.py` | `publish`, `subscribe` | Redis Pub/Sub delivery role. |
| `microservices/user_service/settings.py` | `UserServiceSettings` | Service secret defaults and environment hardening policy. |
| `frontend/app/hooks/useRealtimeConnection.js` | `pendingQueue`, reconnect logic | Client-side realtime resilience and memory risk. |
| `frontend/app/hooks/useAgentSocket.js` | ws URL building + event handling | Runtime contract consumption and client event envelope assumptions. |
| `docker-compose.yml` | service topology, gateway port ownership | Declared runtime topology and service decomposition intent. |
| `docs/API_FIRST_SUMMARY.md` | “100% API-First” claims | Claimed certainty benchmark for docs-vs-runtime checks. |
| `docs/ARCHITECTURE.md` | strict boundaries claims | Claimed architecture principles baseline. |
| `docs/architecture/MICROSERVICES_CONSTITUTION.md` | laws 1..100 | Elite constitutional standard used for comparison. |
| `config/route_ownership_registry.json` | route owners for chat/system/services | Declared ownership map for mismatch analysis. |
| `config/overmind_copy_coupling_baseline.json` | overlap metric + ownership | Direct proof of unresolved duplicate authority during migration. |
| `.github/workflows/ci.yml` | lint/contracts/guardrails/tests jobs | Verification rigor baseline and limits.

## 30. Appendix B: Evidence Index by Symbol
| Symbol | File Path | Architectural Relevance | Findings Supported |
|---|---|---|---|
| `RealityKernel` | `app/kernel.py` | Monolith kernel runtime authority | CF-1, backend consistency |
| `base_router_registry` | `app/api/routers/registry.py` | App route ownership | CF-1, architecture mismatch |
| `chat_stream_ws` (customer) | `app/api/routers/customer_chat.py` | Realtime payload behavior | HF-1, MF-2 |
| `chat_stream_ws` (admin) | `app/api/routers/admin.py` | Admin realtime path in app | CF-1 |
| `extract_websocket_auth` | `app/api/routers/ws_auth.py` | WS auth lifecycle and fallback | security forensics |
| `RedisEventBridge._listen_loop` | `app/core/redis_bus.py` | Cross-system event adaptation | CF-2 |
| `EventBus.subscribe_queue` | `app/core/event_bus.py` | Queue semantics | HF-1, eventing risk |
| `IntegrationKernel.register_driver` | `app/core/integration_kernel/runtime.py` | AI/orchestration boundary typing | CF-3 |
| `GovernanceModel` | `app/core/governance/contracts.py` | Claimed strict contracts | CF-3 contradiction |
| `chat_ws_proxy` | `microservices/api_gateway/main.py` | Edge WS path | CF-1, HF-1 |
| `websocket_proxy` | `microservices/api_gateway/websockets.py` | WS forwarding lifecycle | HF-1 |
| `invoke_admin_tool` | `microservices/.../api/routes.py` | Tool invocation safety boundary | HF-3 |
| `MissionStateManager.log_event` | `microservices/.../state.py` | Outbox + publish semantics | CF-2, MF-1 |
| `MissionStateManager.monitor_mission_events` | `microservices/.../state.py` | Event stream reconstruction/dedupe | CF-2 |
| `AgentState` | `microservices/.../graph/main.py` | LangGraph state schema strictness | CF-3 |
| `_load_search_nodes` | `microservices/.../graph/main.py` | Dependency-failure fallback behavior | AI reliability risk |
| `MockTLM.get_trustworthiness_score` | `microservices/.../graph/admin.py` | Trust gate realism | HF-3, AI forensics |
| `ValidateAccessNode.__call__` | `microservices/.../graph/admin.py` | Access enforcement realism | security/AI risk |
| `kagent_tool` | `microservices/.../graph/mcp_mock.py` | MCP/Kagent wrapper implementation | AI stack realism |
| `Settings.validate_production_security` | `microservices/.../core/config.py` | Conditional hardening | HF-2 |
| `UserServiceSettings.SECRET_KEY` | `microservices/user_service/settings.py` | Secret default posture | HF-2 |
| `pendingQueue` | `frontend/.../useRealtimeConnection.js` | Slow-consumer/reconnect memory behavior | HF-1 |

## 31. Appendix C: Claims Requiring More Proof
| Claim | Status | Why |
|---|---|---|
| “Supabase RLS is enforced for all sensitive retrieval paths” | **absent evidence** | Supabase vector-store usage is visible, but enforced policy artifacts and runtime checks are not fully proven here. |
| “System has chaos-tested websocket resilience” | **absent evidence** | No definitive active chaos/load workflow evidence found in reviewed CI/workflows. |
| “Zero-trust mTLS is active service-to-service in deployed runtime” | **partially proven** | Infra manifests mention mesh/otel/k8s patterns, but activation and enforcement in real runtime are not proven from this audit scope. |
| “TLM trust scoring is operationally meaningful” | **contradicted by code** | `MockTLM` fixed-score placeholder demonstrates non-production trust gate. |
| “Single canonical architecture currently in production” | **contradicted by code** | Coexistence of app kernel runtime and gateway microservices runtime is explicit in repository entrypoints/config. |
