# PR#4 (Phase 2) — Legacy Families Drain to Zero

## الهدف
استنزاف عائلات legacy المتبقية (`/admin/ai-config`, `/v1/content/*`, `/api/v1/data-mesh/*`, `/system/*`) إلى خدماتها المستهدفة بشكل نهائي في مسار runtime الافتراضي.

## ما تم تغييره
- إزالة fallback branches نحو legacy لهذه العائلات داخل API Gateway.
- تحويل `legacy_routes_count` إلى baseline صفري.
- ترقية فحص fitness من monotonic إلى hard-zero.

## سياسة rollback
- rollback يتم عبر إعادة نشر إصدار سابق (release rollback) وليس عبر fallback flags لهذه العائلات.
- مسارات chat فقط تظل تحت rollback flags في هذه المرحلة.

## Scoreboard (PR#4)
| Metric | Value |
|---|---|
| legacy_routes_count | 0 |
| legacy_ws_sessions_total (7d) | يعتمد على تشغيل مسارات chat legacy flags |
| legacy_request_total (7d) | ينخفض لعائلات phase2 إلى 0 |
| legacy_traffic_ratio | يقترب من الصفر (عدا chat controlled cutover) |
| core-kernel_dependency (default profile) | true (Phase 3) |
| contract_gate | true |
| tracing_gate | true |
| ports_consistency | true |
