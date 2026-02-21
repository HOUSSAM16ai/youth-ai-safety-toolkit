"""
Registration Manager for User Service.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.models import User, UserStatus
from microservices.user_service.src.services.rbac import STANDARD_ROLE, RBACService


class RegistrationManager:
    def __init__(self, session: AsyncSession, rbac: RBACService) -> None:
        self.session = session
        self.rbac = rbac

    async def register_user(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
    ) -> User:
        await self.rbac.ensure_seed()
        normalized_email = email.lower().strip()
        existing = await self.session.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

        user = User(
            full_name=full_name,
            email=normalized_email,
            is_admin=False,
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        user.set_password(password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        await self.rbac.assign_role(user, STANDARD_ROLE)
        return user
