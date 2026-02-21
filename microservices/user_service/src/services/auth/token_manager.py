"""
Token Manager for User Service.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.models import RefreshToken, User
from microservices.user_service.src.core.common import utc_now
from microservices.user_service.src.core.security import pwd_context

REFRESH_EXPIRE_DAYS: Final[int] = 14


class TokenManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_refresh_token(
        self,
        user: User,
        *,
        family_id: str | None,
        ip: str | None,
        user_agent: str | None,
    ) -> str:
        token_id = str(uuid.uuid4())
        raw_secret = secrets.token_urlsafe(32)
        hashed = pwd_context.hash(raw_secret)
        expires_at = utc_now() + timedelta(days=REFRESH_EXPIRE_DAYS)

        record = RefreshToken(
            token_id=token_id,
            family_id=family_id or str(uuid.uuid4()),
            user_id=user.id,
            hashed_token=hashed,
            expires_at=expires_at,
            revoked_at=None,
            created_ip=ip,
            user_agent=user_agent,
            created_at=utc_now(),
        )
        self.session.add(record)
        await self.session.commit()
        return f"{token_id}:{raw_secret}"

    async def get_refresh_record(self, token_id: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_id == token_id)
        )
        return result.scalar_one_or_none()

    async def revoke_record(self, record: RefreshToken, *, replaced_by: str | None = None) -> None:
        record.revoke(revoked_at=utc_now(), replaced_by=replaced_by)
        await self.session.commit()

    async def revoke_family(self, family_id: str) -> None:
        now = utc_now()
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None)
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.revoke(revoked_at=now)
        await self.session.commit()

    async def revoke_user_tokens(self, user: User) -> int:
        now = utc_now()
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.revoke(revoked_at=now)
        await self.session.commit()
        return len(tokens)
