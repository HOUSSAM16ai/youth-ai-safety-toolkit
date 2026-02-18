"""
البحث في المستخدمين (User Search).

يوفر عمليات البحث والاستعلام عن المستخدمين.

المبادئ:
- Single Responsibility: فقط البحث
- Performance: استعلامات محسّنة
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.domain.user import User
from microservices.orchestrator_service.src.core.logging import get_logger

logger = get_logger(__name__)


async def search_users(
    session: AsyncSession,
    query: str,
    limit: int = 10,
) -> list[dict[str, object]]:
    """
    البحث عن مستخدمين.

    Args:
        session: جلسة قاعدة البيانات
        query: نص البحث (اسم أو بريد)
        limit: عدد النتائج

    Returns:
        list[dict]: نتائج البحث
    """
    try:
        # البحث في الاسم أو البريد
        search_query = (
            select(User)
            .where((User.name.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%")))
            .limit(limit)
        )

        result = await session.execute(search_query)
        users = result.scalars().all()

        results = []
        for user in users:
            results.append(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                }
            )

        logger.info(f"Found {len(results)} users matching '{query}'")
        return results

    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return []
