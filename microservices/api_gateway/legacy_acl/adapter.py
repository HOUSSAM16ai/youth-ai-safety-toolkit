"""طبقة ACL وحيدة للوصول إلى core-kernel مع وسم حركة المرور القديمة."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import StreamingResponse

from microservices.api_gateway.config import settings
from microservices.api_gateway.proxy import GatewayProxy

logger = logging.getLogger("api_gateway.legacy_acl")


class LegacyACL:
    """يعزل كل اتصال بالنواة القديمة عبر واجهة واحدة قابلة للمراقبة والقياس."""

    def __init__(self, proxy: GatewayProxy) -> None:
        self._proxy = proxy

    async def forward_http(
        self, request: Request, upstream_path: str, route_id: str
    ) -> StreamingResponse:
        """يمرر طلب HTTP إلى legacy مع وسم تتبعي موحد لحركة legacy."""
        request.state.legacy_route = True
        request.state.legacy_route_id = route_id
        logger.warning(
            "legacy_acl_http route_id=%s path=%s legacy=true", route_id, request.url.path
        )
        return await self._proxy.forward(
            request,
            settings.CORE_KERNEL_URL,
            upstream_path,
            extra_headers={"X-Legacy-Route": "true", "X-Legacy-Route-Id": route_id},
        )

    def chat_upstream_path(self, path: str) -> str:
        """يوحد ترجمة مسارات chat نحو واجهة legacy دون تسريب التفاصيل للبوابة."""
        return f"api/chat/{path}"

    def content_upstream_path(self, path: str) -> str:
        """يوحد ترجمة مسارات content نحو واجهة legacy دون تسريب التفاصيل للبوابة."""
        return f"v1/content/{path}"

    def websocket_target(self, upstream_path: str, route_id: str) -> str:
        """يعيد عنوان websocket للنواة القديمة مع تسجيل معرف المسار."""
        logger.warning(
            "legacy_acl_ws route_id=%s upstream_path=%s legacy=true", route_id, upstream_path
        )
        base_url = settings.CORE_KERNEL_URL.replace("http", "ws", 1)
        return f"{base_url}/{upstream_path}"
