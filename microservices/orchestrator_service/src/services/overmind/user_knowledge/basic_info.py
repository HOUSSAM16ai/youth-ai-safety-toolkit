"""
إدارة المعلومات الأساسية للمستخدمين (User Basic Information Management).

يوفر الوصول إلى المعلومات الأساسية للمستخدمين من قاعدة البيانات.

المبادئ:
- Single Responsibility: فقط المعلومات الأساسية
- Error Handling: معالجة شاملة للأخطاء
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.domain.user import User
from microservices.orchestrator_service.src.core.logging import get_logger

logger = get_logger(__name__)


async def get_user_basic_info(session: AsyncSession, user_id: int) -> dict[str, object]:
    """
    الحصول على المعلومات الأساسية للمستخدم.

    Args:
        session: جلسة قاعدة البيانات
        user_id: معرّف المستخدم

    Returns:
        dict: المعلومات الأساسية

    يشمل:
        - id: المعرّف الفريد
        - full_name: الاسم الكامل
        - email: البريد الإلكتروني
        - is_admin: هل هو مسؤول
        - is_active: نشط أم لا
        - status: حالة الحساب
        - created_at: تاريخ الإنشاء
        - updated_at: آخر تحديث
    """
    try:
        # الاستعلام عن المستخدم
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {user_id} not found")
            return {}

        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "status": user.status.value if hasattr(user.status, "value") else str(user.status),
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting basic info for user {user_id}: {e}")
        return {}


async def list_all_users(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """
    عرض قائمة جميع المستخدمين مع معلومات مختصرة مرتبة بالأحدث.

    Args:
        session: جلسة قاعدة البيانات
        limit: عدد المستخدمين المطلوب
        offset: الإزاحة (للصفحات)

    Returns:
        list[dict]: قائمة المستخدمين
    """
    try:
        # الاستعلام عن المستخدمين بترتيب الأحدث
        query = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        users = result.scalars().all()

        users_list: list[dict[str, object]] = []
        for user in users:
            users_list.append(
                {
                    "id": user.id,
                    "full_name": user.full_name,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "status": user.status.value
                    if hasattr(user.status, "value")
                    else str(user.status),
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                }
            )

        logger.info(f"Listed {len(users_list)} users")
        return users_list

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return []
