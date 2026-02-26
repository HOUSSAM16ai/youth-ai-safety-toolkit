import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse

# Local imports
from microservices.api_gateway.config import settings
from microservices.api_gateway.legacy_acl import LegacyACL
from microservices.api_gateway.middleware import (
    RequestIdMiddleware,
    StructuredLoggingMiddleware,
    TraceContextMiddleware,
)
from microservices.api_gateway.proxy import GatewayProxy
from microservices.api_gateway.security import create_service_token, verify_gateway_request
from microservices.api_gateway.websockets import websocket_proxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

# Initialize the proxy handler
proxy_handler = GatewayProxy()
legacy_acl = LegacyACL(proxy_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    logger.info("Starting API Gateway...")
    yield
    logger.info("Shutting down API Gateway...")
    await proxy_handler.close()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Add Middleware
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TraceContextMiddleware)


@app.get("/health")
async def health_check():
    """
    Health check endpoint that verifies connectivity to downstream services.
    Returns a detailed status report.
    """
    services = {
        "planning_agent": settings.PLANNING_AGENT_URL,
        "memory_agent": settings.MEMORY_AGENT_URL,
        "user_service": settings.USER_SERVICE_URL,
        "observability_service": settings.OBSERVABILITY_SERVICE_URL,
        "research_agent": settings.RESEARCH_AGENT_URL,
        "reasoning_agent": settings.REASONING_AGENT_URL,
        "orchestrator_service": settings.ORCHESTRATOR_SERVICE_URL,
    }

    async def check_service(name: str, url: str):
        try:
            # Short timeout for health checks
            resp = await proxy_handler.client.get(f"{url}/health", timeout=2.0)
            status = "UP" if resp.status_code == 200 else f"DOWN ({resp.status_code})"
            return name, status
        except Exception as e:
            return name, f"DOWN ({e!s})"

    # Run checks concurrently
    results = await asyncio.gather(*(check_service(name, url) for name, url in services.items()))
    dependencies = dict(results)

    # Determine overall status
    overall_status = "ok"
    if any(s.startswith("DOWN") for s in dependencies.values()):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": "api-gateway",
        "dependencies": dependencies,
    }


@app.get("/gateway/health")
async def gateway_health_check():
    """
    Alias for /health.
    Matches legacy documentation expectations.
    """
    return await health_check()


# --- Smart Routing ---


@app.api_route(
    "/api/v1/planning/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def planning_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.PLANNING_AGENT_URL, path, service_token=create_service_token()
    )


@app.api_route(
    "/api/v1/memory/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def memory_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.MEMORY_AGENT_URL, path, service_token=create_service_token()
    )


@app.api_route(
    "/api/v1/users/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def user_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.USER_SERVICE_URL, path, service_token=create_service_token()
    )


@app.api_route(
    "/api/v1/auth/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def auth_proxy(path: str, request: Request) -> StreamingResponse:
    """
    Proxy Auth routes (Login/Register) to User Service.
    Resolves ambiguity between Monolith UMS and Microservice.
    """
    return await proxy_handler.forward(
        request,
        settings.USER_SERVICE_URL,
        f"api/v1/auth/{path}",
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/v1/observability/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def observability_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request,
        settings.OBSERVABILITY_SERVICE_URL,
        path,
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/v1/research/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def research_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.RESEARCH_AGENT_URL, path, service_token=create_service_token()
    )


@app.api_route(
    "/api/v1/reasoning/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def reasoning_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.REASONING_AGENT_URL, path, service_token=create_service_token()
    )


@app.api_route(
    "/api/v1/overmind/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def orchestrator_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request,
        settings.ORCHESTRATOR_SERVICE_URL,
        path,
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/v1/missions",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def missions_root_proxy(request: Request) -> StreamingResponse:
    """
    Strangler Fig: Route missions root to Orchestrator Service.
    Decouples mission control from the Monolith.
    """
    return await proxy_handler.forward(
        request,
        settings.ORCHESTRATOR_SERVICE_URL,
        "missions",
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/v1/missions/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    dependencies=[Depends(verify_gateway_request)],
)
async def missions_path_proxy(path: str, request: Request) -> StreamingResponse:
    """
    Strangler Fig: Route missions paths to Orchestrator Service.
    """
    return await proxy_handler.forward(
        request,
        settings.ORCHESTRATOR_SERVICE_URL,
        f"missions/{path}",
        service_token=create_service_token(),
    )


# --- LEGACY MONOLITH ROUTES (STRANGLER PATTERN) ---
# These routes are explicitly mapped to the Core Kernel (Monolith).
# They are marked as deprecated and logged for future extraction.
# Governance: New routes MUST NOT be added here without exception approval.


@app.api_route(
    "/admin/ai-config",
    methods=["GET", "PUT", "OPTIONS", "HEAD"],
    include_in_schema=False,
    deprecated=True,
)
async def admin_ai_config_proxy(request: Request) -> StreamingResponse:
    """
    [LEGACY] Strangler Fig: Route AI Config to Monolith.
    TARGET: User Service (Pending Migration)
    """
    logger.warning("Legacy route accessed: /admin/ai-config")
    if settings.ROUTE_ADMIN_AI_CONFIG_USE_LEGACY:
        return await legacy_acl.forward_http(request, "api/v1/admin/ai-config", "admin_ai_config")
    return await proxy_handler.forward(
        request,
        settings.USER_SERVICE_URL,
        "api/v1/admin/ai-config",
        service_token=create_service_token(),
    )


@app.api_route(
    "/admin/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def admin_proxy(path: str, request: Request) -> StreamingResponse:
    """
    Proxy Admin routes to User Service (UMS).
    Rewrite: /admin/{path} -> /api/v1/admin/{path}
    """
    # This is NOT legacy monolith, it points to USER_SERVICE.
    return await proxy_handler.forward(
        request,
        settings.USER_SERVICE_URL,
        f"api/v1/admin/{path}",
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/security/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def security_proxy(path: str, request: Request) -> StreamingResponse:
    """
    Proxy Security routes to User Service (Auth).
    Rewrite: /api/security/{path} -> /api/v1/auth/{path}
    """
    # This is NOT legacy monolith, it points to USER_SERVICE.
    return await proxy_handler.forward(
        request,
        settings.USER_SERVICE_URL,
        f"api/v1/auth/{path}",
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/chat/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
    deprecated=True,
)
async def chat_http_proxy(path: str, request: Request) -> StreamingResponse:
    """
    [LEGACY] HTTP Chat Proxy.
    TARGET: Orchestrator Service / Conversation Service
    """
    logger.warning("Legacy route accessed: /api/chat/%s", path)
    if settings.ROUTE_CHAT_USE_LEGACY:
        return await legacy_acl.forward_http(
            request, legacy_acl.chat_upstream_path(path), "chat_http"
        )
    return await proxy_handler.forward(
        request,
        settings.ORCHESTRATOR_SERVICE_URL,
        f"api/chat/{path}",
        service_token=create_service_token(),
    )


@app.websocket("/api/chat/ws")
async def chat_ws_proxy(websocket: WebSocket):
    """
    [LEGACY] Customer Chat WebSocket.
    TARGET: Orchestrator Service / Conversation Service
    """
    logger.warning("Legacy WebSocket accessed: /api/chat/ws")
    target_url = legacy_acl.websocket_target("api/chat/ws", "chat_ws_customer")
    await websocket_proxy(websocket, target_url)


@app.websocket("/admin/api/chat/ws")
async def admin_chat_ws_proxy(websocket: WebSocket):
    """
    [LEGACY] Admin Chat WebSocket.
    TARGET: Orchestrator Service / Conversation Service
    """
    logger.warning("Legacy WebSocket accessed: /admin/api/chat/ws")
    target_url = legacy_acl.websocket_target("admin/api/chat/ws", "chat_ws_admin")
    await websocket_proxy(websocket, target_url)


@app.api_route(
    "/v1/content/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
    deprecated=True,
)
async def content_proxy(path: str, request: Request) -> StreamingResponse:
    """
    [LEGACY] Content Service Proxy.
    TARGET: Content Service (To Be Extracted)
    """
    logger.warning("Legacy route accessed: /v1/content/%s", path)
    if settings.ROUTE_CONTENT_USE_LEGACY:
        return await legacy_acl.forward_http(
            request, legacy_acl.content_upstream_path(path), "content"
        )
    return await proxy_handler.forward(
        request,
        settings.RESEARCH_AGENT_URL,
        f"v1/content/{path}",
        service_token=create_service_token(),
    )


@app.api_route(
    "/api/v1/data-mesh/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
    deprecated=True,
)
async def datamesh_proxy(path: str, request: Request) -> StreamingResponse:
    """
    [LEGACY] Data Mesh Proxy.
    TARGET: Data Mesh Service
    """
    logger.warning("Legacy route accessed: /api/v1/data-mesh/%s", path)
    if settings.ROUTE_DATAMESH_USE_LEGACY:
        return await legacy_acl.forward_http(request, f"api/v1/data-mesh/{path}", "data_mesh")
    return await proxy_handler.forward(
        request,
        settings.OBSERVABILITY_SERVICE_URL,
        f"api/v1/data-mesh/{path}",
        service_token=create_service_token(),
    )


@app.api_route(
    "/system/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
    deprecated=True,
)
async def system_proxy(path: str, request: Request) -> StreamingResponse:
    """
    [LEGACY] System Routes Proxy.
    TARGET: System Service
    """
    logger.warning("Legacy route accessed: /system/%s", path)
    if settings.ROUTE_SYSTEM_USE_LEGACY:
        return await legacy_acl.forward_http(request, f"system/{path}", "system")
    return await proxy_handler.forward(
        request,
        settings.ORCHESTRATOR_SERVICE_URL,
        f"system/{path}",
        service_token=create_service_token(),
    )


if __name__ == "__main__":
    uvicorn.run("microservices.api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
