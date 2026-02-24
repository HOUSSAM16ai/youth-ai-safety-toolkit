"""
بث محادثات المسؤول (Admin Chat Streamer).

هذه الخدمة مسؤولة عن إدارة تدفق البيانات الحية عبر WebSocket بين النواة المركزية
وواجهة المستخدم الخاصة بالمسؤول.

المبادئ المعمارية:
- **Async Iteration**: استخدام المولدات غير المتزامنة لضمان استجابة غير محجوبة.
- **Fail Fast**: معالجة الأخطاء وإرسال أحداث خطأ واضحة للواجهة الأمامية.
- **Strict Typing**: الامتثال لمعايير Python 3.12+.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import AIClient
from app.core.domain.chat import AdminConversation, MessageRole
from app.infrastructure.clients.orchestrator_client import orchestrator_client
from app.services.admin.chat_persistence import AdminChatPersistence
from app.services.chat.contracts import ChatStreamEvent

logger = logging.getLogger(__name__)

# مجموعة عالمية للحفاظ على مراجع المهام الخلفية ومنع جمع القمامة (Garbage Collection)
_background_tasks: set[asyncio.Task[object]] = set()


class AdminChatStreamer:
    """
    بث محادثات المسؤول (Admin Chat Streamer).
    """

    def __init__(self, persistence: AdminChatPersistence) -> None:
        """
        تهيئة باث المحادثة.

        Args:
            persistence: خدمة التخزين الدائم للمحادثات.
        """
        self.persistence = persistence

    async def stream_response(
        self,
        user_id: int,
        conversation: AdminConversation,
        question: str,
        history: list[dict[str, object]],
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        metadata: dict[str, object] | None = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        تنفيذ عملية البث الحي للاستجابة عبر OrchestratorClient.

        Yields:
            ChatStreamEvent: أحداث WebSocket منظمة على شكل قاموس.
        """
        # 1. إرسال حدث التهيئة
        # 1. تحديث التاريخ (لضمان تناسق الحالة في الواجهة)
        self._update_history_with_question(history, question)

        yield self._create_init_event(conversation)

        # 2. تنفيذ البث مع الحفظ
        try:
            full_response: list[str] = []

            # Prepare clean history (remove duplicate current question if exists)
            clean_history = [
                {k: str(v) for k, v in m.items()}
                for m in history
                if not (m.get("role") == "user" and m.get("content") == question)
            ]

            async for event in orchestrator_client.chat_with_agent(
                question=question,
                user_id=user_id,
                conversation_id=conversation.id,
                history_messages=clean_history,
                context=metadata,
            ):
                if isinstance(event, dict):
                    # Extract content for persistence
                    evt_type = str(event.get("type", ""))
                    if evt_type in ("assistant_delta", "delta"):
                        content = str(event.get("payload", {}).get("content", ""))
                        if content:
                            full_response.append(content)
                            if self._exceeds_safety_limit(full_response):
                                yield self._create_size_limit_error()
                                break

                    # Compatibility: Map 'assistant_delta' to 'delta' for legacy frontend support
                    if evt_type == "assistant_delta":
                        event["type"] = "delta"

                    yield event
                else:
                    # String fallback
                    content = str(event)
                    full_response.append(content)
                    if self._exceeds_safety_limit(full_response):
                        yield self._create_size_limit_error()
                        break
                    yield self._create_chunk_event(content)

            # 3. حفظ وإنهاء
            await self._persist_response(conversation.id, full_response, session_factory_func)
            yield {"type": "complete", "payload": {"status": "done"}}

        except Exception as e:
            logger.error(f"🔥 Streaming error: {e}", exc_info=True)
            yield self._create_error_event(str(e))

    def _update_history_with_question(
        self, history: list[dict[str, object]], question: str
    ) -> None:
        """
        تحديث التاريخ بالسؤال الجديد.
        """
        if not history or history[-1].get("content") != question:
            history.append({"role": "user", "content": question})

    def _create_init_event(self, conversation: AdminConversation) -> ChatStreamEvent:
        """
        إنشاء حدث التهيئة.
        """
        init_payload = {
            "conversation_id": conversation.id,
            "title": conversation.title,
        }
        return {"type": "conversation_init", "payload": init_payload}

    def _exceeds_safety_limit(self, response_parts: list[str]) -> bool:
        """
        التحقق من تجاوز حد الأمان (100 ألف حرف).
        """
        current_size = sum(len(x) for x in response_parts)
        return current_size > 100000

    def _create_chunk_event(self, content: str) -> ChatStreamEvent:
        """
        إنشاء حدث جزء محتوى (OpenAI style).
        """
        return {"type": "delta", "payload": {"content": content}}

    def _create_size_limit_error(self) -> ChatStreamEvent:
        """
        إنشاء حدث خطأ تجاوز الحجم.
        """
        return {
            "type": "error",
            "payload": {"details": "Response exceeded safety limit (100k chars). Aborting stream."},
        }

    def _create_error_event(self, error_details: str) -> ChatStreamEvent:
        """
        إنشاء حدث خطأ عام.
        """
        return {"type": "error", "payload": {"details": error_details}}

    async def _persist_response(
        self,
        conversation_id: int,
        response_parts: list[str],
        session_factory_func: Callable[[], AsyncSession],
    ) -> None:
        """
        حفظ الاستجابة في قاعدة البيانات.
        """
        assistant_content = "".join(response_parts)
        if not assistant_content and not response_parts:
            # Just to ensure we don't save empty string if it was tool calls only
            # But persist history if needed.
            return

        try:
            async with session_factory_func() as session:
                p = AdminChatPersistence(session)
                await p.save_message(conversation_id, MessageRole.ASSISTANT, assistant_content)
            logger.info(f"✅ Conversation {conversation_id} saved successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to save assistant message: {e}")
