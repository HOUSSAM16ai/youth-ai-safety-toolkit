# PR2 — Chat Control-Plane Cutover Runbook

## الهدف
توحيد مسارات chat HTTP + WS مع نفس سلطة الـ Super Agent (`orchestrator-service`) داخل الـ default runtime.

## نطاق التغيير
- تحديث سجل الملكية `config/route_ownership_registry.json` لمسارات:
  - `/api/chat/{path:path}`
  - `/api/chat/ws`
  - `/admin/api/chat/ws`
- تثبيت `owner` و `target_service` إلى `orchestrator-service`.
- إضافة بوابة لياقة `check_single_brain_control_plane.py` لمنع العودة إلى split-brain.

## خطوات القطع
1. تعديل سجل الملكية وسجل المسارات التوافقي.
2. تحديث عقود المستهلك بحيث يكون WS provider الافتراضي هو `orchestrator-service`.
3. تشغيل:
   - `python scripts/fitness/check_single_brain_control_plane.py`
   - `python scripts/fitness/generate_cutover_scoreboard.py`
4. التأكد أن المؤشرين:
   - `single_brain_architecture=true`
   - `normal_chat_owner == super_agent_owner`

## التحقق التشغيلي
- رحلة HTTP chat عبر `/api/chat/*`.
- رحلة WS chat عبر `/api/chat/ws` و`/admin/api/chat/ws`.
- رحلة mission عبر `/api/v1/missions`.

## Rollback (قابل للإرجاع)
- إرجاع commit الخاص بـ PR2 مباشرة.
- (اختياري مؤقت) تفعيل canary conversation عبر متغيرات rollout فقط خارج default baseline.

## Emergency Legacy Enable
- غير مطلوب لهذا PR لأن التغيير لا يعيد monolith، فقط يوحّد المالك داخل microservices.
- في حال حادث طارئ: revert PR2 ثم تشغيل runbook العام `docs/architecture/LEGACY_EMERGENCY_RUNBOOK.md`.

## Expiry Enforcement
- أي تفعيل استثنائي must be time-boxed ويخضع لفحص:
  - `python scripts/fitness/check_breakglass_expiry_enforcement.py`
