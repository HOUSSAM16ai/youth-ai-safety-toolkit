# PR#3 (Phase 1c) — Conversation Service Target

## الهدف
توفير هدف خدمة Conversation لمسارات chat (HTTP + WS) مع تفعيل تدريجي آمن دون Big Bang.

## ما تم اعتماده
- خدمة جديدة: `microservices/conversation_service/main.py`.
- Gateway rollout knobs:
  - `ROUTE_CHAT_HTTP_CONVERSATION_ROLLOUT_PERCENT`
  - `ROUTE_CHAT_WS_CONVERSATION_ROLLOUT_PERCENT`
- نسب rollout المقترحة: `0 -> 5 -> 25 -> 100`.

## سياسة القرار
- عند `ROUTE_CHAT_USE_LEGACY=true` أو `ROUTE_CHAT_WS_USE_LEGACY=true`: يذهب الطلب إلى legacy وفق TTL.
- عند تعطيل legacy:
  - إن كانت نسبة rollout محققة للحالة: Conversation Service.
  - غير ذلك: Orchestrator كمسار آمن افتراضي.

## التحقق التركيبي (Synthetic Journeys)
1. WS customer:
   - connect `/api/chat/ws`
   - send `{ "question": "..." }`
   - receive `{ "status": "ok", "response": "..." }`
2. HTTP chat:
   - request `/api/chat/messages`
   - verify routing target حسب rollout.

## Scoreboard (PR#3)
| Metric | Value |
|---|---|
| legacy_routes_count | 7 (بدون تغيير حتى Phase 2) |
| legacy_ws_sessions_total (7d) | متاح عبر telemetry بعد النشر |
| legacy_request_total (7d) | بدون تغيير مباشر |
| legacy_traffic_ratio | يبدأ بالانخفاض مع رفع rollout |
| core-kernel_dependency (default profile) | true (Phase 3 لاحقًا) |
| contract_gate | true |
| tracing_gate | true |
| ports_consistency | true (إضافة منفذ 8010 ضمن اتفاق الخدمة) |
