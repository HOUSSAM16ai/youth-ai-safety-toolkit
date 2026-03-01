# CHAT_RUNTIME_UNIFICATION_RECOVERY_REPORT

## 1) Executive Summary
تم تأكيد أن مسار الدردشة الحي موحّد فعلاً، لكن فشل التوحيد حدث لأن العميل الفعّال (`OrchestratorClient`) كان يعتمد افتراضيًا على اسم خدمة Docker (`orchestrator-service`) حتى في أوضاع تشغيل لا تملك DNS داخلي لـ Docker service names. النتيجة كانت فشلًا موحّدًا (Admin + Customer + Super Agent) برسالة: `Error connecting to agent: [Errno -2] Name or service not known`.

تم تنفيذ إصلاح حادثة محدود وقابل للإرجاع: **تطبيع هدف orchestrator حسب قابلية حل الاسم وقت التشغيل** مع fallback صريح إلى `http://localhost:8006` عندما يكون `orchestrator-service` غير قابل للحل، مع إبقاء الملكية الحية موحّدة على orchestrator.

---

## 2) Runtime Truth Matrix

| Runtime Mode | Admin Chat Owner | Customer Chat Owner | Super Agent Owner | Backend Target | Resolvable? | Notes |
|---|---|---|---|---|---|---|
| Modern Compose (`docker-compose.yml`) | orchestrator عبر gateway/ws | orchestrator عبر gateway/ws | orchestrator/StateGraph | `http://orchestrator-service:8006` | نعم (داخل شبكة compose) | `api-gateway` يحقن ORCHESTRATOR_SERVICE_URL بهذه القيمة. |
| Legacy/Emergency (`docker-compose.legacy.yml`) | core-kernel (monolith runtime) | core-kernel | مسارات kernel/legacy | لا يوجد orchestrator service ضمن هذا compose | غالبًا لا | نمط legacy لا يفعّل orchestrator service افتراضيًا. |
| DevContainer (`.devcontainer/docker-compose.host.yml` + `supervisor.sh`) | `app.main` على `:8000` | `app.main` على `:8000` | عبر نفس مسار التطبيق | كان يسقط إلى `orchestrator-service` عند غياب env | لا (عادة) | devcontainer يشغل backend منفردًا (ليس modern compose بالكامل). |
| Local/Dev scripts (`scripts/setup_dev.sh`) | `app.main` على `:8000` | `app.main` على `:8000` | عبر نفس العميل | كان يسقط إلى `orchestrator-service` | لا (عادة) | تشغيل محلي مباشر لا يملك DNS اسم خدمة Docker. |

---

## 3) Exact Current Failure Class
- الفئة: **Runtime service-name resolution failure** (DNS/host resolution).
- السطح الظاهر: `assistant_error` بمحتوى: `Error connecting to agent: ...` من `OrchestratorClient.chat_with_agent`.
- النص المعروض للمستخدم يطابق التعامل مع استثناءات طبقة `httpx`/socket في العميل.

---

## 4) Root Cause Proof
1. مسار WS الموحّد (admin/customer) يمر عبر `orchestrator_client.chat_with_agent` من `websocket_authority`.
2. `chat_with_agent` عند الفشل يعيد نص الخطأ المباشر للمستخدم: `Error connecting to agent: {e}`.
3. قبل الإصلاح كان default URL للعميل هو `http://orchestrator-service:8006` عند غياب `ORCHESTRATOR_SERVICE_URL` في إعدادات التطبيق الأساسية.
4. أوضاع dev/devcontainer/local تشغّل `app.main` مباشرة، ولا توفر DNS لحل `orchestrator-service` خارج شبكة compose الحديثة.
5. إذًا يظهر `Name or service not known` بشكل موحّد على جميع الرحلات بعد إزالة مسار النجاة المحلي القديم.

---

## 5) Safe Target Ownership Decision
**المالك الحي المختار: `orchestrator-service` مباشرة.**

السبب:
- هو المالك المكتمل فعليًا لمسار WS/HTTP الحي في gateway حاليًا.
- يدعم StateGraph + mission branch في `orchestrator_service`.
- يقلل المخاطر مقارنة بخيار `conversation-service` (الذي كان تاريخيًا canary/بديلًا تدريجيًا وليس الهدف النهائي النشط).

تم رفض جعل `conversation-service` مالكًا افتراضيًا في الحادثة لأن الهدف هنا استعادة الخدمة فورًا بأقل تغيير على المسار المؤكد.

---

## 6) Recovery Plan (Phased, Minimal, Reversible)
### Phase 0 (Proof)
- جرد أوضاع التشغيل من compose/devcontainer/scripts.
- تتبع مصدر رسالة الخطأ حتى طبقة العميل.

### Phase 1 (Single Owner Validation)
- تثبيت قرار أن المالك الحي هو orchestrator على WS/HTTP (موجود بالفعل في تغييرات سابقة).

### Phase 2 (Incident Fix)
- إضافة Runtime URL resolver في `OrchestratorClient`:
  - إذا العنوان موجه إلى alias Docker (`orchestrator-service`) وكان غير قابل للحل في runtime الحالي، التحويل الآمن إلى `http://localhost:8006`.
  - تسجيل خطأ واضح لتشخيص mismatch بدل فشل صامت.
  - فشل سريع برسالة تشغيلية صريحة موسومة `[RUNTIME_TARGET_UNRESOLVABLE]` إذا كان الهدف غير قابل للحل ولا يوجد fallback صالح.

### Phase 3 (Verification)
- تشغيل smoke tests لمسارات admin/customer/super-agent + routing + runtime resolution.

### Phase 4 (Rollback)
- revert commit الحالي فقط.

---

## 7) Code Changes Performed
### A) `app/infrastructure/clients/orchestrator_client.py`
- أضيفت دوال:
  - `_is_host_resolvable`
  - `_resolve_runtime_orchestrator_url`
- أضيفت ثوابت:
  - `LOCAL_ORCHESTRATOR_URL`
  - `DOCKER_ORCHESTRATOR_HOSTS`
- تم تعديل `__init__` لاختيار `base_url` القابل للوصول في runtime.

**Symptom addressed:** خطأ DNS `[Errno -2] Name or service not known` في جميع الرحلات.

**Risk:** قد يتم fallback إلى localhost في بيئة غير مناسبة إذا تم ضبط DNS بشكل غير متوقع.

**Rollback:** revert هذا الملف إلى الالتقاط القديم للعنوان.

### B) `tests/unit/test_orchestrator_client_runtime_resolution.py`
- أضيفت اختبارات مواصفة لسيناريوهات:
  - host غير docker alias (يبقى كما هو)
  - alias غير قابل للحل (fallback localhost)
  - alias قابل للحل (يبقى docker host)
  - مضيف غير docker وغير قابل للحل (RuntimeError fail-fast)

**Symptom addressed:** ضمان عدم عودة حادثة runtime resolution.

---

## 8) Smoke Test Results
1. Runtime resolution validation
- `pytest -q tests/unit/test_orchestrator_client_runtime_resolution.py` ✅

2. Admin + Customer chat smoke (unified WS authority)
- ضمن: `pytest -q tests/api/test_chat_websocket_unified_authority.py` ✅

3. Super Agent smoke
- ضمن: `pytest -q tests/microservices/test_orchestrator_agent_chat_stategraph_stream.py` ✅

4. WebSocket connect/proxy smoke
- ضمن: `pytest -q tests/microservices/test_api_gateway_ws_routing.py` ✅

5. HTTP control-plane routing smoke
- ضمن: `pytest -q tests/microservices/test_api_gateway_chat_http_rollout.py` ✅

6. Combined incident-focused suite
- `pytest -q tests/unit/test_orchestrator_client_runtime_resolution.py tests/api/test_chat_websocket_unified_authority.py tests/microservices/test_orchestrator_agent_chat_stategraph_stream.py tests/microservices/test_api_gateway_ws_routing.py tests/microservices/test_api_gateway_chat_http_rollout.py` ✅ (`12 passed`)

---

## 9) Cutover Scoreboard
Metric| Value
---|---
admin_chat_owner| orchestrator-service (via unified websocket authority)
customer_chat_owner| orchestrator-service (via unified websocket authority)
super_agent_owner| orchestrator-service (mission_complex branch)
websocket_owner| orchestrator-service
selected_runtime_mode| local/dev + compose-aware resolution
backend_target_host| orchestrator-service (compose) / localhost (fallback)
backend_target_resolvable| true (post-fix runtime-aware)
legacy_dispatch_bridge_active_on_live_path| false
admin_customer_split_brain| false
super_agent_split_brain| false
payload_contract_verified| true
smoke_admin_chat| pass
smoke_customer_chat| pass
smoke_super_agent| pass
rollback_ready| true

---

## 10) Rollback Instructions
1. `git revert <commit_sha_of_this_fix>`
2. أعد تشغيل الخدمة (`app.main`) أو حاوية backend.
3. أعد تشغيل smoke suite نفسها للتحقق من العودة للحالة السابقة.

---

## 11) Evidence Index
- `app/services/chat/websocket_authority.py` (WS الموحد admin/customer عبر orchestrator client).
- `app/infrastructure/clients/orchestrator_client.py` (مصدر رسالة `Error connecting to agent` + إصلاح runtime URL resolution).
- `microservices/orchestrator_service/src/api/routes.py` (StateGraph + mission_complex branch).
- `microservices/api_gateway/main.py` (single owner routing WS/HTTP إلى orchestrator).
- `docker-compose.yml` (modern compose يحقن `ORCHESTRATOR_SERVICE_URL=http://orchestrator-service:8006`).
- `docker-compose.legacy.yml` (legacy/emergency mode بملكية core-kernel).
- `.devcontainer/docker-compose.host.yml` + `.devcontainer/supervisor.sh` + `scripts/setup_dev.sh` (تشغيل محلي/devcontainer مباشر لـ `app.main`).
- `tests/unit/test_orchestrator_client_runtime_resolution.py` (إثبات fallback/resolution behavior).
