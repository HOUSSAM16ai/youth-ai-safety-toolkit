"""
سجل موجهات API كمصدر حقيقة موحّد.
"""

from fastapi import APIRouter

from app.api.routers import (
    admin,
    content,
    crud,
    customer_chat,
    data_mesh,
    security,
    system,
)

type RouterSpec = tuple[APIRouter, str]


def base_router_registry() -> list[RouterSpec]:
    """
    يبني سجل الموجهات الأساسية للتطبيق بدون موجه البوابة.
    """
    return [
        (system.root_router, ""),
        (system.router, ""),
        (admin.router, ""),
        (security.router, "/api/security"),
        (data_mesh.router, "/api/v1/data-mesh"),
        (crud.router, "/api/v1"),
        (customer_chat.router, ""),
        (content.router, ""),
    ]
