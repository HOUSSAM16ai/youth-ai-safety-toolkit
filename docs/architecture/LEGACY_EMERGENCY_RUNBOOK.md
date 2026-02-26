# Legacy Emergency Re-Enable Runbook (Time-Boxed)

إعادة تمكين `core-kernel` بشكل طارئ ومؤقت فقط عند فشل حرج في الخدمات البديلة.

## مبادئ ملزمة
- التشغيل الافتراضي يجب أن يكون بدون `core-kernel` وبدون `postgres-core`.
- أي إعادة تمكين Legacy لها نافذة زمنية قصوى: **24 ساعة**.
- **Approval required**: يجب وجود تذكرة موافقة تشغيلية (`LEGACY_APPROVAL_TICKET`).
- **Auto-expiry policy**: يجب ضبط `LEGACY_EXPIRES_AT` بصيغة ISO-8601 قبل التشغيل.

## خطوات التفعيل الطارئ
1. شغّل ملف Legacy فقط:
   ```bash
   docker compose -f docker-compose.legacy.yml --profile emergency up -d
   ```
2. اضبط متغيرات الطوارئ (Placeholders فقط):
   ```bash
   export LEGACY_APPROVAL_TICKET=CHG-XXXXX
   export LEGACY_EXPIRES_AT=2026-02-27T12:00:00Z
   export CORE_KERNEL_URL=http://core-kernel:8000
   ```
3. فعّل flags المطلوبة لحالات chat فقط عند الضرورة:
   - `ROUTE_CHAT_USE_LEGACY=true`
   - `ROUTE_CHAT_WS_USE_LEGACY=true`
   - `ROUTE_ADMIN_CHAT_WS_USE_LEGACY=true`
4. راقب أحجام الطلبات legacy ومعرّفات `route_id`.

## الإغلاق الإجباري
1. بعد انقضاء الوقت أو زوال السبب:
   - أعد flags إلى الوضع الحديث.
2. احذف متغيرات الطوارئ من بيئة التشغيل.
3. أوقف stack الطارئ:
   ```bash
   docker compose -f docker-compose.legacy.yml down
   ```
