"""
خدمة حدود محادثة العملاء القياسيين.

تنسق هذه الخدمة البث والتخزين وبوابة السياسات لضمان أن المحادثات
تبقى ضمن النطاق التعليمي المسموح.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator, Callable

from fastapi import HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_gateway import AIClient
from app.services.auth.ws_auth import extract_websocket_auth
from app.core.config import get_settings
from app.core.domain.chat import CustomerConversation, MessageRole
from app.core.domain.user import User
from app.services.audit import AuditService
from app.services.auth.token_decoder import decode_user_id
from app.services.chat.contracts import ChatDispatchResult, ChatStreamEvent
from app.services.chat.education_policy_gate import EducationPolicyDecision, EducationPolicyGate
from app.services.chat.intent_detector import ChatIntent, IntentDetector
from app.services.chat.tool_router import ToolRouter
from app.services.customer.chat_persistence import CustomerChatPersistence
from app.services.customer.chat_streamer import CustomerChatStreamer

logger = logging.getLogger(__name__)


class CustomerChatBoundaryService:
    """
    واجهة تنسيق محادثات العملاء القياسيين.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.persistence = CustomerChatPersistence(db)
        self.streamer = CustomerChatStreamer(self.persistence)
        self.policy_gate = EducationPolicyGate()
        self.audit = AuditService(db)
        self.intent_detector = IntentDetector()
        self.tool_router = ToolRouter()

    async def validate_ws_auth(self, websocket: WebSocket) -> tuple[User, str]:
        """
        Validate WebSocket authentication and return the user and selected protocol.
        """
        token, selected_protocol = extract_websocket_auth(websocket)
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication")

        try:
            user_id = decode_user_id(token, get_settings().SECRET_KEY)
        except HTTPException as e:
            raise e

        # Ensure we use db from self
        actor = await self.db.get(User, user_id)
        if actor is None or not actor.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        if actor.is_admin:
            raise HTTPException(
                status_code=403, detail="Admin accounts must use the admin chat endpoint."
            )

        return actor, selected_protocol

    async def verify_conversation_access(
        self, user: User, conversation_id: int
    ) -> CustomerConversation:
        """
        التحقق من صلاحية الوصول لمحادثة تعليمية.
        """
        try:
            return await self.persistence.verify_access(user.id, conversation_id)
        except ValueError as error:
            message = str(error)
            if "User not found" in message:
                raise HTTPException(status_code=401, detail="User not found") from error
            raise HTTPException(status_code=404, detail="Conversation not found") from error

    async def get_or_create_conversation(
        self,
        user: User,
        question: str,
        conversation_id: str | int | None = None,
    ) -> CustomerConversation:
        """
        استرجاع محادثة موجودة أو إنشاء واحدة جديدة.
        """
        try:
            normalized_id: str | None = None
            if conversation_id is not None:
                normalized_id = str(int(conversation_id))
            return await self.persistence.get_or_create_conversation(
                user.id, question, normalized_id
            )
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail="Invalid conversation ID") from error

    async def save_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        policy_flags: dict[str, str] | None = None,
    ) -> None:
        """
        حفظ رسالة المحادثة مع أعلام السياسة.
        """
        await self.persistence.save_message(conversation_id, role, content, policy_flags)

    async def get_chat_history(self, conversation_id: int, limit: int = 20) -> list[dict[str, str]]:
        """
        استرجاع سجل المحادثة.
        """
        return await self.persistence.get_chat_history(conversation_id, limit)

    async def stream_chat_response(
        self,
        conversation: CustomerConversation,
        question: str,
        history: list[dict[str, str]],
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        metadata: dict[str, object] | None = None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        تفويض عملية البث إلى Streamer.
        """
        async for chunk in self.streamer.stream_response(
            conversation, question, history, ai_client, session_factory_func, metadata
        ):
            yield chunk

    async def orchestrate_chat_stream(
        self,
        user: User,
        question: str,
        conversation_id: str | int | None,
        ai_client: AIClient,
        session_factory_func: Callable[[], AsyncSession],
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, object] | None = None,
    ) -> ChatDispatchResult:
        """
        تنسيق تدفق المحادثة مع بوابة السياسات والتخزين.
        """
        if user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Admin accounts must use the admin chat endpoint.",
            )
        role_label = "STANDARD_USER"
        intent_result = await self.intent_detector.detect(question)
        effective_intent = intent_result.intent

        # Override intent if mission_type is provided in metadata (e.g. from UI modal)
        # This ensures policy checks respect the user's explicit choice
        if metadata and metadata.get("mission_type") == "mission_complex":
            effective_intent = ChatIntent.MISSION_COMPLEX

        if (
            effective_intent != ChatIntent.CONTENT_RETRIEVAL
            and self._looks_like_content_request(question)
            and effective_intent != ChatIntent.MISSION_COMPLEX
        ):
            # Only switch to content retrieval if not already a mission
            effective_intent = ChatIntent.CONTENT_RETRIEVAL

        conversation = await self.get_or_create_conversation(user, question, conversation_id)

        if self._is_tool_intent(effective_intent):
            tool_decision = self.tool_router.authorize_intent(
                role=role_label,
                intent=effective_intent,
            )
            if not tool_decision.allowed:
                refusal_text = tool_decision.refusal_message or "عذرًا، لا يمكنني تنفيذ هذا الطلب."
                await self._record_tool_blocked(
                    user_id=user.id,
                    conversation_id=conversation.id,
                    intent=effective_intent.value,
                    reason_code=tool_decision.reason_code,
                    ip=ip,
                    user_agent=user_agent,
                )
                await self.save_message(
                    conversation.id,
                    MessageRole.USER,
                    "[BLOCKED REQUEST]",
                    {
                        "classification": "tool_access",
                        "blocked": "true",
                        "intent": effective_intent.value,
                        "reason_code": tool_decision.reason_code,
                    },
                )
                await self.save_message(
                    conversation.id,
                    MessageRole.ASSISTANT,
                    refusal_text,
                    {
                        "classification": "tool_access",
                        "refusal": "true",
                        "reason_code": tool_decision.reason_code,
                    },
                )
                stream = self._refusal_stream(conversation, refusal_text)
                return ChatDispatchResult(status_code=403, stream=stream)

        decision = self.policy_gate.evaluate(question)

        if not decision.allowed:
            await self._record_blocked_attempt(
                user_id=user.id,
                conversation_id=conversation.id,
                decision=decision,
                ip=ip,
                user_agent=user_agent,
            )
            await self.save_message(
                conversation.id,
                MessageRole.USER,
                "[BLOCKED REQUEST]",
                {
                    "classification": decision.category,
                    "blocked": "true",
                    "redaction_hash": decision.redaction_hash,
                    "reason_code": decision.reason_code,
                },
            )
            await self.save_message(
                conversation.id,
                MessageRole.ASSISTANT,
                decision.refusal_message or "",
                {
                    "classification": decision.category,
                    "refusal": "true",
                    "reason_code": decision.reason_code,
                },
            )
            stream = self._refusal_stream(conversation, decision.refusal_message)
            return ChatDispatchResult(status_code=200, stream=stream)

        if effective_intent != ChatIntent.CONTENT_RETRIEVAL and decision.category != "education":
            refusal_text = self._build_strict_education_refusal()
            await self.save_message(
                conversation.id,
                MessageRole.USER,
                question,
                {"classification": "education_strict", "blocked": "true"},
            )
            await self.save_message(
                conversation.id,
                MessageRole.ASSISTANT,
                refusal_text,
                {"classification": "education_strict", "refusal": "true"},
            )
            stream = self._refusal_stream(conversation, refusal_text)
            return ChatDispatchResult(status_code=200, stream=stream)

        await self.save_message(
            conversation.id,
            MessageRole.USER,
            question,
            {"classification": decision.category},
        )
        history = await self.get_chat_history(conversation.id)

        stream = self.stream_chat_response(
            conversation, question, history, ai_client, session_factory_func, metadata
        )
        return ChatDispatchResult(status_code=200, stream=stream)

    async def _record_tool_blocked(
        self,
        *,
        user_id: int,
        conversation_id: int,
        intent: str,
        reason_code: str,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        """
        تسجيل محاولة استخدام أدوات غير مصرح بها.
        """
        await self.audit.record(
            actor_user_id=user_id,
            action="TOOL_ACCESS_BLOCKED",
            target_type="customer_conversation",
            target_id=str(conversation_id),
            metadata={
                "intent": intent,
                "reason_code": reason_code,
            },
            ip=ip,
            user_agent=user_agent,
        )

    async def _record_blocked_attempt(
        self,
        *,
        user_id: int,
        conversation_id: int,
        decision: EducationPolicyDecision,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        """
        تسجيل محاولة محجوبة بدون تخزين محتوى حساس.
        """
        await self.audit.record(
            actor_user_id=user_id,
            action="POLICY_BLOCKED",
            target_type="customer_conversation",
            target_id=str(conversation_id),
            metadata={
                "classification": decision.category,
                "reason_code": decision.reason_code,
                "redaction_hash": decision.redaction_hash,
            },
            ip=ip,
            user_agent=user_agent,
        )

    def _build_strict_education_refusal(self) -> str:
        """إنشاء رسالة توضح أن المسار مخصص للأسئلة التعليمية فقط."""
        lines = [
            "عذرًا، هذا المسار مخصص للأسئلة التعليمية فقط.",
            "يمكنك طرح سؤال حول تمرين أو مفهوم علمي وسأساعدك وفق السياق المتاح.",
            "للاسترجاع الدقيق، استخدم صيغة مثل: التمرين الأول، الموضوع الأول، سنة 2024.",
        ]
        return "\n".join(lines)

    def _looks_like_content_request(self, question: str) -> bool:
        """تعرف سريع على الطلبات التعليمية التي تشير لتمارين مخزنة."""
        # Use word boundaries for English terms to avoid false positives (e.g. 'how' inside 'however')
        # Arabic terms don't use \b comfortably without more complex regex due to morphology,
        # so we keep them as simple substring checks or ensure whitespace context if needed.
        # For this implementation, we mix substring for Arabic/Safe terms and regex for ambiguous English.

        lowered = question.lower()

        # 1. Simple substring checks (Safe/Long terms)
        substring_keywords = (
            "تمرين",
            "تمارين",
            "موضوع",
            "بكالوريا",
            "الاحتمالات",
            "الأعداد المركبة",
            "أفهم",
            "فهم",
            "اشرح",
            "لماذا",
            "كيف",
            "من أين",
            "afham",
            "sharh",
            "ashrah",
            "eshrah",
            "نتيجة",
            "الحل",
            "جواب",
            "جاءت",
        )
        if any(k in lowered for k in substring_keywords):
            return True

        # 2. Regex for short/ambiguous English terms
        # Matches: "bac", "subject", "exercise", "why", "how", etc. as whole words
        pattern = r"\b(bac|subject|exercise|exercises|explain|why|how|result|solution|answer)\b"
        return bool(re.search(pattern, lowered))

    def _is_tool_intent(self, intent: ChatIntent) -> bool:
        """تحديد ما إذا كانت النية مرتبطة باستخدام أدوات حساسة."""
        tool_intents = {
            ChatIntent.FILE_READ,
            ChatIntent.FILE_WRITE,
            ChatIntent.CODE_SEARCH,
            ChatIntent.PROJECT_INDEX,
        }
        return intent in tool_intents

    async def _refusal_stream(
        self,
        conversation: CustomerConversation,
        message: str | None,
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """
        بث رد الرفض بشكل متوافق مع WebSocket.
        """
        init_payload = {"conversation_id": conversation.id, "title": conversation.title}
        yield {"type": "conversation_init", "payload": init_payload}

        refusal_text = message or "عذرًا، لا يمكنني المساعدة في هذا الطلب."
        yield {"type": "delta", "payload": {"content": refusal_text}}
        yield {"type": "complete", "payload": {"status": "refused"}}

    async def get_latest_conversation_details(self, user: User) -> dict[str, object] | None:
        """
        استرجاع تفاصيل آخر محادثة للعميل.
        """
        conversation = await self.persistence.get_latest_conversation(user.id)
        if not conversation:
            return None

        messages = await self.persistence.get_conversation_messages(conversation.id, limit=20)
        return {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:50000] if msg.content else "",
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    "policy_flags": msg.policy_flags,
                }
                for msg in messages
            ],
        }

    async def list_user_conversations(self, user: User) -> list[dict[str, object]]:
        """
        سرد محادثات العميل للواجهة.
        """
        conversations = await self.persistence.list_conversations(user.id)
        results: list[dict[str, object]] = []
        for conv in conversations:
            created_at = conv.created_at.isoformat() if conv.created_at else ""
            results.append(
                {
                    "id": conv.id,
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "created_at": created_at,
                    "updated_at": None,
                }
            )
        return results

    async def get_conversation_details(self, user: User, conversation_id: int) -> dict[str, object]:
        """
        استرجاع تفاصيل محادثة محددة مع التحقق من الملكية.
        """
        conversation = await self.verify_conversation_access(user, conversation_id)
        messages = await self.persistence.get_conversation_messages(conversation.id, limit=20)
        return {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:50000] if msg.content else "",
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    "policy_flags": msg.policy_flags,
                }
                for msg in messages
            ],
        }
