# Architecture Recovery PR Roadmap

## PR#1 — Forensic Baseline + Control Gates Hardening
- **Purpose:** تثبيت حقيقة معمارية قابلة للقياس قبل أي cutover سلوكي.
- **Files/Areas:** `scripts/fitness/generate_cutover_scoreboard.py`, `scoreboard.json`, `docs/diagnostics/*`, اختبارات unit للوحة القطع.
- **Tests:** اختبار توليد scoreboard ومفاتيحه الإلزامية + تشغيل fitness script.
- **Rollback:** revert مباشر لملفات القياس دون تأثير runtime.
- **Risk:** منخفض.
- **Success metric:** وجود scoreboard موحد يحوي مؤشرات single-brain/stategraph ownership.

## PR#2 — Chat Control-Plane Convergence (HTTP + WS)
- **Purpose:** توجيه chat HTTP/WS عبر نفس سلطة orchestrator مع adapter edge فقط.
- **Files/Areas:** route ownership registry + gateway provider mapping + conversation edge adapters.
- **Tests:** chat HTTP journey, chat WS journey, gateway ownership tests.
- **Rollback:** feature flag للرجوع إلى مسار chat السابق.
- **Risk:** متوسط.
- **Success metric:** `normal_chat_owner == super_agent_owner`.

## PR#3 — StateGraph Runtime Backbone Activation
- **Purpose:** تحويل stategraph إلى مسار التشغيل الحقيقي للدردشة والمهام.
- **Files/Areas:** orchestrator execution pipeline, mission/chat state contracts, event streaming.
- **Tests:** graph transitions, progress events, dispatch integration.
- **Rollback:** provider switch إلى executor السابق داخل orchestrator فقط.
- **Risk:** متوسط/مرتفع.
- **Success metric:** `stategraph_is_runtime_backbone=true` مع نجاح J1..J5.

## PR#4 — Phantom Limb Exorcism
- **Purpose:** إلغاء أي ازدواجية active بين overmind في `app/` ونسخة orchestrator.
- **Files/Areas:** callers rewiring + deactivation/archive for losing copy.
- **Tests:** import-boundary, no app contamination, orchestration regression tests.
- **Rollback:** إعادة التفعيل عبر branch/tag قصير العمر.
- **Risk:** متوسط.
- **Success metric:** `active_overmind_duplication_metric=0` و `app_import_count_in_microservices=0`.

## PR#5 — Hard-Zero Monolith Retirement (Default Runtime)
- **Purpose:** إزالة monolith نهائيًا من default profile مع break-glass مؤقت منتهي الصلاحية.
- **Files/Areas:** compose profiles, gateway defaults, runbooks/ADR/docs.
- **Tests:** default runtime smoke + route ownership completeness + legacy off assertions.
- **Rollback:** break-glass policy time-boxed مع expiry enforcement.
- **Risk:** متوسط.
- **Success metric:** `monolith_required_for_default_runtime=false` واستمرارية J1..J7.
