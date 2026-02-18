from abc import ABC, abstractmethod

from microservices.orchestrator_service.src.core.gateway.models import (
    ProviderCandidate,
    RoutingStrategy,
)


class BaseRoutingStrategy(ABC):
    """واجهة الاستراتيجية الأساسية لحساب درجات المرشحين."""

    @abstractmethod
    def calculate_scores(self, candidates: list[ProviderCandidate]) -> None:
        """تحديث درجات المرشحين داخل القائمة المُمررة."""
        raise NotImplementedError


class CostOptimizedStrategy(BaseRoutingStrategy):
    """استراتيجية تُركز على تقليل التكلفة الإجمالية."""

    def calculate_scores(self, candidates: list[ProviderCandidate]) -> None:
        for c in candidates:
            c["score"] = 1.0 / (c["cost"] + 0.001)


class LatencyBasedStrategy(BaseRoutingStrategy):
    """استراتيجية تُفضل أقل زمن استجابة."""

    def calculate_scores(self, candidates: list[ProviderCandidate]) -> None:
        for c in candidates:
            c["score"] = 1.0 / (c["latency"] + 0.001)


class IntelligentRoutingStrategy(BaseRoutingStrategy):
    """استراتيجية ذكية تُوازن بين التكلفة والسرعة والصحة."""

    def calculate_scores(self, candidates: list[ProviderCandidate]) -> None:
        if not candidates:
            return

        min_cost = min(c["cost"] for c in candidates)
        max_cost = max(c["cost"] for c in candidates)
        cost_range = max_cost - min_cost if max_cost > min_cost else 1.0

        min_latency = min(c["latency"] for c in candidates)
        max_latency = max(c["latency"] for c in candidates)
        latency_range = max_latency - min_latency if max_latency > min_latency else 1.0

        for c in candidates:
            norm_cost = (c["cost"] - min_cost) / cost_range if cost_range > 0 else 0.0
            norm_latency = (
                (c["latency"] - min_latency) / latency_range if latency_range > 0 else 0.0
            )

            # Score: Higher is better.
            c["score"] = (
                (1.0 - norm_cost) * 0.3 + (1.0 - norm_latency) * 0.5 + c["health_score"] * 0.2
            )


class FallbackStrategy(BaseRoutingStrategy):
    """استراتيجية احتياطية عند عدم توفر استراتيجية محددة."""

    def calculate_scores(self, candidates: list[ProviderCandidate]) -> None:
        for c in candidates:
            cost_score = 1.0 / (c["cost"] + 0.001)
            latency_score = 1.0 / (c["latency"] + 0.001)
            c["score"] = cost_score * 0.3 + latency_score * 0.5 + c["health_score"] * 0.2


STRATEGY_MAP = {
    RoutingStrategy.COST_OPTIMIZED: CostOptimizedStrategy(),
    RoutingStrategy.LATENCY_BASED: LatencyBasedStrategy(),
    RoutingStrategy.INTELLIGENT: IntelligentRoutingStrategy(),
}


def get_strategy(strategy_enum: RoutingStrategy) -> BaseRoutingStrategy:
    """إرجاع الاستراتيجية المناسبة أو الاستراتيجية الاحتياطية عند الغياب."""
    return STRATEGY_MAP.get(strategy_enum, FallbackStrategy())
