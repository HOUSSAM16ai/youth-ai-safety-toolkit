"""
Service Registry.

Manages microservice registration and discovery dynamically.
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

import httpx

from .config import ServiceEndpoint

logger = logging.getLogger("api-gateway")


@dataclass(slots=True)
class ServiceHealth:
    """
    Service Health Status.

    Attributes:
        is_healthy: Is the service healthy
        last_check: Last check timestamp
        response_time_ms: Response time in ms
        error_message: Error message if any
    """

    is_healthy: bool
    last_check: datetime
    response_time_ms: float | None = None
    error_message: str | None = None


class ServiceRegistry:
    """
    Microservice Registry.

    Provides:
    - Service Registration
    - Service Discovery
    - Health Checks
    - Simple Load Balancing

    Principles:
    - Functional Core: Data separated from logic
    - Immutability: Registered services are static (in this version)
    - Explicit State: Clear and defined state
    """

    def __init__(
        self,
        services: tuple[ServiceEndpoint, ...] = (),
        health_check_interval: int = 30,
    ) -> None:
        """
        Initialize the registry.

        Args:
            services: List of registered services
            health_check_interval: Health check interval in seconds
        """
        self._services: Final[dict[str, ServiceEndpoint]] = {svc.name: svc for svc in services}
        self._health: dict[str, ServiceHealth] = {}
        self._health_check_interval = health_check_interval

        logger.info(f"✅ Service Registry initialized with {len(self._services)} services")

    def get_service(self, name: str) -> ServiceEndpoint | None:
        """
        Get service info by name.
        """
        return self._services.get(name)

    def list_services(self) -> Mapping[str, ServiceEndpoint]:
        """
        List all registered services.
        """
        return self._services

    def get_health(self, name: str) -> ServiceHealth | None:
        """
        Get service health status.
        """
        return self._health.get(name)

    async def check_health(self, name: str) -> ServiceHealth:
        """
        Check health of a specific service.
        """
        service = self.get_service(name)
        if not service:
            return ServiceHealth(
                is_healthy=False,
                last_check=datetime.utcnow(),
                error_message=f"Service '{name}' not found in registry",
            )

        health_url = f"{service.base_url}{service.health_path}"
        start_time = datetime.utcnow()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                response.raise_for_status()

                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000

                health = ServiceHealth(
                    is_healthy=True,
                    last_check=end_time,
                    response_time_ms=response_time,
                )

                self._health[name] = health
                logger.debug(f"✅ Service '{name}' is healthy ({response_time:.2f}ms)")
                return health

        except Exception as exc:
            end_time = datetime.utcnow()
            health = ServiceHealth(
                is_healthy=False,
                last_check=end_time,
                error_message=str(exc),
            )

            self._health[name] = health
            logger.warning(f"❌ Service '{name}' health check failed: {exc}")
            return health

    async def check_all_health(self) -> dict[str, ServiceHealth]:
        """
        Check health of all services.
        """
        results = {}
        for name in self._services:
            results[name] = await self.check_health(name)
        return results

    def should_check_health(self, name: str) -> bool:
        """
        Determine if a service should be health-checked.
        """
        health = self._health.get(name)
        if not health:
            return True

        time_since_check = datetime.utcnow() - health.last_check
        return time_since_check > timedelta(seconds=self._health_check_interval)

    def get_healthy_services(self) -> list[str]:
        """
        Get list of healthy service names.
        """
        return [name for name, health in self._health.items() if health.is_healthy]
