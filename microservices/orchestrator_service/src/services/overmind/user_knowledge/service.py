"""
خدمة معرفة المستخدمين الموحدة (Unified User Knowledge Service).

Facade Pattern يوفر واجهة موحدة لجميع عمليات معرفة المستخدمين.

المبادئ:
- Facade Pattern: واجهة بسيطة لنظام معقد
- Dependency Injection: حقن التبعيات
- Context Manager: إدارة الموارد تلقائياً
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.database import async_session_factory
from microservices.orchestrator_service.src.core.domain.user import User
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.user_knowledge.basic_info import (
    get_user_basic_info,
    list_all_users,
)
from microservices.orchestrator_service.src.services.overmind.user_knowledge.performance import (
    get_user_performance,
)
from microservices.orchestrator_service.src.services.overmind.user_knowledge.relations import (
    get_user_relations,
)
from microservices.orchestrator_service.src.services.overmind.user_knowledge.search import (
    search_users,
)
from microservices.orchestrator_service.src.services.overmind.user_knowledge.statistics import (
    get_user_statistics,
)

logger = get_logger(__name__)


class UserKnowledge:
    """
    معرفة المستخدم الشاملة (Comprehensive User Knowledge).

    Facade Pattern يوفر واجهة موحدة لجميع عمليات معرفة المستخدمين:
    - من هو؟ (الهوية)
    - ماذا يفعل؟ (النشاطات)
    - كيف يتصرف؟ (السلوك)
    - ماذا يفضل؟ (التفضيلات)
    - كيف أداؤه؟ (المقاييس)

    الاستخدام:
        >>> async with UserKnowledge() as uk:
        >>>     user_info = await uk.get_user_complete_profile(user_id=1)
        >>>     logger.info(user_info['basic']['name'])
        >>>     logger.info(user_info['statistics']['total_missions'])
    """

    def __init__(self) -> None:
        """تهيئة نظام معرفة المستخدمين."""
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "UserKnowledge":
        """فتح جلسة قاعدة بيانات مستقلة."""
        self._session = async_session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """إغلاق الجلسة مع التراجع عند الخطأ."""
        if not self._session:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()
        self._session = None

    # =========================================================================
    # المعلومات الأساسية (Basic Information)
    # =========================================================================

    async def get_user_basic_info(self, user_id: int) -> dict[str, object]:
        """
        الحصول على المعلومات الأساسية للمستخدم.

        Args:
            user_id: معرّف المستخدم

        Returns:
            dict: المعلومات الأساسية
        """
        if not self._session:
            return {}
        return await get_user_basic_info(self._session, user_id)

    # =========================================================================
    # الإحصائيات والنشاطات (Statistics & Activities)
    # =========================================================================

    async def get_user_statistics(self, user_id: int) -> dict[str, object]:
        """
        الحصول على إحصائيات المستخدم.

        Args:
            user_id: معرّف المستخدم

        Returns:
            dict: إحصائيات شاملة
        """
        if not self._session:
            return {}
        return await get_user_statistics(self._session, user_id)

    # =========================================================================
    # السلوك والأداء (Behavior & Performance)
    # =========================================================================

    async def get_user_performance(self, user_id: int) -> dict[str, object]:
        """
        الحصول على مقاييس أداء المستخدم.

        Args:
            user_id: معرّف المستخدم

        Returns:
            dict: مقاييس الأداء
        """
        if not self._session:
            return {}
        return await get_user_performance(self._session, user_id)

    # =========================================================================
    # العلاقات والروابط (Relations & Connections)
    # =========================================================================

    async def get_user_relations(self, user_id: int) -> dict[str, object]:
        """
        الحصول على علاقات المستخدم مع الكيانات الأخرى.

        Args:
            user_id: معرّف المستخدم

        Returns:
            dict: العلاقات والروابط
        """
        if not self._session:
            return {}
        return await get_user_relations(self._session, user_id)

    # =========================================================================
    # الملف الشامل (Complete Profile)
    # =========================================================================

    async def get_user_complete_profile(self, user_id: int) -> dict[str, object]:
        """
        الحصول على الملف الشخصي الكامل والشامل للمستخدم.

        Args:
            user_id: معرّف المستخدم

        Returns:
            dict: الملف الشخصي الكامل

        يجمع جميع المعلومات:
            - basic: المعلومات الأساسية
            - statistics: الإحصائيات
            - performance: مقاييس الأداء
            - relations: العلاقات
        """
        logger.info(f"Building complete profile for user {user_id}")

        # جمع جميع المعلومات
        basic = await self.get_user_basic_info(user_id)

        if not basic:
            logger.warning(f"User {user_id} not found")
            return {
                "error": "User not found",
                "user_id": user_id,
            }

        statistics = await self.get_user_statistics(user_id)
        performance = await self.get_user_performance(user_id)
        relations = await self.get_user_relations(user_id)

        profile = {
            "user_id": user_id,
            "basic": basic,
            "statistics": statistics,
            "performance": performance,
            "relations": relations,
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Complete profile generated for user {user_id}")
        return profile

    # =========================================================================
    # قائمة المستخدمين (Users List)
    # =========================================================================

    async def list_all_users(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        """
        عرض قائمة جميع المستخدمين مع معلومات مختصرة.

        Args:
            limit: عدد المستخدمين المطلوب
            offset: الإزاحة (للصفحات)

        Returns:
            list[dict]: قائمة المستخدمين
        """
        if not self._session:
            return []
        return await list_all_users(self._session, limit, offset)

    async def count_users(self) -> int:
        """
        عد جميع المستخدمين المسجلين بدقة عبر قاعدة البيانات.

        Returns:
            int: إجمالي عدد المستخدمين.
        """
        if not self._session:
            return 0
        result = await self._session.execute(select(func.count()).select_from(User))
        return int(result.scalar() or 0)

    # =========================================================================
    # البحث (Search)
    # =========================================================================

    async def search_users(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """
        البحث عن مستخدمين.

        Args:
            query: نص البحث (اسم أو بريد)
            limit: عدد النتائج

        Returns:
            list[dict]: نتائج البحث
        """
        if not self._session:
            return []
        return await search_users(self._session, query, limit)
