"""
إدارة إحصائيات المستخدمين (User Statistics Management).

يوفر الإحصائيات والنشاطات للمستخدمين.

المبادئ:
- Single Responsibility: فقط الإحصائيات
- Performance: استعلامات محسّنة
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.domain.chat import (
    CustomerConversation,
    CustomerMessage,
)
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.models.mission import Mission, Task

logger = get_logger(__name__)


async def get_user_statistics(session: AsyncSession, user_id: int) -> dict[str, int | str | None]:
    """
    الحصول على إحصائيات المستخدم.
    Get comprehensive user statistics.

    Args:
        session: جلسة قاعدة البيانات
        user_id: معرّف المستخدم

    Returns:
        dict: إحصائيات شاملة
    """
    try:
        stats = {}

        # 1. إحصائيات المهام | Missions statistics
        await _get_missions_statistics(session, user_id, stats)

        # 2. إحصائيات المهام الفرعية | Tasks statistics
        await _get_tasks_statistics(session, user_id, stats)

        # 3. إحصائيات الرسائل | Messages statistics
        await _get_messages_statistics(session, user_id, stats)

        # 4. آخر نشاط | Last activity
        await _get_last_activity(session, user_id, stats)

        logger.info(f"Retrieved statistics for user {user_id}")
        return stats

    except Exception as e:
        logger.error(f"Error getting statistics for user {user_id}: {e}")
        return {}


async def _get_missions_statistics(
    session: AsyncSession, user_id: int, stats: dict[str, int | str | None]
) -> None:
    """
    الحصول على إحصائيات المهام.
    Get missions statistics for user.
    """
    missions_query = select(
        func.count(Mission.id).label("total"),
        func.sum(func.cast(Mission.status == "completed", int)).label("completed"),
        func.sum(func.cast(Mission.status == "failed", int)).label("failed"),
        func.sum(func.cast(Mission.status == "in_progress", int)).label("active"),
    ).where(Mission.initiator_id == user_id)

    missions_result = await session.execute(missions_query)
    missions_row = missions_result.one_or_none()

    if missions_row:
        stats["total_missions"] = missions_row.total or 0
        stats["completed_missions"] = missions_row.completed or 0
        stats["failed_missions"] = missions_row.failed or 0
        stats["active_missions"] = missions_row.active or 0
    else:
        _set_default_missions_stats(stats)


def _set_default_missions_stats(stats: dict[str, int | str | None]) -> None:
    """
    تعيين إحصائيات المهام الافتراضية.
    Set default missions statistics.
    """
    stats["total_missions"] = 0
    stats["completed_missions"] = 0
    stats["failed_missions"] = 0
    stats["active_missions"] = 0


async def _get_tasks_statistics(
    session: AsyncSession, user_id: int, stats: dict[str, int | str | None]
) -> None:
    """
    الحصول على إحصائيات المهام الفرعية.
    Get sub-tasks statistics for user.
    """
    tasks_query = (
        select(
            func.count(Task.id).label("total"),
            func.sum(func.cast(Task.status == "completed", int)).label("completed"),
        )
        .join(Mission)
        .where(Mission.initiator_id == user_id)
    )

    tasks_result = await session.execute(tasks_query)
    tasks_row = tasks_result.one_or_none()

    if tasks_row:
        stats["total_tasks"] = tasks_row.total or 0
        stats["completed_tasks"] = tasks_row.completed or 0
    else:
        _set_default_tasks_stats(stats)


def _set_default_tasks_stats(stats: dict[str, int | str | None]) -> None:
    """
    تعيين إحصائيات المهام الفرعية الافتراضية.
    Set default tasks statistics.
    """
    stats["total_tasks"] = 0
    stats["completed_tasks"] = 0


async def _get_messages_statistics(
    session: AsyncSession, user_id: int, stats: dict[str, int | str | None]
) -> None:
    """
    الحصول على إحصائيات الرسائل.
    Get chat messages statistics for user.
    """
    messages_query = (
        select(func.count(CustomerMessage.id))
        .join(CustomerConversation, CustomerMessage.conversation_id == CustomerConversation.id)
        .where(CustomerConversation.user_id == user_id)
    )
    messages_result = await session.execute(messages_query)
    stats["total_chat_messages"] = messages_result.scalar() or 0


async def _get_last_activity(
    session: AsyncSession, user_id: int, stats: dict[str, int | str | None]
) -> None:
    """
    الحصول على آخر نشاط للمستخدم.
    Get user's last activity timestamp.
    """
    last_message_query = (
        select(CustomerMessage.created_at)
        .join(CustomerConversation, CustomerMessage.conversation_id == CustomerConversation.id)
        .where(CustomerConversation.user_id == user_id)
        .order_by(CustomerMessage.created_at.desc())
        .limit(1)
    )

    last_message_result = await session.execute(last_message_query)
    last_message = last_message_result.scalar_one_or_none()

    if last_message:
        stats["last_activity"] = last_message.isoformat()
    else:
        stats["last_activity"] = None
