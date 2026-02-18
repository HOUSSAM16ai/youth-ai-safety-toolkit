# app/core/resilience/circuit_breaker.py
"""
CIRCUIT BREAKER — CENTRALIZED IMPLEMENTATION
============================================

Single source of truth for circuit breaker pattern implementation.
Eliminates the 11 duplicate circuit breaker implementations found in:
- app/core/ai_gateway.py
- app/services/chat_orchestrator_service.py
- app/services/admin_chat_boundary_service.py
- app/services/api_gateway_service.py
- app/services/api_gateway_chaos.py
- app/services/chaos_engineering.py
- app/services/distributed_resilience_service.py
- app/services/aiops_self_healing_service.py
- app/services/deployment_orchestrator_service.py
- app/services/llm_client_service.py
- app/services/service_mesh_integration.py

RESPONSIBILITIES:
✅ Circuit breaker state management
✅ Failure threshold tracking
✅ Recovery timeout handling
✅ Half-open state testing

DOES NOT:
❌ Make actual service calls (caller's responsibility)
❌ Implement retry logic (see retry module)
❌ Implement telemetry (see observability)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum

from microservices.orchestrator_service.src.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing recovery, limited requests


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds to wait before trying half-open
    half_open_max_calls: int = 3  # Max concurrent calls in half-open


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    Prevents cascading failures by stopping requests to failing services.
    Implements the classic circuit breaker pattern with three states:
    - CLOSED: Normal operation
    - OPEN: Failing, reject requests
    - HALF_OPEN: Testing recovery

    Usage:
        breaker = CircuitBreaker("my-service")

        if breaker.allow_request():
            try:
                result = make_call()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
                raise
        else:
            # Circuit is open, fail fast
            raise CircuitOpenError()
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.RLock()

        logger.info(
            f"Circuit breaker '{name}' initialized with "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout}s"
        )

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        with self._lock:
            current_state = self._state

            if current_state == CircuitState.CLOSED:
                return True

            if current_state == CircuitState.OPEN:
                # Check if we should try half-open
                time_since_failure = time.time() - self._last_failure_time
                if time_since_failure >= self.config.timeout:
                    logger.info(f"Circuit '{self.name}' entering HALF_OPEN state")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    return True
                return False

            # HALF_OPEN state
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def can_execute(self) -> tuple[bool, str]:
        """
        Legacy compatibility method.

        Returns:
            Tuple of (can_execute, message)
        """
        with self._lock:
            current_state = self._state
            now = time.time()

            if current_state == CircuitState.CLOSED:
                return True, "ok"

            if current_state == CircuitState.OPEN:
                time_since_failure = now - self._last_failure_time
                if time_since_failure >= self.config.timeout:
                    logger.info(f"Circuit '{self.name}' entering HALF_OPEN state")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
                    return True, "ok"
                remaining = max(0, int(self.config.timeout - time_since_failure))
                return False, f"Circuit open. Retry after {remaining}s"

            # HALF_OPEN state
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True, "ok"
            return False, "Circuit half-open, max test calls reached"

    def record_success(self) -> None:
        """Record a successful call"""
        with self._lock:
            current_state = self._state

            if current_state == CircuitState.HALF_OPEN:
                self._success_count += 1
                logger.debug(
                    f"Circuit '{self.name}' success in HALF_OPEN "
                    f"({self._success_count}/{self.config.success_threshold})"
                )

                if self._success_count >= self.config.success_threshold:
                    logger.info(f"Circuit '{self.name}' closing (recovery successful)")
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0

            elif current_state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    logger.debug(f"Circuit '{self.name}' resetting failure count")
                    self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call"""
        with self._lock:
            current_state = self._state
            self._last_failure_time = time.time()

            if current_state == CircuitState.HALF_OPEN:
                # Failure in half-open immediately opens circuit
                logger.warning(f"Circuit '{self.name}' opening (failure in HALF_OPEN)")
                self._state = CircuitState.OPEN
                self._half_open_calls = 0
                self._success_count = 0

            elif current_state == CircuitState.CLOSED:
                self._failure_count += 1
                logger.debug(
                    f"Circuit '{self.name}' failure "
                    f"({self._failure_count}/{self.config.failure_threshold})"
                )

                if self._failure_count >= self.config.failure_threshold:
                    logger.warning(
                        f"Circuit '{self.name}' opening "
                        f"(threshold reached: {self.config.failure_threshold})"
                    )
                    self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state"""
        with self._lock:
            logger.info(f"Circuit '{self.name}' manually reset")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count"""
        return self._failure_count

    def get_stats(self) -> dict[str, object]:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                    "half_open_max_calls": self.config.half_open_max_calls,
                },
            }


class CircuitBreakerRegistry:
    """
    Singleton registry for managing circuit breakers.

    Provides centralized access to circuit breakers across the application.
    Ensures one circuit breaker per service/resource.
    """

    _instance: CircuitBreakerRegistry | None = None
    _lock = threading.Lock()

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._breakers_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> CircuitBreakerRegistry:
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = CircuitBreakerRegistry()
                    logger.info("Circuit breaker registry initialized")
        return cls._instance

    def get(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Unique name for the circuit breaker
            config: Optional configuration (only used if creating new)

        Returns:
            Circuit breaker instance
        """
        with self._breakers_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created circuit breaker '{name}'")
            return self._breakers[name]

    def reset(self, name: str) -> None:
        """Reset a specific circuit breaker"""
        with self._breakers_lock:
            if name in self._breakers:
                self._breakers[name].reset()

    def reset_all(self) -> None:
        """Reset all circuit breakers"""
        with self._breakers_lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")

    def get_all_stats(self) -> dict[str, dict[str, object]]:
        """Get statistics for all circuit breakers"""
        with self._breakers_lock:
            return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def remove(self, name: str) -> None:
        """Remove a circuit breaker from registry"""
        with self._breakers_lock:
            if name in self._breakers:
                del self._breakers[name]
                logger.info(f"Removed circuit breaker '{name}'")

    def clear(self) -> None:
        """Clear all circuit breakers"""
        with self._breakers_lock:
            self._breakers.clear()
            logger.info("Circuit breaker registry cleared")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""

    def __init__(self, breaker_name: str):
        self.breaker_name = breaker_name
        super().__init__(f"Circuit breaker '{breaker_name}' is OPEN")


# =============================================================================
# PUBLIC API
# =============================================================================


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker from the registry.

    This is the primary function to use for obtaining circuit breakers
    throughout the application.

    Args:
        name: Unique name for the circuit breaker
        config: Optional configuration

    Returns:
        Circuit breaker instance
    """
    registry = CircuitBreakerRegistry.get_instance()
    return registry.get(name, config)


def reset_circuit_breaker(name: str) -> None:
    """Reset a specific circuit breaker"""
    registry = CircuitBreakerRegistry.get_instance()
    registry.reset(name)


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers"""
    registry = CircuitBreakerRegistry.get_instance()
    registry.reset_all()


def get_all_circuit_breaker_stats() -> dict[str, dict[str, object]]:
    """Get statistics for all circuit breakers"""
    registry = CircuitBreakerRegistry.get_instance()
    return registry.get_all_stats()


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    "get_all_circuit_breaker_stats",
    "get_circuit_breaker",
    "reset_all_circuit_breakers",
    "reset_circuit_breaker",
]
