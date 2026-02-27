# PR3 — StateGraph Runtime Backbone Activation

## الهدف
تحويل مسار chat (HTTP + WS) إلى تنفيذ فعلي عبر LangGraph داخل `orchestrator-service`، بحيث لا يبقى StateGraph مسارًا معزولًا.

## التغييرات
- إضافة نقاط orchestrator المباشرة:
  - `GET /api/chat/messages`
  - `POST /api/chat/messages`
  - `WS /api/chat/ws`
  - `WS /admin/api/chat/ws`
- كل رسالة chat تُنفذ عبر `create_langgraph_service()` (StateGraph-first).
- إضافة بوابة `check_stategraph_runtime_backbone.py` للتحقق من:
  - ملكية chat إلى orchestrator.
  - وجود مسارات chat HTTP+WS داخل orchestrator.

## التحقق
1. `python scripts/fitness/check_stategraph_runtime_backbone.py`
2. `pytest -q tests/microservices/test_orchestrator_chat_stategraph.py`
3. `python scripts/fitness/generate_cutover_scoreboard.py`

## rollback
- revert commit الخاص بـ PR3 لإزالة مسارات chat المباشرة من orchestrator.
- يبقى gateway ومسارات ownership كما هي ويمكن تفعيل canary conversation عند الحاجة.

## المراقبة
- مراقبة نجاح WS عبر `route_id`:
  - `chat_ws_customer`
  - `chat_ws_admin`
- مراقبة استجابات chat HTTP (`status`, `run_id`, `graph_mode`).
