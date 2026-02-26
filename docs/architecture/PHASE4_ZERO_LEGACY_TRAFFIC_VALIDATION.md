# Phase 4 — Zero Legacy Traffic Validation (30 Days)

## الهدف
تثبيت شرط الإنهاء النهائي: عدم وجود أي حركة legacy (`HTTP` و`WS`) لمدة لا تقل عن 30 يومًا.

## الدليل التشغيلي المطلوب
- ملف دليل القياس: `docs/architecture/LEGACY_TRAFFIC_30D_STATUS.json`
- حقول إلزامية:
  - `window_days >= 30`
  - `legacy_request_total_30d = 0`
  - `legacy_ws_sessions_total_30d = 0`
  - `legacy_traffic_ratio_30d = 0.0`

## Enforcement
- تم إضافة fitness function: `scripts/fitness/check_legacy_traffic_zero_window.py`
- تم ربطها في CI guardrails كشرط دمج.

## Scoreboard (Phase 4)
| Metric | Value |
|---|---|
| legacy_routes_count | 0 |
| legacy_ws_sessions_total (30d) | 0 |
| legacy_request_total (30d) | 0 |
| legacy_traffic_ratio | 0.0 |
| core-kernel_dependency (default profile) | false |
| contract_gate | true |
| tracing_gate | true |
| ports_consistency | true |
