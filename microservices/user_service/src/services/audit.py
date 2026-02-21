"""
Centralized audit service package.
Provides high-precision logging for sensitive operations.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.user_service.models import AuditLog
from microservices.user_service.src.core.common import utc_now

logger = logging.getLogger(__name__)


class AuditLogEntry(BaseModel):
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: str | None
    metadata: Mapping[str, object] | None = None
    ip: str | None
    user_agent: str | None


class AuditService:
    """
    High-precision audit service with strict schema validation and async persistence.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        target_type: str,
        target_id: str | None,
        metadata: Mapping[str, object],
        ip: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        """
        Record an audit log entry with strict validation.
        """
        try:
            payload = AuditLogEntry(
                actor_user_id=actor_user_id,
                action=str(action),
                target_type=target_type,
                target_id=target_id,
                metadata=metadata,
                ip=ip,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Audit log validation failed: {e}. Payload: {metadata}")
            raise

        details_dict = dict(payload.metadata) if payload.metadata else {}

        entry = AuditLog(
            actor_user_id=payload.actor_user_id,
            action=str(payload.action),
            target_type=payload.target_type,
            target_id=payload.target_id,
            details=details_dict,
            ip=payload.ip,
            user_agent=payload.user_agent,
            created_at=utc_now(),
        )

        try:
            self.session.add(entry)
            await self.session.commit()
            await self.session.refresh(entry)
            return entry
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")
            await self.session.rollback()
            raise
