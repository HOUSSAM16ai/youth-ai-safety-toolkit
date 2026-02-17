import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import StreamingResponse

# Local imports
from microservices.api_gateway.config import settings
from microservices.api_gateway.middleware import RequestIdMiddleware, StructuredLoggingMiddleware
from microservices.api_gateway.proxy import GatewayProxy
from microservices.api_gateway.security import create_service_token, verify_gateway_request

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


if __name__ == "__main__":
    uvicorn.run("microservices.api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
