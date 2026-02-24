from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable

from fastapi import HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import AIClient
from app.services.auth.ws_auth import extract_websocket_auth
from app.core.config import get_settings
from app.core.domain.chat import AdminConversation, MessageRole
from app.core.domain.user import User
from app.services.admin.chat_persistence import AdminChatPersistence
from app.services.admin.chat_streamer import AdminChatStreamer
from app.services.auth.token_decoder import decode_user_id, extract_bearer_token
from app.services.chat.contracts import ChatDispatchResult, ChatStreamEvent

logger = logging.getLogger(__name__)


class AdminChatBoundaryService:
    """
    خدمة محادثة المسؤول (Admin Chat Service).
    ---------------------------------------------------------
    تنسق جميع عمليات المحادثة الخاصة بالمسؤول.
    تطبق مبدأ فصل المسؤوليات (Separation of Concerns) عبر تفويض المهام
    إلى مكونات متخصصة (Persistence, Streamer).

    المسؤوليات:
    1. **التنسيق (Orchestration)**: إدارة تدفق العملية من الطلب إلى الرد.
    2. **الأمان (Security)**: التحقق من الهوية والصلاحيات.
    3. **معالجة البيانات (Data Processing)**: تخزين واسترجاع المحادثات والرسائل.

    ملاحظة: تم تبسيط هذه الخدمة بإزالة طبقة boundaries غير الضرورية.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        تهيئة الخدمة وحقن التبعيات.

        Args:
            db: جلسة قاعدة البيانات غير المتزامنة.
        """
        self.db = db
        self.settings = get_settings()

        # التفويض للمكونات المتخصصة (Delegation)
        self.persistence = AdminChatPersistence(db)
        self.streamer = AdminChatStreamer(self.persistence)

    def validate_auth_header(self, auth_header: str | None) -> int:
        """
        التحقق من ترويسة المصادقة واستخراج معرف المستخدم.
        Validate authentication header and extract user ID.

        Args:
            auth_header: قيمة ترويسة Authorization | Authorization header value

        Returns:
            int: معرف المستخدم | User ID

        Raises:
            HTTPException: في حال فشل المصادقة (401) | On authentication failure (401)
        """
        # Validate header existence and format
        token = extract_bearer_token(auth_header)
        return decode_user_id(token, self.settings.SECRET_KEY)

    async def validate_ws_auth(self, websocket: WebSocket) -> tuple[User, str]:
        """
        Validate WebSocket authentication and return the user and selected protocol.
        Ensures strict admin access control.
        """
        token, selected_protocol = extract_websocket_auth(websocket)
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication")

        try:
            user_id = decode_user_id(token, self.settings.SECRET_KEY)
        except HTTPException as e:
            # Re-raise authentication errors
            raise e

        user = await self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")

        return user, selected_protocol

    async def verify_conversation_access(
        self, user: User, conversation_id: int
    ) -> AdminConversation:
        """
        التحقق من صلاحية وصول المستخدم للمحادثة.
        """
        try:
            return await self.persistence.verify_access(user.id, conversation_id)
        except ValueError as e:
            msg = str(e)
            if "User not found" in msg:
                raise HTTPException(status_code=401, detail="User not found") from e
            if "Conversation not found" in msg:
                raise HTTPException(status_code=404, detail="Conversation not found") from e
            raise HTTPException(status_code=404, detail="Conversation not found") from e

    async def get_or_create_conversation(
        self, user: User, question: str, conversation_id: str | int | None = None
    ) -> AdminConversation:
        """
        استرجاع محادثة موجودة أو إنشاء واحدة جديدة.
        """
        try:
            normalized_id: str | None = None
            if conversation_id is not None:
                try:
                    normalized_id = str(int(conversation_id))
                except (TypeError, ValueError) as conversion_error:
                    raise HTTPException(
                        status_code=400, detail="Invalid conversation ID format"
                    ) from conversion_error

            return await self.persistence.get_or_create_conversation(
                user.id, question, normalized_id
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail="Invalid conversation ID") from e

    async def save_message(
        self, conversation_id: int, role: MessageRole, content: str
    ) -> dict[str, str | int | bool]:
        """حفظ رسالة في قاعدة البيانات."""
        return await self.persistence.save_message(conversation_id, role, content)

    async def get_chat_history(
        self, conversation_id: int, limit: int = 20
    ) -> list[dict[str, object]]:
        """استرجاع سجل المحادثة."""
        return await self.persistence.get_chat_history(conversation_id, limit)

    async def stream_chat_response(
        self,
        user: User,
        conversation: AdminConversation,
        question: str,
        history: list[dict[str, object]],
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        metadata: dict[str, object] | None = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        تفويض عملية البث إلى Streamer.
        """
        async for chunk in self.streamer.stream_response(
            user.id, conversation, question, history, ai_client, session_factory_func, metadata
        ):
            yield chunk

    async def stream_chat_response_safe(
        self,
        user: User,
        conversation: AdminConversation,
        question: str,
        history: list[dict[str, object]],
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        metadata: dict[str, object] | None = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        تغليف عملية البث بشبكة أمان (Safety Net).
        تضمن التقاط الاستثناءات وإرجاعها كأحداث JSON بدلاً من قطع الاتصال.
        """
        try:
            async for chunk in self.stream_chat_response(
                user, conversation, question, history, ai_client, session_factory_func, metadata
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Stream interrupted: {e}", exc_info=True)
            yield {
                "type": "error",
                "payload": {"details": f"Service Error: {e}"},
            }

    async def orchestrate_chat_stream(
        self,
        user: User,
        question: str,
        conversation_id: str | int | None,
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        metadata: dict[str, object] | None = None,
    ) -> ChatDispatchResult:
        """
        تنسيق تدفق المحادثة الكامل:
        1. الحصول على المحادثة أو إنشاء واحدة جديدة.
        2. حفظ رسالة المستخدم.
        3. تجهيز السياق (سجل المحادثة).
        4. بث الرد مع معالجة الأخطاء.
        """
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin access required.")

        # Ensure metadata is passed and respected (consistent with customer boundary)
        # Admin usually has full access, but we might want to log the explicit intent
        if metadata and metadata.get("mission_type") == "mission_complex":
            logger.info("Admin initiated complex mission explicitly.")

        # 1. Get or Create Conversation
        conversation = await self.get_or_create_conversation(user, question, conversation_id)

        # 2. Save User Message
        await self.save_message(conversation.id, MessageRole.USER, question)

        # 3. Prepare Context
        history = await self.get_chat_history(conversation.id)

        # 4. Stream Response
        stream = self.stream_chat_response_safe(
            user, conversation, question, history, ai_client, session_factory_func, metadata
        )
        return ChatDispatchResult(status_code=200, stream=stream)

    # --- طرق استرجاع البيانات (Data Retrieval Methods) ---

    async def get_latest_conversation_details(self, user: User) -> dict[str, object] | None:
        """
        استرجاع تفاصيل آخر محادثة للوحة التحكم.
        يفرض حداً أقصى صارماً للرسائل (20) لمنع انهيار المتصفح وتجميد التطبيق.
        """
        conversation = await self.persistence.get_latest_conversation(user.id)
        if not conversation:
            return None

        # استخدام حد أقصى صارم (Strict Limit) لمنع التجميد (Freezing)
        messages = await self.persistence.get_conversation_messages(conversation.id, limit=20)
        return {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:50000] if msg.content else "",
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                }
                for msg in messages
            ],
        }

    async def list_user_conversations(self, user: User) -> list[dict[str, object]]:
        """
        سرد المحادثات للشريط الجانبي (Sidebar History).

        Returns data compatible with ConversationSummaryResponse schema.
        """
        conversations = await self.persistence.list_conversations(user.id)
        results = []
        for conv in conversations:
            c_at = conv.created_at.isoformat() if conv.created_at else ""
            u_at = c_at
            if hasattr(conv, "updated_at") and conv.updated_at:
                u_at = conv.updated_at.isoformat()
            results.append(
                {
                    "id": conv.id,
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "created_at": c_at,
                    "updated_at": u_at,
                }
            )
        return results

    async def get_conversation_details(self, user: User, conversation_id: int) -> dict[str, object]:
        """
        استرجاع التفاصيل الكاملة لمحادثة محددة.
        يفرض حداً أقصى صارماً للرسائل (20) لمنع انهيار المتصفح وتجميد التطبيق.
        """
        conversation = await self.verify_conversation_access(user, conversation_id)
        # خفض الحد من 1000 إلى 25 ثم إلى 20 لحل مشكلة التشنج (App Freeze) - تم التخفيض مرة أخرى
        messages = await self.persistence.get_conversation_messages(conversation.id, limit=20)
        return {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:50000] if msg.content else "",
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                }
                for msg in messages
            ],
        }
