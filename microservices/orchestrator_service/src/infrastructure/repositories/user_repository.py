"""
تنفيذ مستودع المستخدمين باستخدام SQLAlchemy.

يطبق عقد `UserRepository` من طبقة النطاق مع صرامة أنواع وتوثيق عربي
يحافظ على اتساق عقود الـ API-first ويمنع البيانات غير المصرح بها.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.orchestrator_service.src.core.domain.repositories import UserUpdatePayload
from microservices.orchestrator_service.src.core.domain.user import User


class SQLAlchemyUserRepository:
    """تنفيذ SQLAlchemy لواجهة `UserRepository`."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_id(self, user_id: int) -> User | None:
        """يجلب المستخدم بالمعرّف الأساسي أو يعيد None عند عدم الوجود."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        """يجلب المستخدم وفق البريد الإلكتروني بعد تحويله إلى أحرف صغيرة."""
        normalized = email.lower().strip()
        result = await self._session.execute(select(User).where(User.email == normalized))
        return result.scalar_one_or_none()

    async def create(self, user_data: UserUpdatePayload) -> User:
        """ينشئ مستخدمًا جديدًا مع دعم ضبط البريد وتشفير كلمة المرور عند توفرها."""
        normalized_email = user_data.get("email", "").lower().strip()
        user = User(
            full_name=user_data.get("full_name", ""),
            email=normalized_email,
            is_admin=bool(user_data.get("is_admin", False)),
        )

        password = user_data.get("password")
        if password:
            user.set_password(password)

        self._session.add(user)
        await self._session.flush()
        return user

    async def update(self, user_id: int, user_data: UserUpdatePayload) -> User | None:
        """يحدّث مستخدمًا قائمًا ويطبّق ضبط البريد وتشفير كلمة المرور عند الحاجة."""
        user = await self.find_by_id(user_id)
        if not user:
            return None

        if "email" in user_data:
            user.email = str(user_data["email"]).lower().strip()
        if "full_name" in user_data:
            user.full_name = str(user_data["full_name"])
        if "is_admin" in user_data:
            user.is_admin = bool(user_data["is_admin"])
        if "password" in user_data:
            user.set_password(str(user_data["password"]))

        await self._session.flush()
        return user

    async def delete(self, user_id: int) -> bool:
        """يحذف المستخدم المحدد إذا وُجد وإلا يعيد False."""
        user = await self.find_by_id(user_id)
        if not user:
            return False
        await self._session.delete(user)
        await self._session.flush()
        return True
