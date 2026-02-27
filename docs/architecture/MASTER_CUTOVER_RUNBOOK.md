# Master Cutover Runbook (Phase 1)

## الهدف
توفير مسار قطع تدريجي وآمن نحو تشغيل 100% microservices مع آليات rollback فورية وقيود زمنية للطوارئ.

## 1) Cutover حسب عائلة المسارات

### A) Chat HTTP (`/api/chat/*`)
1. ارفع `ROUTE_CHAT_HTTP_CONVERSATION_ROLLOUT_PERCENT` تدريجيًا: `0 -> 5 -> 25 -> 50 -> 100`.
2. بعد كل خطوة:
   - نفّذ اختبار عقود البوابة.
   - راقب معدل الأخطاء وزمن الاستجابة.
3. في أي تدهور يتجاوز العتبة، ارجع فورًا إلى النسبة السابقة.

### B) Chat WebSocket (`/api/chat/ws`, `/admin/api/chat/ws`)
1. ارفع `ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT` بنفس النمط التدريجي.
2. تحقق من handshake + message delivery + close codes.
3. عند التدهور: rollback إلى النسبة السابقة مباشرة.

### C) Missions وSystem وData Mesh
1. أبقِ التوجيه إلى الخدمات المالكة في سجل المسارات.
2. امنع أي fallback legacy ضمن default profile.
3. تحقق من smoke tests بعد كل نشر.

## 2) Rollback Rules (Per-route)
- rollback يجب أن يكون route-level عبر flags فقط.
- لا rollback شامل لكل النظام إلا عند حادثة platform-wide.
- rollback window:
  - Detect: 5 دقائق
  - Decide: 10 دقائق
  - Apply: فوري

## 3) Emergency Legacy Enablement (Break-glass)
1. أنشئ ملف `config/breakglass_legacy.env` من المثال.
2. اضبط:
   - `LEGACY_BREAKGLASS_ENABLED=true`
   - `LEGACY_APPROVAL_TICKET=<CHG-ID>`
   - `LEGACY_EXPIRES_AT=<ISO-8601 UTC>`
3. تحقق قبل التشغيل:
   - `python scripts/fitness/check_breakglass_expiry_enforcement.py`
4. شغّل الطوارئ:
   - `docker compose --env-file config/breakglass_legacy.env -f docker-compose.legacy.yml --profile emergency up -d`
5. تحقق من الانتهاء الآلي:
   - عند تجاوز `LEGACY_EXPIRES_AT` يجب أن يفشل فحص break-glass في CI/تشغيل العمليات.

## 4) TTL Policy
- الحد الأقصى لمدة التفعيل الطارئ: 24 ساعة.
- أي تفعيل بلا ticket أو بتاريخ منتهي/متجاوز للحد يجب أن يُرفض.
- التجديد يتطلب CHG جديدًا وتاريخ انتهاء جديدًا.

## 5) Post-incident Cleanup
1. عطّل break-glass:
   - `LEGACY_BREAKGLASS_ENABLED=false`
2. أوقف legacy emergency profile.
3. أعد توليد scoreboard وتوثيق الحادثة.
