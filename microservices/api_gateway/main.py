import uvicorn
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import logging

# Local imports
from microservices.api_gateway.config import settings
from microservices.api_gateway.proxy import GatewayProxy

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

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-gateway"}

# --- Smart Routing ---

@app.api_route("/api/v1/planning/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def planning_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.PLANNING_AGENT_URL, path)

@app.api_route("/api/v1/memory/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def memory_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.MEMORY_AGENT_URL, path)

@app.api_route("/api/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def user_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.USER_SERVICE_URL, path)

@app.api_route("/api/v1/observability/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def observability_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.OBSERVABILITY_SERVICE_URL, path)

@app.api_route("/api/v1/research/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def research_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.RESEARCH_AGENT_URL, path)

@app.api_route("/api/v1/reasoning/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def reasoning_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.REASONING_AGENT_URL, path)

# Catch-all for Core Kernel (Legacy Monolith)
# This must be defined last to act as a fallback
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def core_kernel_proxy(path: str, request: Request):
    return await proxy_handler.forward(request, settings.CORE_KERNEL_URL, path)


if __name__ == "__main__":
    uvicorn.run("microservices.api_gateway.main:app", host="0.0.0.0", port=8000, reload=True)
