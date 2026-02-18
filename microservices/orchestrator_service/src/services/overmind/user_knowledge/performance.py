"""
إدارة مقاييس أداء المستخدمين (User Performance Metrics Management).

يوفر مقاييس الأداء والإنتاجية للمستخدمين.

المبادئ:
- Single Responsibility: فقط مقاييس الأداء
- Analytics: تحليلات متقدمة
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_logger
from microservices.orchestrator_service.src.models.mission import Mission
from microservices.orchestrator_service.src.services.overmind.user_knowledge.statistics import (
    get_user_statistics,
)

logger = get_logger(__name__)


async def get_user_performance(
    session: AsyncSession, user_id: int
) -> dict[str, float | int | str | None]:
    """
    الحصول على مقاييس أداء المستخدم.
    Get comprehensive user performance metrics.

    Args:
        session: جلسة قاعدة البيانات
        user_id: معرّف المستخدم

    Returns:
        dict: مقاييس الأداء
    """
    try:
        performance = {}

        # 1. معدل النجاح | Success rate
        await _calculate_success_rate(session, user_id, performance)

        # 2. متوسط مدة المهمة | Average mission duration
        await _calculate_average_duration(session, user_id, performance)

        # 3. المهام في الأسبوع | Missions per week
        await _calculate_weekly_missions(session, user_id, performance)

        # 4. درجات الأداء | Performance scores
        _calculate_performance_scores(performance)

        logger.info(f"Retrieved performance metrics for user {user_id}")
        return performance

    except Exception as e:
        logger.error(f"Error getting performance for user {user_id}: {e}")
        return {}


async def _calculate_success_rate(
    session: AsyncSession, user_id: int, performance: dict[str, float | int | str | None]
) -> None:
    """
    حساب معدل النجاح.
    Calculate success rate from mission statistics.
    """
    stats = await get_user_statistics(session, user_id)
    total = stats.get("total_missions", 0)
    completed = stats.get("completed_missions", 0)

    if total > 0:
        performance["success_rate"] = (completed / total) * 100
    else:
        performance["success_rate"] = 0.0


async def _calculate_average_duration(
    session: AsyncSession, user_id: int, performance: dict[str, float | int | str | None]
) -> None:
    """
    حساب متوسط مدة المهمة.
    Calculate average mission duration in hours.
    """
    duration_query = select(
        func.avg(
            func.extract("epoch", Mission.updated_at) - func.extract("epoch", Mission.created_at)
        ).label("avg_duration_seconds")
    ).where(and_(Mission.initiator_id == user_id, Mission.status == "completed"))

    duration_result = await session.execute(duration_query)
    avg_duration_seconds = duration_result.scalar()

    if avg_duration_seconds:
        # تحويل من ثواني إلى ساعات | Convert seconds to hours
        performance["average_mission_duration_hours"] = avg_duration_seconds / 3600
    else:
        performance["average_mission_duration_hours"] = 0.0


async def _calculate_weekly_missions(
    session: AsyncSession, user_id: int, performance: dict[str, float | int | str | None]
) -> None:
    """
    حساب المهام في الأسبوع الماضي.
    Calculate missions in the past week.
    """
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    recent_missions_query = select(func.count(Mission.id)).where(
        and_(Mission.initiator_id == user_id, Mission.created_at >= seven_days_ago)
    )

    recent_result = await session.execute(recent_missions_query)
    performance["missions_per_week"] = recent_result.scalar() or 0


def _calculate_performance_scores(performance: dict[str, float | int | str | None]) -> None:
    """
    حساب درجات الإنتاجية والجودة.
    Calculate productivity and quality scores.
    """
    # درجة الإنتاجية | Productivity score (based on completed missions)
    completed = performance.get("success_rate", 0) / 100
    productivity = min(completed * 100, 100)
    performance["productivity_score"] = productivity

    # درجة الجودة | Quality score (based on success rate)
    quality = performance.get("success_rate", 0)
    performance["quality_score"] = min(quality, 100)
