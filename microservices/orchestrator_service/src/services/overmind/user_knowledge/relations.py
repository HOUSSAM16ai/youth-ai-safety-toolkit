"""
إدارة علاقات المستخدمين (User Relations Management).

يوفر العلاقات بين المستخدمين والكيانات الأخرى.

المبادئ:
- Single Responsibility: فقط العلاقات
- Performance: استعلامات محسّنة
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.domain.chat import (
    CustomerConversation,
    CustomerMessage,
)
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.models.mission import Mission

logger = get_logger(__name__)


async def get_user_relations(session: AsyncSession, user_id: int) -> dict[str, object]:
    """
    الحصول على علاقات المستخدم مع الكيانات الأخرى.

    Args:
        session: جلسة قاعدة البيانات
        user_id: معرّف المستخدم

    Returns:
        dict: العلاقات والروابط

    يشمل:
        - recent_missions: قائمة المهام (آخر 5)
        - recent_messages: الرسائل الأخيرة (آخر 5)
    """
    try:
        relations = {}

        # المهام الأخيرة (Recent Missions)
        missions_query = (
            select(Mission)
            .where(Mission.initiator_id == user_id)
            .order_by(Mission.created_at.desc())
            .limit(5)
        )

        missions_result = await session.execute(missions_query)
        missions = missions_result.scalars().all()

        relations["recent_missions"] = [
            {
                "id": m.id,
                "objective": m.objective,
                "status": m.status.value if hasattr(m.status, "value") else str(m.status),
                "created_at": m.created_at.isoformat() if hasattr(m, "created_at") else None,
            }
            for m in missions
        ]

        # الرسائل الأخيرة (Recent Messages)
        messages_query = (
            select(CustomerMessage)
            .join(CustomerConversation, CustomerMessage.conversation_id == CustomerConversation.id)
            .where(CustomerConversation.user_id == user_id)
            .order_by(CustomerMessage.created_at.desc())
            .limit(5)
        )

        messages_result = await session.execute(messages_query)
        messages = messages_result.scalars().all()

        relations["recent_messages"] = [
            {
                "id": msg.id,
                "role": msg.role if hasattr(msg, "role") else "user",
                "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                "created_at": msg.created_at.isoformat() if hasattr(msg, "created_at") else None,
            }
            for msg in messages
        ]

        logger.info(f"Retrieved relations for user {user_id}")
        return relations

    except Exception as e:
        logger.error(f"Error getting relations for user {user_id}: {e}")
        return {}
