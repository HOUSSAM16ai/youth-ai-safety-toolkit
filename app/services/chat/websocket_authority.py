"""سلطة WebSocket موحّدة لمسارات الدردشة الحية.

يوفّر هذا الملف نقطة تحكم واحدة لمعالجة جلسات الدردشة عبر WebSocket
لكلٍ من مسار الأدمن ومسار العملاء، مع الحفاظ على تحقق الهوية وحدود
الصلاحيات وتدفق الأحداث المتوافق مع واجهات المستخدم الحالية.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.di import get_logger
from app.core.domain.user import User
from app.infrastructure.clients.orchestrator_client import orchestrator_client

logger = get_logger(__name__)


_INTENT_ALIASES: dict[str, str] = {
    "mission_complex": "MISSION_COMPLEX",
    "deep_analysis": "DEEP_ANALYSIS",
    "code_search": "CODE_SEARCH",
    "chat": "DEFAULT",
}


def _normalize_intent_name(raw_intent: object) -> str | None:
    """يُطبع اسم النية القادمة من الواجهة إلى الصيغة التي يفهمها orchestrator."""

    if not isinstance(raw_intent, str):
        return None

    normalized = raw_intent.strip()
    if not normalized:
        return None

    alias_key = normalized.lower()
    if alias_key in _INTENT_ALIASES:
        return _INTENT_ALIASES[alias_key]

    return normalized.upper()


def _build_request_context(payload: dict[str, object], policy: ChatWebSocketPolicy) -> dict[str, object]:
    """يبني سياق الطلب المرسل إلى طبقة orchestrator مع تطبيع النية."""

    context: dict[str, object] = {"route_id": policy.route_id}

    mission_type = payload.get("mission_type")
    normalized_intent = _normalize_intent_name(mission_type)
    if normalized_intent is not None:
        context["intent"] = normalized_intent

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata_intent = _normalize_intent_name(metadata.get("mission_type"))
        if metadata_intent is not None:
            context["intent"] = metadata_intent

    return context


@dataclass(frozen=True)
class ChatWebSocketPolicy:
    """سياسة مسار الدردشة التي تحدد متطلبات الدور ورسائل الرفض."""

    requires_admin: bool
    forbidden_details: str
    route_id: str


def _is_forbidden_by_role(actor: User, policy: ChatWebSocketPolicy) -> bool:
    """يتحقق من انتهاك متطلبات الدور المحددة للمسار."""

    return actor.is_admin != policy.requires_admin


def _adapt_event_for_legacy_compat(
    event: dict[str, object],
    policy: ChatWebSocketPolicy,
) -> dict[str, object]:
    """يحوّل أحداث الأخطاء لمسار الأدمن إلى العقدة legacy عند الحاجة."""

    event_type = str(event.get("type", ""))
    if event_type != "assistant_error" or not policy.requires_admin:
        return event

    payload = event.get("payload")
    content = "Unexpected error."
    if isinstance(payload, dict):
        content = str(payload.get("content", content))

    return {
        "type": "error",
        "payload": {
            "details": content,
            "status_code": 500,
        },
    }


async def _resolve_actor(
    websocket: WebSocket,
    db: AsyncSession,
    auth_extractor: Callable[[WebSocket], tuple[str | None, str | None]],
    user_decoder: Callable[[str, str], int],
) -> tuple[User, str | None] | None:
    """يفك ترميز الهوية من طلب WebSocket ويعيد المستخدم الفعال أو None عند الفشل."""

    token, selected_protocol = auth_extractor(websocket)
    if not token:
        await websocket.close(code=4401)
        return None

    try:
        user_id = user_decoder(token, get_settings().SECRET_KEY)
    except HTTPException:
        await websocket.close(code=4401)
        return None

    actor = await db.get(User, user_id)
    if actor is None or not actor.is_active:
        await websocket.close(code=4401)
        return None

    return actor, selected_protocol


async def stream_chat_via_orchestrator(
    websocket: WebSocket,
    db: AsyncSession,
    policy: ChatWebSocketPolicy,
    auth_extractor: Callable[[WebSocket], tuple[str | None, str | None]],
    user_decoder: Callable[[str, str], int],
) -> None:
    """يشغّل تدفق الدردشة الحي عبر Orchestrator كمسار تنفيذ موحّد.

    يضمن هذا التابع أن جميع المسارات الحية (أدمن/عميل) تستخدم نفس طبقة
    التنفيذ الحديثة، مع الحفاظ على حارس التوافق الذي يرسل fallback عند
    انتهاء التدفق دون أي محتوى قابل للعرض.
    """

    actor_and_protocol = await _resolve_actor(websocket, db, auth_extractor, user_decoder)
    if actor_and_protocol is None:
        return
    actor, selected_protocol = actor_and_protocol

    await websocket.accept(subprotocol=selected_protocol)

    if _is_forbidden_by_role(actor, policy):
        await websocket.send_json(
            {
                "type": "error",
                "payload": {
                    "details": policy.forbidden_details,
                    "status_code": 403,
                },
            }
        )
        await websocket.close(code=4403)
        return

    try:
        while True:
            payload = await websocket.receive_json()
            question = str(payload.get("question", "")).strip()
            if not question:
                await websocket.send_json(
                    {"type": "error", "payload": {"details": "Question is required."}}
                )
                continue

            context = _build_request_context(payload, policy)

            content_delivered = False

            async for event in orchestrator_client.chat_with_agent(
                question=question,
                user_id=actor.id,
                conversation_id=payload.get("conversation_id"),
                history_messages=[],
                context=context,
            ):
                if isinstance(event, dict):
                    evt_type = str(event.get("type", ""))
                    if evt_type in (
                        "assistant_delta",
                        "assistant_final",
                        "assistant_error",
                        "tool_result_summary",
                    ):
                        content_delivered = True
                    await websocket.send_json(_adapt_event_for_legacy_compat(event, policy))
                    continue

                content_delivered = True
                await websocket.send_json(
                    {"type": "assistant_delta", "payload": {"content": str(event)}}
                )

            if not content_delivered:
                logger.warning(
                    "Output Guard triggered: Stream ended without content.",
                    extra={"user_id": actor.id, "route_id": policy.route_id},
                )
                await websocket.send_json(
                    {
                        "type": "assistant_fallback",
                        "payload": {
                            "content": "عذراً، لم أتمكن من استخراج نتيجة نهائية لهذه العملية. يرجى المحاولة مرة أخرى أو صياغة الطلب بشكل أوضح."
                        },
                    }
                )

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected route_id=%s", policy.route_id)
