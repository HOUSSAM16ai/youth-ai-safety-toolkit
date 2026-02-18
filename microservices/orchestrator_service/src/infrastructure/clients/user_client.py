"""
User Service Client.
Provides a typed interface to the User Service.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

import httpx
from pydantic import BaseModel

from microservices.orchestrator_service.src.core.http_client_factory import (
    HTTPClientConfig,
    get_http_client,
)
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.core.settings import get_settings

logger = get_logger("user-client")

DEFAULT_USER_SERVICE_URL: Final[str] = "http://user-service:8003"


class UserCountResponse(BaseModel):
    count: int


class UserResponse(BaseModel):
    user_id: UUID
    name: str
    email: str


class UserCreateRequest(BaseModel):
    name: str
    email: str


class UserClient:
    """
    عميل للتفاعل مع خدمة المستخدمين المصغّرة.

    يلتزم بدستور الخدمات المصغّرة (القواعد 4 و11 و21).
    """

    def __init__(self, base_url: str | None = None) -> None:
        """
        تهيئة عميل خدمة المستخدمين مع دعم تبديل العنوان حسب البيئة.
        """
        settings = get_settings()
        resolved_url = base_url or settings.USER_SERVICE_URL or DEFAULT_USER_SERVICE_URL
        self.base_url = resolved_url.rstrip("/")
        self.config = HTTPClientConfig(
            name="user-service-client",
            timeout=10.0,  # Rule 62: Timeouts
            max_connections=50,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        return get_http_client(self.config)

    async def get_user_count(self) -> int:
        """استرجاع العدد الإجمالي للمستخدمين."""
        url = f"{self.base_url}/users/count"
        logger.debug("Calling User Service", extra={"url": url})

        client = await self._get_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return UserCountResponse(**data).count
        except httpx.HTTPError as e:
            logger.error("Failed to get user count", exc_info=e)
            raise
        except Exception as e:
            logger.error("Unexpected error getting user count", exc_info=e)
            raise

    async def create_user(self, name: str, email: str) -> UserResponse:
        """إنشاء مستخدم جديد عبر واجهة الخدمة."""
        url = f"{self.base_url}/users"
        payload = UserCreateRequest(name=name, email=email)

        client = await self._get_client()
        try:
            response = await client.post(url, json=payload.model_dump())
            response.raise_for_status()
            return UserResponse(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                logger.warning(f"User already exists: {email}")
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {email}", exc_info=e)
            raise

    async def get_users(self) -> list[UserResponse]:
        """جلب قائمة جميع المستخدمين."""
        url = f"{self.base_url}/users"
        client = await self._get_client()

        response = await client.get(url)
        response.raise_for_status()

        return [UserResponse(**item) for item in response.json()]


# Singleton instance
user_client = UserClient()
