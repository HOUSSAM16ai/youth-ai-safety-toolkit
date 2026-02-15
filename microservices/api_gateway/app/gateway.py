"""
Central API Gateway Logic.

Implements the routing and proxying logic for the microservices architecture.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, status

from .config import GatewayConfig, RouteRule
from .registry import ServiceRegistry

logger = logging.getLogger("api-gateway")


class APIGateway:
    """
    Central API Gateway.

    Principles:
    - Smart Routing: Routes requests based on configuration
    - API-First: Everything is an API
    - Resilience: Retries and timeouts
    """

    def __init__(
        self,
        config: GatewayConfig,
        registry: ServiceRegistry | None = None,
    ) -> None:
        """
        Initialize the gateway.

        Args:
            config: Gateway configuration
            registry: Service registry (optional)
        """
        self.config = config
        self.registry = registry or ServiceRegistry(services=config.services)
        self.router = self._build_router()

        logger.info("✅ API Gateway initialized")

    def _build_router(self) -> APIRouter:
        """
        Builds the main router with dynamic routes.
        """
        router = APIRouter()

        @router.get("/health")
        async def gateway_health() -> dict[str, object]:
            """Check gateway and services health."""
            services_health = await self.registry.check_all_health()

            healthy_count = sum(1 for h in services_health.values() if h.is_healthy)
            total_count = len(services_health)

            return {
                "gateway": "healthy",
                "services": {
                    name: {
                        "healthy": health.is_healthy,
                        "response_time_ms": health.response_time_ms,
                        "last_check": health.last_check.isoformat(),
                        "error": health.error_message,
                    }
                    for name, health in services_health.items()
                },
                "summary": {
                    "healthy": healthy_count,
                    "total": total_count,
                    "percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
                },
            }

        @router.get("/services")
        async def list_services() -> dict[str, object]:
            """List all registered services."""
            services = self.registry.list_services()
            return {
                "services": [
                    {
                        "name": svc.name,
                        "base_url": svc.base_url,
                        "health_path": svc.health_path,
                        "timeout": svc.timeout,
                    }
                    for svc in services.values()
                ],
                "count": len(services),
            }

        # Register Routes from Config
        for route in self.config.routes:
            self._add_route(router, route)

        return router

    def _add_route(self, router: APIRouter, route: RouteRule) -> None:
        """
        Adds a route handler for a specific rule.
        """
        # Define the handler function
        async def route_handler(request: Request, path: str = "") -> Response:
            return await self._proxy_request(route, path, request)

        # Generate a unique name for the handler
        route_name = f"proxy_{route.service_name}_{route.path_prefix.replace('/', '_')}"
        route_handler.__name__ = route_name

        # Construct the path pattern
        if route.path_prefix == "/":
            # Catch-all root
            router.add_api_route(
                "/{path:path}",
                route_handler,
                methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
                include_in_schema=False, # Hide catch-all from root schema to avoid clutter
            )
        else:
            # Specific prefix
            # 1. Match /prefix/{path}
            router.add_api_route(
                f"{route.path_prefix}/{{path:path}}",
                route_handler,
                methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
                include_in_schema=True,
                tags=[route.service_name]
            )

            # 2. Match /prefix (exact match)
            # We create a wrapper to pass empty path
            async def route_handler_root(request: Request) -> Response:
                return await self._proxy_request(route, "", request)

            route_handler_root.__name__ = f"{route_name}_root"

            router.add_api_route(
                route.path_prefix,
                route_handler_root,
                methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
                include_in_schema=True,
                tags=[route.service_name]
            )

    async def _proxy_request(
        self,
        route: RouteRule,
        path: str,
        request: Request,
    ) -> Response:
        """
        Proxies the request to the target service.
        """
        service_name = route.service_name
        service = self.registry.get_service(service_name)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found",
            )

        # Construct Target URL
        # If strip_prefix is True: target = base_url / path
        # If strip_prefix is False: target = base_url / route_prefix / path

        if route.strip_prefix:
            final_path = path
        elif route.path_prefix == "/":
            # If we don't strip, we append the original prefix
            # Note: path captures only the suffix.
            final_path = path
        else:
            final_path = f"{route.path_prefix.lstrip('/')}/{path}"

        # Clean up double slashes just in case
        final_path = final_path.lstrip("/")
        target_url = f"{service.base_url}/{final_path}"

        # Headers & Body
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None)

        query_params = dict(request.query_params)
        body = await request.body()

        # Retry Logic
        last_error = None
        for attempt in range(service.retry_count):
            try:
                async with httpx.AsyncClient(timeout=service.timeout) as client:
                    response = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        params=query_params,
                        content=body,
                    )

                    return Response(
                        content=response.content,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.headers.get("content-type"),
                    )

            except httpx.TimeoutException:
                last_error = f"Timeout after {service.timeout}s"
                logger.warning(
                    f"⚠️ Timeout proxying to {service_name} (attempt {attempt + 1}/{service.retry_count})"
                )

            except httpx.RequestError as exc:
                last_error = str(exc)
                logger.warning(
                    f"⚠️ Error proxying to {service_name}: {exc} (attempt {attempt + 1}/{service.retry_count})"
                )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to proxy request to '{service_name}': {last_error}",
        )
