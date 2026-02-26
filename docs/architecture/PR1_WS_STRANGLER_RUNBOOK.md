# PR#1 Runbook — WS Legacy Hard-Wire Containment (Strangler Fig)

## الهدف
احتواء مسارات WebSocket الحساسة (`/api/chat/ws`, `/admin/api/chat/ws`) داخل **Flag Guard + TTL** بدون كسر العملاء الحاليين.

## مفاتيح التشغيل
- `ROUTE_CHAT_WS_USE_LEGACY=true|false`
- `ROUTE_ADMIN_CHAT_WS_USE_LEGACY=true|false`
- `ROUTE_CHAT_WS_LEGACY_TTL=ISO-8601`
- `ROUTE_ADMIN_CHAT_WS_LEGACY_TTL=ISO-8601`
- `CONVERSATION_WS_URL=ws://...` (مرشح التحويل)

> السلوك الافتراضي في PR#1 يبقى محافظًا على الإنتاج: المساران يعملان عبر legacy عند تفعيل العلم.

## قواعد السلامة
1. عند `*_USE_LEGACY=true` يتم **فرض TTL إلزامي**، وأي TTL منتهي يوقف fallback فورًا (Fail Fast).
2. عند `*_USE_LEGACY=false` يتم التوجيه إلى `CONVERSATION_WS_URL` مع نفس المسار (`api/chat/ws` أو `admin/api/chat/ws`).
3. العداد `legacy_ws_sessions_total` يتم تسجيله مع الوسوم:
   - `route_id`
   - `legacy_flag`

## خطة Cutover تدريجية
- 0%: `*_USE_LEGACY=true` (Baseline)
- 5%: تفعيل `false` على canary route/environment مع مراقبة الأخطاء.
- 25%: توسيع تدريجي بعد ثبات القياسات.
- 100%: تحويل كامل بعد اجتياز SLO.

## Rollback فوري (Per-Route)
- لإرجاع مسار واحد فقط:
  - مثال عميل: `ROUTE_CHAT_WS_USE_LEGACY=true`
  - مثال إداري: `ROUTE_ADMIN_CHAT_WS_USE_LEGACY=true`
- يشترط تحديث TTL صالح قبل التفعيل.

## التحقق التشغيلي
- راقب السجلات التالية:
  - `chat_ws_candidate route_id=... legacy=false target=...`
  - `legacy_acl_ws route_id=... legacy=true`
  - `legacy_ws_sessions_total=... route_id=... legacy_flag=...`

## Scoreboard (PR#1)
| Metric | Value |
|---|---|
| legacy_routes_count | 7 (بدون تغيير في PR#1) |
| legacy_ws_sessions_total (7d) | متاح عبر السجلات/المجمّع بعد النشر |
| legacy_request_total (7d) | بدون تغيير في PR#1 |
| legacy_traffic_ratio | بدون تغيير في PR#1 |
| core-kernel_dependency (default profile) | true (Phase 3) |
| contract_gate | false (PR#2) |
| tracing_gate | true (بدون تغيير) |
| ports_consistency | بدون تغيير |
