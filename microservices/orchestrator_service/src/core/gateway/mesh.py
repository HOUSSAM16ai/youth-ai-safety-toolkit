"""
واجهة شبكة البوابة (Legacy Facade).
----------------------------------
تقدم هذه الوحدة طبقة توافق لنموذج NeuralRoutingMesh القديم
مع الحفاظ على العميل المبسط SimpleAIClient في القلب.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator

from app.core.ai_config import get_ai_config
from app.core.interfaces.llm import LLMClient as AIClient
from app.core.types import JSONDict
from microservices.orchestrator_service.src.core.gateway.circuit_breaker import CircuitBreaker
from microservices.orchestrator_service.src.core.gateway.exceptions import (
    AIAllModelsExhaustedError,
    AIProviderError,
)
from microservices.orchestrator_service.src.core.gateway.node import NeuralNode
from microservices.orchestrator_service.src.core.gateway.simple_client import SimpleAIClient

_ai_config = get_ai_config()

# ============================================================================
# Legacy Aliases (For Backward Compatibility)
# ============================================================================

SAFETY_NET_MODEL_ID = "system/safety-net"
"""معرف نموذج شبكة الأمان المستخدم في حالات الانقطاع."""


class NeuralRoutingMesh(SimpleAIClient):
    """
    طبقة توافق تُحاكي واجهة NeuralRoutingMesh القديمة للاختبارات.
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or _ai_config.openrouter_api_key
        super().__init__(api_key=resolved_key)
        self.nodes_map: dict[str, NeuralNode] = {
            SAFETY_NET_MODEL_ID: NeuralNode(
                model_id=SAFETY_NET_MODEL_ID,
                circuit_breaker=CircuitBreaker("safety-net", 1, 1.0),
            )
        }
        self.omni_router = get_omni_router()
        if isinstance(self.omni_router, _DefaultOmniRouter):
            self.omni_router.set_nodes_map(self.nodes_map)

    def _get_prioritized_nodes(self, messages: list[JSONDict]) -> list[NeuralNode]:
        """يعيد قائمة العقد المرتبة حسب توجيه الراوتر."""
        ranked_ids = self.omni_router.get_ranked_nodes(messages)
        return [self.nodes_map[node_id] for node_id in ranked_ids if node_id in self.nodes_map]

    async def _stream_from_node_with_retry(
        self,
        node: NeuralNode,
        messages: list[JSONDict],
    ) -> AsyncGenerator[JSONDict, None]:
        """تنفيذ افتراضي مبسط للبث من عقدة محددة."""
        raise AIProviderError(f"Neural node {node.model_id} has no stream implementation.")

    async def stream_chat(self, messages: list[JSONDict]) -> AsyncGenerator[JSONDict, None]:
        """يبث من العقد المتاحة مع احترام القواطع وحدود المعدل."""
        prioritized_nodes = self._get_prioritized_nodes(messages)

        for node in prioritized_nodes:
            if not node.circuit_breaker.allow_request():
                continue
            if node.rate_limit_cooldown_until > time.time():
                continue

            try:
                async for chunk in self._stream_from_node_with_retry(node, messages):
                    yield chunk
                return
            except Exception:
                continue

        if SAFETY_NET_MODEL_ID in self.nodes_map and SAFETY_NET_MODEL_ID not in [
            node.model_id for node in prioritized_nodes
        ]:
            async for chunk in super()._stream_safety_net():
                yield chunk
            return

        raise AIAllModelsExhaustedError("All models are unavailable.")


class _DefaultOmniRouter:
    """موجه افتراضي يعيد عقد الشبكة وفق ترتيب ثابت."""

    def __init__(self) -> None:
        self._nodes_map: dict[str, NeuralNode] = {}

    def set_nodes_map(self, nodes_map: dict[str, NeuralNode]) -> None:
        """يحقن خريطة العقد ليستخدمها الموجه الافتراضي."""
        self._nodes_map = nodes_map

    def get_ranked_nodes(self, _: list[JSONDict]) -> list[str]:
        ordered = [node_id for node_id in self._nodes_map if node_id != SAFETY_NET_MODEL_ID]
        if SAFETY_NET_MODEL_ID in self._nodes_map:
            ordered.append(SAFETY_NET_MODEL_ID)
        return ordered


def get_omni_router() -> _DefaultOmniRouter:
    """يبني موجهًا افتراضيًا للاستخدام في طبقة التوافق."""
    return _DefaultOmniRouter()


# ============================================================================
# Factory
# ============================================================================


def get_ai_client() -> AIClient:
    """
    Factory function to get the global AI client instance.
    """
    return SimpleAIClient()
