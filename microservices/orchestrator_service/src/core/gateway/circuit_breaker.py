"""طبقة توافق لقاطع الدائرة وفق واجهة البوابة القديمة."""

from microservices.orchestrator_service.src.core.resilience.circuit_breaker import (
    CircuitBreaker as CoreCircuitBreaker,
)
from microservices.orchestrator_service.src.core.resilience.circuit_breaker import (
    CircuitBreakerConfig,
)


class CircuitBreaker(CoreCircuitBreaker):
    """
    قاطع دائرة متوافق مع الواجهة القديمة.

    يسمح بتمرير عتبة الفشل والمهلة مباشرة لتسهيل اختبارات التوافق.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        timeout: float | None = None,
    ) -> None:
        config = CircuitBreakerConfig()
        if failure_threshold is not None:
            config.failure_threshold = failure_threshold
        if timeout is not None:
            config.timeout = timeout
        super().__init__(name=name, config=config)


__all__ = ["CircuitBreaker"]
