import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse

# Local imports
from microservices.api_gateway.config import settings
from microservices.api_gateway.middleware import RequestIdMiddleware, StructuredLoggingMiddleware
from microservices.api_gateway.proxy import GatewayProxy
from microservices.api_gateway.security import create_service_token, verify_gateway_request
from microservices.api_gateway.websockets import websocket_proxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

# Initialize the proxy handler
proxy_handler = GatewayProxy()


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


# --- Explicit Legacy Routes ---


@app.api_route(
    "/admin/ai-config",
    methods=["GET", "PUT", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def admin_ai_config_proxy(request: Request) -> StreamingResponse:
    """
    Strangler Fig: Route AI Config to Monolith.
    This feature has not been migrated to User Service yet.
    """
    return await proxy_handler.forward(request, settings.CORE_KERNEL_URL, "api/v1/admin/ai-config")


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
)
async def chat_http_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(request, settings.CORE_KERNEL_URL, f"api/chat/{path}")


@app.websocket("/api/chat/ws")
async def chat_ws_proxy(websocket: WebSocket):
    """
    Proxy for Customer Chat WebSocket.
    """
    target_url = settings.CORE_KERNEL_URL.replace("http", "ws") + "/api/chat/ws"
    await websocket_proxy(websocket, target_url)


@app.websocket("/admin/api/chat/ws")
async def admin_chat_ws_proxy(websocket: WebSocket):
    """
    Proxy for Admin Chat WebSocket.
    """
    target_url = settings.CORE_KERNEL_URL.replace("http", "ws") + "/admin/api/chat/ws"
    await websocket_proxy(websocket, target_url)


@app.api_route(
    "/v1/content/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def content_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(request, settings.CORE_KERNEL_URL, f"v1/content/{path}")


@app.api_route(
    "/api/v1/data-mesh/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def datamesh_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(
        request, settings.CORE_KERNEL_URL, f"api/v1/data-mesh/{path}"
    )


@app.api_route(
    "/system/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def system_proxy(path: str, request: Request) -> StreamingResponse:
    return await proxy_handler.forward(request, settings.CORE_KERNEL_URL, f"system/{path}")




if __name__ == "__main__":
    uvicorn.run("microservices.api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
