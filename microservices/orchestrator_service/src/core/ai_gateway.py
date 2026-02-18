"""
بوابة الذكاء الاصطناعي (AI Gateway).

يعمل هذا الملف كواجهة (Facade) للوحدات الذرية الموجودة في `app/core/gateway/`.
يحافظ على التوافق مع الإصدارات السابقة مع تطبيق SRP عبر البنية الجديدة.

المبادئ (Principles):
- Harvard CS50 2025: توثيق عربي، صرامة الأنواع
- Berkeley SICP: Abstraction Barriers (الواجهة تخفي التعقيد)
- SOLID: Facade Pattern (واجهة مبسطة لنظام معقد)

الاستخدام (Usage):
    client = get_ai_client()
    response = await client.generate("prompt")
"""

import logging

from microservices.orchestrator_service.src.core.gateway.connection import ConnectionManager

# --- Import Atomic Modules ---
from microservices.orchestrator_service.src.core.gateway.exceptions import (
    AIAllModelsExhaustedError,
    AICircuitOpenError,
    AIConnectionError,
    AIError,
    AIProviderError,
    AIRateLimitError,
)
from microservices.orchestrator_service.src.core.gateway.mesh import (
    AIClient,
    NeuralRoutingMesh,
    get_ai_client,
)
from microservices.orchestrator_service.src.core.superhuman_performance_optimizer import (
    get_performance_optimizer,
)

# Re-export key components for backward compatibility
__all__ = [
    "AIAllModelsExhaustedError",
    "AICircuitOpenError",
    "AIClient",
    "AIConnectionError",
    "AIError",
    "AIProviderError",
    "AIRateLimitError",
    "ConnectionManager",
    "NeuralRoutingMesh",
    "ai_gateway",
    "get_ai_client",
    "get_performance_report",
    "get_recommended_model",
]

logger = logging.getLogger(__name__)
_performance_optimizer = get_performance_optimizer()


def get_performance_report() -> dict[str, object]:
    """
    الحصول على تقرير أداء شامل من محسن الأداء.

    يفوض العملية إلى خدمة المحسن (Optimizer Service).

    Returns:
        تقرير مفصل عن أداء النماذج المختلفة
    """
    return _performance_optimizer.get_detailed_report()


def get_recommended_model(available_models: list[str], context: str = "") -> str:
    """
    الحصول على النموذج الموصى به بناءً على الأداء التاريخي.

    يستخدم الذكاء الاصطناعي لاختيار أفضل نموذج بناءً على السياق والأداء السابق.

    Args:
        available_models: قائمة النماذج المتاحة
        context: السياق الحالي (اختياري)

    Returns:
        اسم النموذج الموصى به
    """
    return _performance_optimizer.get_recommended_model(available_models, context)


class AIGatewayFacade:
    """
    واجهة موحدة لعمليات بوابة الذكاء الاصطناعي (AI Gateway Facade).
    """

    def __init__(self) -> None:
        self._client: AIClient | None = None

    @property
    def client(self) -> AIClient:
        if not self._client:
            self._client = get_ai_client()
        return self._client

    async def generate_text(self, prompt: str, **kwargs) -> dict[str, str | int | bool]:
        return await self.client.generate_text(prompt, **kwargs)  # type: ignore

    async def forge_new_code(self, **kwargs) -> dict[str, str | int | bool]:
        return await self.client.forge_new_code(**kwargs)  # type: ignore

    def __getattr__(self, name: str) -> object:
        return getattr(self.client, name)


# Singleton instance
ai_gateway = AIGatewayFacade()
