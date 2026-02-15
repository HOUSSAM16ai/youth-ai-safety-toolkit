"""
Gateway Configuration.

Defines the gateway configuration declaratively (Data as Code).
"""

import os
from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True, slots=True)
class ServiceEndpoint:
    """
    Represents a microservice endpoint.

    Attributes:
        name: Unique service name
        base_url: Base URL of the service
        health_path: Health check path (default: /health)
        timeout: Request timeout in seconds (default: 30)
        retry_count: Number of retries (default: 3)
    """

    name: str
    base_url: str
    health_path: str = "/health"
    timeout: int = 30
    retry_count: int = 3


@dataclass(frozen=True, slots=True)
class RouteRule:
    """
    Request routing rule.

    Attributes:
        path_prefix: Path prefix to route
        service_name: Target service name
        strip_prefix: Strip prefix before routing (default: True)
        require_auth: Requires authentication (default: True)
    """

    path_prefix: str
    service_name: str
    strip_prefix: bool = True
    require_auth: bool = True


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """
    Comprehensive Gateway Configuration.
    """

    services: tuple[ServiceEndpoint, ...] = field(default_factory=tuple)
    routes: tuple[RouteRule, ...] = field(default_factory=tuple)
    enable_cors: bool = True
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 100
    jwt_secret: str | None = None


# Default Gateway Configuration for Docker Environment
DEFAULT_GATEWAY_CONFIG: Final[GatewayConfig] = GatewayConfig(
    services=(
        ServiceEndpoint(
            name="core-kernel",
            base_url=os.getenv("CORE_KERNEL_URL", "http://core-kernel:8000"),
        ),
        ServiceEndpoint(
            name="planning-agent",
            base_url=os.getenv("PLANNING_AGENT_URL", "http://planning-agent:8000"),
        ),
        ServiceEndpoint(
            name="memory-agent",
            base_url=os.getenv("MEMORY_AGENT_URL", "http://memory-agent:8000"),
        ),
        ServiceEndpoint(
            name="user-service",
            base_url=os.getenv("USER_SERVICE_URL", "http://user-service:8000"),
        ),
        ServiceEndpoint(
            name="observability-service",
            base_url=os.getenv("OBSERVABILITY_SERVICE_URL", "http://observability-service:8000"),
        ),
        ServiceEndpoint(
            name="research-agent",
            base_url=os.getenv("RESEARCH_AGENT_URL", "http://research-agent:8000"),
        ),
        ServiceEndpoint(
            name="reasoning-agent",
            base_url=os.getenv("REASONING_AGENT_URL", "http://reasoning-agent:8000"),
        ),
    ),
    routes=(
        RouteRule(
            path_prefix="/api/v1/planning",
            service_name="planning-agent",
            strip_prefix=True,
        ),
        RouteRule(
            path_prefix="/api/v1/memory",
            service_name="memory-agent",
            strip_prefix=True,
        ),
        RouteRule(
            path_prefix="/api/v1/users",
            service_name="user-service",
            strip_prefix=True,
        ),
        RouteRule(
            path_prefix="/api/v1/observability",
            service_name="observability-service",
            strip_prefix=True,
        ),
        RouteRule(
            path_prefix="/api/v1/research",
            service_name="research-agent",
            strip_prefix=True,
        ),
        RouteRule(
            path_prefix="/api/v1/reasoning",
            service_name="reasoning-agent",
            strip_prefix=True,
        ),
        # Catch-all for Core Kernel (Monolith)
        RouteRule(
            path_prefix="/",
            service_name="core-kernel",
            strip_prefix=False, # Do not strip root prefix
        ),
    ),
    enable_cors=True,
    enable_rate_limiting=True,
    max_requests_per_minute=100,
)
