import time

from fastapi import APIRouter

from microservices.reasoning_agent.src.core.logging import get_logger
from microservices.reasoning_agent.src.domain.models import AgentRequest, AgentResponse
from microservices.reasoning_agent.src.services.reasoning_service import reasoning_workflow

logger = get_logger("api-routes")
router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """
    Basic health check endpoint.
    """
    return {"status": "healthy", "service": "reasoning-agent"}

@router.post("/execute", response_model=AgentResponse, tags=["Agent"])
async def execute(request: AgentRequest) -> AgentResponse:
    """
    Unified execution endpoint for the Reasoning Agent.
    """
    start_time = time.time()
    logger.info(f"Received request from {request.caller_id}: {request.action}")

    try:
        if request.action in {"reason", "solve_deeply"}:
            query = str(request.payload.get("query", ""))
            context = str(request.payload.get("context", ""))

            if not query:
                return AgentResponse(
                    status="error",
                    error="Query is required for reasoning."
                )

            # Execute Workflow
            # Note: run is async
            result = await reasoning_workflow.run(query=query, context=context)

            duration = (time.time() - start_time) * 1000

            return AgentResponse(
                status="success",
                data={"answer": str(result)},
                metrics={"duration_ms": duration}
            )

        return AgentResponse(
            status="error",
            error=f"Action '{request.action}' not supported."
        )

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        return AgentResponse(
            status="error",
            error=str(e)
        )
