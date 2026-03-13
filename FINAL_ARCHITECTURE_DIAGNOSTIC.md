# التقرير التشخيصي الاستقصائي (Forensic Architecture Diagnostic Report)
## النظام: NAAS-Agentic-Core (EL-NUKHBA)

---

# 1) Executive Summary (الملخص التنفيذي وأخطر المشاكل)

هذا التقرير يستند إلى فحص معماري جذري ومباشر لشيفرة المصدر (100% Evidence-Based). تم اكتشاف عدة مشاكل جوهرية تهدد استقرار النظام التشغيلي وتمزق مفهوم "Single Truth" المعماري.

### 1. Split-Brain Routing and Circular Streaming (P0)
- **Severity**: P0 (Critical)
- **Confidence**: Confirmed
- **Evidence**:
  - في `microservices/api_gateway/config.py`، إذا لم يكن `CONVERSATION_PARITY_VERIFIED=true` يتم توجيه الـ WS إلى `ORCHESTRATOR_SERVICE_URL`.
  - المونوليث `app/api/routers/customer_chat.py` يملك `/ws` (الذي يُنادى عبر `/api/chat/ws`) ويقوم بعمل `ChatOrchestrator.dispatch()`.
  - في `ChatOrchestrator.process()` (في `app/services/chat/orchestrator.py`) يتم التفويض مرة أخرى إلى `orchestrator_client.chat_with_agent` إذا كانت النية وكيلية (Agent Intent)، وهذا يعود لضرب خدمة الأوركستراتور كأنها خدمة ميكروية.
- **Why it matters**: وجود مسارين لمعالجة المحادثة (الأساسي عبر المونوليث الذي يُكلّم الـ Orchestrator عبر HTTP Client، والثاني الذي يمكن أن يوجه الـ WebSocket مباشرة من الـ Gateway للـ Orchestrator في حالة التحديث) يخلق Split-Brain كامل في ملكية حالة الـ WebSocket وتخزين البيانات.
- **Root Cause**: معمارية "Strangler Fig" غير المكتملة. Gateway يوجّه إلى Microservice لكن الواجهة القديمة لا تزال نشطة وتُكلّم الـ Microservice بنفسها كـ Client.
- **Shortest Safe Fix**: إزالة وكالة توجيه الـ HTTP من قلب المونوليث وتفعيل الـ Parity Cutover بالكامل نحو Orchestrator للـ WebSockets أو إيقاف توجيه الـ Gateway المزدوج.
- **Long-term Fix**: نقل Ownership المحادثة التعليمية تماماً إلى `orchestrator-service` وتفكيك طبقة `app/services/chat`.

### 2. Async Event Loop Blocking Risks in LangGraph Node (P1)
- **Severity**: P1 (High)
- **Confidence**: Confirmed
- **Evidence**:
  - `microservices/orchestrator_service/src/services/overmind/graph/main.py`
  - في `SupervisorNode.__call__` يتم استدعاء `dspy.ChainOfThought(AdminIntentClassifier)(query=query)` بشكل متزامن (Synchronous Call) داخل مسار غير متزامن. لا يوجد استخدام لـ `to_thread`.
- **Why it matters**: استدعاء DSPy، وهو يقوم بطلب LLM Network Call أو Inference متزامن، سيقوم بتجميد (Blocking) الـ Async Event Loop الخاص بـ FastAPI لخدمة الأوركستراتور بأكملها مما يؤدي إلى انقطاع كافة اتصالات WebSocket.
- **Root Cause**: خلط كود استنتاجي (Synchronous DSPy) في عقد LangGraph دون الالتفاف حوله بـ `asyncio.to_thread` أو `loop.run_in_executor`.
- **Shortest Safe Fix**: إضافة `await asyncio.to_thread(self.dspy_classifier, query=query)` أو استخدام واجهات DSPy غير المتزامنة إن وجدت.
- **Long-term Fix**: فرض حظر Lint/CI على أي I/O متزامن داخل دوال الـ Node في LangGraph.

### 3. Gateway WebSocket Proxy Leaking and Connection Timeouts (P1)
- **Severity**: P1 (High)
- **Confidence**: Confirmed
- **Evidence**: `microservices/api_gateway/websockets.py`
  - في `websocket_proxy` يتم استخدام `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` لانتظار `client_to_target` و `target_to_client`.
  - إذا انتهت إحدى المهام، يتم عمل `task.cancel()` للأخرى. ولكن لا يوجد ضمان لإغلاق الـ WebSocket الهدف (`target_ws`) بشكل آمن دائماً إذا حصل إغلاق فجائي للشبكة دون صدور `WebSocketDisconnect`.
  - الدليل الأقوى: `httpx.AsyncClient` في `GatewayProxy.forward` يحتوي Timeout، لكن مسار الـ WebSocket يستخدم مكتبة `websockets` دون Timeout Idle Connection واضح للـ PING/PONG.
- **Why it matters**: سيؤدي ذلك إلى تراكم اتصالات "Zombie WebSockets" مفتوحة تستهلك ذاكرة الـ API Gateway حتى الانهيار OOM (Out of Memory).
- **Root Cause**: غياب `ping_interval` و `ping_timeout` في إعدادات الاتصال بمكتبة `websockets.connect`، والاعتماد المطلق على الكشف المحلي للانقطاع.
- **Shortest Safe Fix**: إضافة `ping_interval=20, ping_timeout=20` في `websockets.connect`.

### 4. Non-Durable Pub/Sub for Mission Eventing (P1)
- **Severity**: P1 (High)
- **Confidence**: Confirmed
- **Evidence**: `microservices/orchestrator_service/src/api/routes.py` (سطر 268) في `stream_mission_ws`.
  - يتم جلب السجل القديم من الداتابيز `state_manager.get_mission_events(mission_id)`.
  - ثم يتم الاستماع `event_bus.subscribe(channel)` عبر Redis Pub/Sub عادي (وليس Redis Streams).
- **Why it matters**: الـ Pub/Sub في Redis هو "Fire and Forget". أي حدث (Event) ينطلق في اللحظة بين جلب الأحداث القديمة وبدء الاستماع الجديد سيضيع إلى الأبد (Race Condition/Event Loss).
- **Root Cause**: الاعتماد على Pub/Sub للمزامنة بين معالجة الـ Mission في الخلفية وبثها لعميل UI.
- **Shortest Safe Fix**: استخدام "Redis Streams" مع Consumer Groups أو عمل Polling آمن للحالة مع Outbox Pattern.

### 5. Insecure JSON Extraction from Streaming Payloads (P2)
- **Severity**: P2 (Medium - Reliability)
- **Confidence**: Confirmed
- **Evidence**: `app/services/admin/chat_streamer.py` و `app/services/chat/orchestrator.py`.
  - يتم فحص الكتل المتدفقة لاكتشاف ما إذا كانت JSON عبر `final_content.startswith("{") and final_content.endswith("}")` ثم `json.loads(final_content)`.
- **Why it matters**: محاولات فك تشفير JSON بهذه الطريقة في البث الحي (Streaming chunks) هشة جداً وتنهار إذا وصل كود JSON مجزأ على دفعتين (Chunk 1: `{"type": "e`, Chunk 2: `rror"...}`).
- **Root Cause**: الـ Client (`orchestrator_client`) لا يرسل SSE مهيكل دائماً بل نصوص خام أو نصوص تبدو كـ JSON وتُمزج في الـ Chunking.
- **Shortest Safe Fix**: استخدام بروتوكول SSE صريح أو سطر/سطر (JSON Lines) بدلاً من محاولة تخمين محتوى السلسلة المجزأة.

### 6. Misaligned Pacing Strategy and Fake Streams (P2)
- **Severity**: P2
- **Confidence**: Confirmed
- **Evidence**: `app/services/admin/streaming/service.py`
  - تقوم `SmartTokenChunker` أو `async_stream_response` بجمع النصوص ثم عمل `await self.sleep(delay_ms / MS_TO_SECONDS)` لمحاكاة استجابة بشرية (Pacing).
- **Why it matters**: في نظام وكلاء متعددين يعاني من عبء التشغيل، إجبار النظام على Sleep إضافي لمحاكاة التحدث البشري (Pacing) يستهلك الـ Event Loop، كما أنه يجعل النظام معقداً بدون ضرورة وظيفية.
- **Root Cause**: تصميم يعطي أولوية للمحاكاة المرئية في الـ Backend بدلاً من معالجتها في الـ Frontend.

### 7. Over-Segmentation and Unused Abstractions in Boundaries (P2)
- **Severity**: P2
- **Confidence**: Confirmed
- **Evidence**: هناك فصل معقد في `app/services/boundaries` بين `AdminChatBoundaryService` و `CustomerChatBoundaryService`، وكلاهما يفوض إلى `ChatOrchestrator` أو يستخدم أنماطاً متطابقة للبث، وكلاهما يُدار بواسطة `ChatRoleDispatcher`.
- **Why it matters**: الكود يقرأ كأنه "Enterprise FizzBuzz". مئات الأسطر من الكود لنفس المسار.
- **Shortest Safe Fix**: دمج مسارات الدردشة تحت هندسة LangGraph الموحدة وحذف الـ Boundaries Service.

### 8. Potential Retry Loop Exhaustion resulting in unlogged drops (P2)
- **Severity**: P2
- **Confidence**: Confirmed
- **Evidence**: `microservices/api_gateway/proxy.py` في حلقة الـ `for attempt in range(retries + 1)`.
  - التعليق يقول `request.stream() consumes the receive channel`. إذا تمت قراءة الستريم في المحاولة الأولى وفشلت، المحاولة الثانية ستأخذ `request.stream()` مستنزف ولن يتم تمرير الـ Body، مما قد يتسبب بخطأ لا إرادي أو صامت في الجهة الأخرى (Upstream).
- **Why it matters**: طلبات الـ POST مع Body كبير قابلة للمحاولة لكنها ستفشل صمتاً أو تتسبب بـ Bad Request في الـ retry.

---

# 2) Architecture Truth Map

### Service Inventory (As Proven by Code)
1. **API Gateway** (`api_gateway/main.py`): The single entry point on port 8000. Proxies HTTP and WS. Contains Smart Routing logic and Circuit Breakers.
2. **Orchestrator Service** (`orchestrator_service/main.py`): The "Overmind". Port 8006. Uses LangGraph to direct traffic (`create_unified_graph`). Contains Chat endpoints and Mission control.
3. **Conversation Service** (`conversation_service/main.py`): Currently an empty stub / facade returning `{"status": "ok", "service": "conversation-service"}` to provide architectural parity flags.
4. **App (Legacy Monolith)** (`app/main.py` & `app/kernel.py`): Still contains massive domain logic, boundary services, routing limits, semantic caching. The gateway bypasses it for modern routes, but its models and routers are still compiled.
5. **Planning/Memory/User/Research/Reasoning/Observability**: Defined in Compose and Gateway, but Orchestrator treats some of them as direct Agent dependencies.

### Owner Matrix
| Domain / Entity | Actual State Owner | Database/Cache | Sync/Async Communication |
| --- | --- | --- | --- |
| Customer Chat | `app/services/customer/chat_persistence.py` & `orchestrator_service` | `app` DB vs `orchestrator_db` (Split brain) | WebSocket & HTTP Proxy |
| Admin Chat | `app` AND `orchestrator_service` | Split DB logic | WebSocket / SSE |
| System Intents | `orchestrator_service` (Supervisor Node) | Redis (PubSub) | Async LangGraph Execution |
| Missions | `orchestrator_service` (`MissionStateManager`) | `orchestrator_db` + Redis PubSub | HTTP triggers, WS pub/sub stream |

### Legacy vs Modern Matrix
- **Canonical Code**: `microservices/orchestrator_service/src/api/routes.py`, `microservices/api_gateway`.
- **Compatibility Façade**: `microservices/conversation_service` (stub), HTTP compatibility routes in gateway (`/admin/ai-config`, `/system/*`).
- **Dead Code Candidate**: `app/services/boundaries/`, `app/services/chat/orchestrator.py` (once UI is fully migrated to orchestrator WS).
- **Transitional but Critical**: Gateway `proxy.py` and `websockets.py`.

---

# 3) Critical Request Flows

### Chat WebSocket Flow (The Canonical Conflict)
1. **Entry**: Client connects to `ws://api-gateway:8000/api/chat/ws`.
2. **Gateway**: `app.websocket("/api/chat/ws")` (in `microservices/api_gateway/main.py`) accepts.
3. **Route Resolution**: `_resolve_chat_ws_target` evaluates `ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT`. Defaults to Orchestrator (`ws://orchestrator-service:8006/api/chat/ws`).
4. **Proxy**: `websocket_proxy` opens upstream connection, passing headers. Starts two infinite loops with `asyncio.FIRST_COMPLETED`.
5. **Target (Orchestrator)**: `orchestrator_service/src/api/routes.py` `chat_ws_stategraph`.
6. **Execution**: Extracts token, gets objective. Calls `_stream_chat_langgraph`, hitting `app_graph` (the LangGraph engine).
7. **Flaw**: Wait, if the UI still talks to Monolith, what happens to `app/api/routers/customer_chat.py`? The gateway shadows it. Any direct hit to Monolith fails. But `app/` is still compiling its own boundaries and DB writes.

### Agent Orchestration Flow
1. **Entry**: Graph execution starts at `SupervisorNode`.
2. **State Transition**: `ADMIN_PATTERNS` regex checks. Fallback to `dspy.ChainOfThought` (Blocking).
3. **Node Route**: Routes to `query_analyzer`, `admin_agent`, or `tool_executor`.
4. **Tools**: `ToolExecutorNode` loops over `tc["args"]` and uses `ainvoke()`.
5. **Failure Mode**: Tool error yields `{ "final_response": "Error..." }` and moves to `validator`.

---

# 4) Root-Cause Architecture Diagnosis

### Diagnosis 1: The "Split-Brain" Chat Execution
- **Evidence**: We have a full LangGraph engine in `orchestrator_service` (`create_unified_graph`), AND a full `ChatOrchestrator` in `app/services/chat/orchestrator.py` that delegates to `orchestrator_client.chat_with_agent` via HTTP SSE.
- **Why Root Cause**: The system is in a transitional "Strangler Fig" state, but the Strangler is strangling itself. The Orchestrator is being treated as both a *target microservice* (LangGraph node) and a *downstream API* for the Monolith.
- **Blast Radius**: Double DB connections, state inconsistency, unmaintainable testing paths.
- **Refactor**: Commit to Orchestrator-Service completely for ALL Chat execution. Kill `app/services/chat/`. Update Frontend to use pure API Gateway routes.

### Diagnosis 2: Blocking the Event Loop with DSPy
- **Evidence**: `microservices/orchestrator_service/src/services/overmind/graph/main.py` -> `SupervisorNode.__call__`. `result = self.dspy_classifier(query=query)`
- **Why Root Cause**: LangGraph nodes run in an async context. Calling a synchronous AI inference API blocks the Python thread. FastAPI cannot serve other requests or WebSocket heartbeats during this time.
- **Blast Radius**: Massive performance bottleneck. One complex query freezes the entire Orchestrator pod.
- **Refactor**: Wrap DSPy calls in `asyncio.to_thread` or transition fully to Async LLM clients for routing.

### Diagnosis 3: Non-Durable Mission Eventing (Race Condition)
- **Evidence**: `microservices/orchestrator_service/src/api/routes.py` lines 260-280.
- **Why Root Cause**: When a mission connects via WS to stream events, it fetches old events from DB, then subscribes to Redis PubSub. The gap between DB fetch and Redis `subscribe` means events emitted during those milliseconds are irrevocably lost.
- **Blast Radius**: Frontend UI hangs waiting for a `phase_completed` or `mission_completed` event that already fired.
- **Refactor**: Use Redis Streams (XREAD) or a state-sync flag on the DB record.

---

# 5) WebSocket / Streaming / Async Audit

- **Acceptance Location**: Accepted at Gateway `websockets.py` `await client_ws.accept()`. Then re-accepted at Orchestrator `await websocket.accept()`.
- **Auth**: Gateway extracts token and injects it? No, Gateway forwards `headers`. Orchestrator `extract_websocket_auth` extracts the JWT and validates it.
- **Rate Limits/Limits**: Not enforced on the WS upgrade path cleanly.
- **Backpressure**: Standard TCP backpressure. But Gateway `websockets.py` does `await client_ws.receive_text()` -> `await target_ws.send()`. If Target is slow, it will pause reading from Client. This is acceptable.
- **Ping/Pong/Heartbeat**: **MISSING**. `websockets.connect` is called without `ping_interval`. Silently dropped TCP connections will leave ghost connections.

---

# 6) State, Transactions, Consistency

- **Entity Owner**: `Mission` entity owned by Orchestrator DB. `Conversation` entity owned by App DB (legacy) and Orchestrator DB (new).
- **Outbox Pattern**: Not present. Events are published to Redis immediately via `MissionStateManager.log_event`. If the DB transaction fails, the Redis event is already sent (or vice versa). Non-atomic.
- **Transaction Boundaries**: FastAPI `Depends(get_db)` manages session, but `asyncio.gather` and background tasks break `Session` isolation occasionally.

---

# 7) Agents / Orchestration / Reasoning Layer

- **The Real Graph**:
  - `SupervisorNode` -> `QueryAnalyzer` | `AdminAgentNode` | `ToolExecutor`
  - `QueryAnalyzer` -> `Retriever` -> `Reranker` -> `Synthesizer` | `WebFallback`
  - `Synthesizer` -> `ValidatorNode`
- **DSPy vs LlamaIndex**: DSPy is used deterministically for intent classification (`AdminIntentClassifier`). LlamaIndex is likely the Retriever.
- **Validator Gate**: The `ValidatorNode` in `main.py` is literally: `return {}`. The `check_quality` edge unconditionally returns `"pass"`. **It is a demo-grade stub!** There is no real validation occurring in the graph.

---

# 8) Frontend / API Contract / Compatibility Analysis

- The frontend connects to `API_URL: http://api-gateway:8000`.
- The gateway successfully masks the migration using URL rewriting (e.g., `/admin/api/chat/ws` -> `orchestrator-service/admin/api/chat/ws`).
- However, JSON streaming formats mismatch. Monolith expects `{"type": "delta", "payload": {"content": "..."}}`. Orchestrator `_stream_chat_langgraph` sends `{"type": "assistant_delta", "payload": {"content": "..."}}` or raw JSON.

---

# 9) Docs-vs-Code-vs-Compose Drift

| Claim in Docs | Code Reality | Compose Reality | Severity |
| --- | --- | --- | --- |
| Conversation Service manages Parity | `conversation_service/main.py` is a hardcoded stub. | Deployed but bypassed by default | Low |
| Validator verifies outputs before reply | `ValidatorNode` returns `{}` and `check_quality` returns `"pass"`. | Same | High |
| 100% Microservices | `app/kernel.py` and `app/services` still hold ~40% of domain logic | Main monolith still compiles | Medium |

---

# 10) Observability & Operability Audit

- **Traces**: OpenTelemetry is injected (`TraceContextMiddleware`). `SupervisorNode` calls `emit_telemetry()`. Good propagation.
- **Metrics**: Gateway exposes `/gateway/health`.
- **Healthchecks**: `docker-compose.yml` has robust healthchecks utilizing `curl -f`.
- **CI**: Extremely rigid (`scripts/ci_guardrails.py`, Ruff, Pytest required). The architecture is strongly protected by CI gates.

---

# 11) Top 8 Findings Table

| ID | Category | Title | Severity | Confidence | Root Cause | Fix Now |
|---|---|---|---|---|---|---|
| 1 | Architecture | Split-Brain Chat Ownership | P0 | High | Strangler pattern incomplete; Monolith and Microservice fight over WS state. | Force Gateway WS route strictly to Orchestrator; disable Monolith WS. |
| 2 | Async | DSPy Event Loop Blocking | P1 | High | `dspy` is synchronous, freezing the Async Node in `SupervisorNode`. | Wrap DSPy call in `asyncio.to_thread`. |
| 3 | Networking | Zombie WebSockets (No PING) | P1 | High | Gateway `websockets.connect` lacks ping intervals. | Add `ping_interval` and `ping_timeout` to connection kwargs. |
| 4 | State | Mission PubSub Race Condition | P1 | High | Redis PubSub is read after DB fetch, missing intermediate events. | Switch to Redis Streams or implement polling reconciliation. |
| 5 | Integrity | Validator Node is a Stub | P2 | High | `ValidatorNode` is empty, contradicting the "Verify-then-Reply" constitution. | Implement actual critique logic in ValidatorNode. |
| 6 | Robustness | JSON Parsing in Streaming Chunk | P2 | High | Checking `final_content.startswith("{")` for JSON fallback parsing is brittle. | Enforce strictly typed SSE events across all services. |
| 7 | Networking | Gateway request.stream() Retry | P2 | High | Retrying `request.stream()` after it is consumed will crash/fail silently. | Disable retries for streaming bodies or buffer small requests. |
| 8 | Clean Code | Fake "Pacing" Sleeps | P3 | High | Backend mimics human typing speed via `asyncio.sleep`, wasting resources. | Remove artificial sleeps; let frontend handle UI pacing. |

---

# 12) The 3 Most Dangerous Things

1. **أخطر مشكلة معمارية**: **Split-Brain WebSocket Handling**. التوجيه المزدوج للـ WebSockets بين الـ Monolith القديم والـ Orchestrator الجديد يؤدي إلى تلف البيانات وسباق الحالة (Race Conditions) وصعوبة تتبع أصل الرد.
2. **أخطر مشكلة تشغيلية**: **Synchronous DSPy in LangGraph**. تجميد الـ Event Loop بالكامل عند كل استعلام يحتاج إلى تقييم نية (Intent). في الإنتاج (Production) مع 10 مستخدمين متزامنين، سيتوقف الخادم عن الاستجابة لطلبات الـ Ping وسيسقط النظام.
3. **أخطر مشكلة تغيّر/صيانة**: **Fake Validator Node**. المستودع يعتمد بشكل كامل على شعار "Verify-then-Reply"، بينما الواقع في الكود أن عقدة `ValidatorNode` لا تفعل شيئاً سوى التمرير التلقائي (`return "pass"`). هذا ينسف مصداقية المرجعية الدقيقة للـ Agent.

---

# 13) Refactor Roadmap

- **72 Hours (Containment)**:
  - إضافة `asyncio.to_thread` في `SupervisorNode`.
  - إضافة Ping/Pong لمكتبة WebSocket في Gateway.
  - إيقاف `retry` في بوابة الـ Gateway إذا كان الطلب يحتوي على Stream.
- **2 Weeks (Structural Correction)**:
  - معالجة الـ Pub/Sub Race Condition في `MissionStateManager`.
  - كتابة كود التحقق الفعلي داخل `ValidatorNode` ليعكس متطلبات السلامة (Safeguarding).
- **6 Weeks (Kill List & Consolidation)**:
  - التخلص التام من `app/services/boundaries` ومسارات المونوليث المتعلقة بالدردشة.
  - نقل ملكية الـ `Conversation` بشكل نهائي إلى `orchestrator_service` DB.

---

# 14) Proof Appendix

- **أهم الملفات المقروءة**:
  - `microservices/api_gateway/websockets.py` (Missing Ping timeout, unsafe async task handling).
  - `microservices/orchestrator_service/src/services/overmind/graph/main.py` (Synchronous DSPy, empty ValidatorNode).
  - `microservices/orchestrator_service/src/api/routes.py` (Pub/Sub Eventing Race Condition).
  - `app/services/chat/orchestrator.py` (Insecure JSON chunking heuristic).
- **What must be measured in Staging**:
  - Load test WebSocket connections to observe OOM limits due to Zombie connections.
  - Send 5 simultaneous requests to Supervisor Node to verify Event Loop freezing.