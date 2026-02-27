# Route Ownership Registry

> المصدر الوحيد للحقيقة لتوجيه البوابة (Strangler Fig).
> **الملف المعتمد آليًا:** `config/route_ownership_registry.json`.

| route_id | route_pattern | owner | legacy_flag | target_service |
|---|---|---|---|---|
| chat_ws_customer | `/api/chat/ws` | conversation-platform | `false` | conversation-service |
| chat_ws_admin | `/admin/api/chat/ws` | conversation-platform | `false` | conversation-service |
| chat_http | `/api/chat/{path}` | conversation-platform | `false` | orchestrator-service |
| admin_ai_config | `/admin/ai-config` | identity-platform | `false` | user-service |
| content | `/v1/content/{path}` | research-platform | `false` | research-agent |
| data_mesh | `/api/v1/data-mesh/{path}` | data-platform | `false` | observability-service |
| system | `/system/{path}` | orchestrator-platform | `false` | orchestrator-service |

## ملاحظات الحوكمة
- أي fallback legacy يجب أن يكون مقيّدًا بعلم route-level + TTL إلزامي.
- أي route جديد يجب إضافته إلى `config/route_ownership_registry.json` أولًا، ثم تحديث هذا الملخّص الوثائقي.
