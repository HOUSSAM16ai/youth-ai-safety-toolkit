"""
وكيل الاستدلال (Reasoning Agent).

هذه الخدمة مسؤولة عن تنفيذ عمليات التفكير المنطقي المعقدة (Deep Reasoning)
باستخدام استراتيجيات شجرة الأفكار (Tree of Thought) وغيرها.
"""

import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

# Integration with internal logic
from microservices.reasoning_agent.src.ai_client import SimpleAIClient
from microservices.reasoning_agent.src.workflow import SuperReasoningWorkflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    """يدير دورة حياة وكيل الاستدلال."""
    print("🚀 Reasoning Agent Started")
    # Warmup or checks could go here
    yield
    print("🛑 Reasoning Agent Stopped")


# --- Unified Agent Protocol ---


class AgentRequest(BaseModel):
    """
    طلب تنفيذ إجراء موحد.
    """

    caller_id: str = Field(..., description="Entity requesting the action")
    target_service: str = Field("reasoning_agent", description="Target service name")
    action: str = Field(..., description="Action to perform (e.g., 'reason')")
    payload: dict[str, object] = Field(default_factory=dict, description="Action arguments")
    security_token: str | None = Field(None, description="Auth token")


class AgentResponse(BaseModel):
    """
    استجابة موحدة للوكيل.
    """

    status: str = Field(..., description="'success' or 'error'")
    data: object | None = Field(None, description="Result data")
    error: str | None = Field(None, description="Error message")
    metrics: dict[str, object] = Field(default_factory=dict, description="Performance metrics")


# ------------------------------


def _build_router() -> APIRouter:
    """بناء موجهات الخدمة."""
    router = APIRouter()

    @router.get("/health", tags=["System"])
    def health_check() -> dict[str, str]:
        """فحص الحالة."""
        return {"status": "healthy", "service": "reasoning-agent"}

    @router.post("/execute", response_model=AgentResponse, tags=["Agent"])
    async def execute(request: AgentRequest) -> AgentResponse:
        """
        نقطة الدخول الموحدة لتنفيذ الأوامر (Unified Execution Endpoint).
        """
        start_time = time.time()
        try:
            # Dispatch Logic
            if request.action in {"reason", "solve_deeply"}:
                # Extract parameters
                query = request.payload.get("query", "")
                if not query:
                    return AgentResponse(status="error", error="Query is required for reasoning.")

                # Initialize Components
                ai_client = SimpleAIClient()
                # We can inject specific strategies here if payload requests them
                workflow = SuperReasoningWorkflow(client=ai_client, timeout=300)

                # Execute Workflow
                result = await workflow.run(query=query)

                duration = (time.time() - start_time) * 1000

                # Result is usually a string (content) from StopEvent
                # But workflow.run returns the result of the last step.
                # In SuperReasoningWorkflow: return StopEvent(result=content)
                # So result should be content string.

                result_data = {
                    "answer": str(result),
                    "logic_trace": [
                        "Executed R-MCTS Workflow"
                    ],  # Full trace requires capturing events
                }

                return AgentResponse(
                    status="success", data=result_data, metrics={"duration_ms": duration}
                )

            return AgentResponse(
                status="error", error=f"Action '{request.action}' not supported by Reasoning Agent."
            )

        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    return router


def create_app() -> FastAPI:
    """إنشاء تطبيق FastAPI لوكيل الاستدلال."""
    app = FastAPI(
        title="Reasoning Agent",
        description="خدمة مخصصة للاستدلال المنطقي العميق (Microservice)",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(_build_router())
    return app


app = create_app()
