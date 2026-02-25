"""
منطق تهيئة البيانات الأولية لخدمة المستخدمين.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.models import User, UserStatus
from microservices.user_service.src.services.auth.service import AuthService
from microservices.user_service.src.services.rbac import RBACService

logger = logging.getLogger(__name__)


async def seed_initial_data(session: AsyncSession) -> None:
    """
    يقوم بتهيئة البيانات الأولية لخدمة المستخدمين.

    - يتحقق من وجود الأدوار والصلاحيات (RBAC) ويقوم بإنشائها إذا لزم الأمر.
    - يتحقق من وجود أي مستخدم في قاعدة البيانات.
    - إذا لم يتم العثور على مستخدمين، يقوم بإنشاء حساب مدير النظام الافتراضي (System Admin).
    """
    logger.info("Seeding Initial Data...")

    # Seed RBAC (Roles & Permissions)
    rbac = RBACService(session)
    await rbac.ensure_seed()

    # Check if any user exists
    result = await session.execute(select(User).limit(1))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.info("Users already exist. Skipping admin seed.")
        return

    # Create Default Admin
    logger.info("No users found. Creating default Admin user...")
    auth_service = AuthService(session)

    try:
        # Create user
        admin_email = "admin@cogniforge.com"
        admin_pass = "admin"  # Default weak password for initial setup

        user = await auth_service.register_user(
            full_name="System Admin", email=admin_email, password=admin_pass
        )

        # Make Active (just in case default is pending)
        if user.status != UserStatus.ACTIVE:
            user.status = UserStatus.ACTIVE
            session.add(user)
            await session.commit()

        # Promote to Admin
        await auth_service.promote_to_admin(user=user)

        logger.warning(f"Default Admin Created: {admin_email} / {admin_pass}")
        logger.warning("Please change this password immediately!")

    except Exception as e:
        logger.error(f"Failed to seed default admin: {e}")
        await session.rollback()
        raise
