# PR#5 (Phase 3) — Retire core-kernel from Default Runtime

## الهدف
إزالة `core-kernel` و`postgres-core` من `docker-compose.yml` (default/prod) والإبقاء عليهما فقط في `docker-compose.legacy.yml` كخيار طوارئ مقيّد.

## ما تم تنفيذه
- `docker-compose.yml`:
  - لا يحتوي `core-kernel`.
  - لا يحتوي `postgres-core`.
- `docker-compose.legacy.yml`:
  - يحتوي `core-kernel` و`postgres-core`.
  - كلاهما ضمن profiles: `legacy`, `emergency`.
  - يفرض placeholders تشغيلية: `LEGACY_APPROVAL_TICKET`, `LEGACY_EXPIRES_AT`.

## سياسات الحوكمة
- ملف التشغيل الافتراضي ممنوع أن يحتوي أي مؤشر على `core-kernel`.
- تشغيل legacy emergency يجب أن يكون time-boxed ≤ 24h وبموافقة موثقة.

## Scoreboard (PR#5)
| Metric | Value |
|---|---|
| legacy_routes_count | 0 |
| legacy_ws_sessions_total (7d) | يعتمد على تمكين chat rollback flags |
| legacy_request_total (7d) | 0 لعائلات phase2 |
| legacy_traffic_ratio | يجب أن يصل للصفر خلال نافذة المراقبة |
| core-kernel_dependency (default profile) | false |
| contract_gate | true |
| tracing_gate | true |
| ports_consistency | true (core port في legacy فقط) |
