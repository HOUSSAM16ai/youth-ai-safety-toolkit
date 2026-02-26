# Route Ownership Registry

> المصدر الوحيد للحقيقة لتوجيه البوابة (Strangler Fig).

| route_id | route_pattern | owner | legacy_flag | sunset_date | target_service |
|---|---|---|---|---|---|
| chat_ws_customer | `/api/chat/ws` | conversation-platform | `ROUTE_CHAT_WS_USE_LEGACY` | 2026-06-30 | conversation-service (candidate in PR#1) |
| chat_ws_admin | `/admin/api/chat/ws` | conversation-platform | `ROUTE_ADMIN_CHAT_WS_USE_LEGACY` | 2026-06-30 | conversation-service (candidate in PR#1) |
| chat_http | `/api/chat/{path}` | conversation-platform | `ROUTE_CHAT_USE_LEGACY` | 2026-06-30 | orchestrator-service |
| admin_ai_config | `/admin/ai-config` | identity-platform | `none` | 2026-06-30 | user-service |
| content | `/v1/content/{path}` | research-platform | `none` | 2026-06-30 | research-agent |
| data_mesh | `/api/v1/data-mesh/{path}` | data-platform | `none` | 2026-06-30 | observability-service |
| system | `/system/{path}` | orchestrator-platform | `none` | 2026-06-30 | orchestrator-service |

## ملاحظات الحوكمة
- أي fallback legacy يجب أن يكون مقيّدًا بعلم route-level + TTL إلزامي.
- أي route جديد يُضاف هنا يجب أن يحدد `owner` و`sunset_date` قبل الدمج.
