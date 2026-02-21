"""
سجل موجهات API كمصدر حقيقة موحّد.
"""

from fastapi import APIRouter

from app.api.routers import (
    admin,
    content,
    customer_chat,
    data_mesh,
    system,
    ums,
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
        (data_mesh.router, "/api/v1/data-mesh"),
        (ums.router, "/api/v1"),
        (customer_chat.router, ""),
        (content.router, ""),
    ]
