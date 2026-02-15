"""
وكيل التخطيط (Planning Agent).

يوفر هذا الوكيل واجهات API مستقلة لتوليد الخطط بناءً على هدف المستخدم
مع الالتزام بالنواة الوظيفية وقشرة تنفيذية واضحة.
"""

import asyncio
import contextlib
import importlib.util
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.outbox import run_outbox_worker
from app.middleware.idempotency import IdempotencyMiddleware
from microservices.planning_agent.database import (
    async_session_factory,
    get_session,
    init_db,
)
from microservices.planning_agent.errors import setup_exception_handlers
from microservices.planning_agent.graph import graph
from microservices.planning_agent.health import HealthResponse, build_health_payload
from microservices.planning_agent.logging import get_logger, setup_logging
from microservices.planning_agent.models import Plan
from microservices.planning_agent.settings import PlanningAgentSettings, get_settings

logger = get_logger("planning-agent")


def _dspy_dependencies_available() -> bool:
    """يتحقق من توفر اعتمادات DSPy الأساسية قبل محاولة التحميل."""

    required_specs = (
        "dspy",
        "litellm",
        "openai",
        "openai.types.beta.threads.message_content",
    )
    for spec in required_specs:
        try:
            if importlib.util.find_spec(spec) is None:
                return False
        except ModuleNotFoundError:
            return False
    return True


def _load_dspy() -> object | None:
    """يحاول تحميل مكتبة DSPy إذا كانت متاحة دون تعطيل الخدمة."""

    if not _dspy_dependencies_available():
        logger.warning("مكتبة DSPy أو تبعياتها غير متاحة، سيتم تخطي التهيئة الذكية")
        return None

    return importlib.import_module("dspy")


# --- Unified Agent Protocol ---


class AgentRequest(BaseModel):
    caller_id: str
    target_service: str
    action: str
    payload: dict
    security_token: str | None = None


class AgentResponse(BaseModel):
    status: str
    data: dict | None = None
    error: str | None = None
    metrics: dict = {}


# ------------------------------


class PlanRequest(BaseModel):
    """حمولة طلب إنشاء خطة تعليمية قابلة للتفسير."""

    goal: str = Field(..., description="الهدف الرئيسي للخطة")
    context: list[str] = Field(default_factory=list, description="سياق إضافي داعم")


class PlanResponse(BaseModel):
    """استجابة توليد الخطة النهائية."""

    plan_id: UUID
    goal: str
    steps: list[str]


def _get_fallback_plan(goal: str, context: list[str]) -> list[str]:
    """توليد خطة احتياطية مخصصة عند فشل النموذج الذكي."""
    base_steps = [
        f"تحليل هدف '{goal}' وتجزئته إلى مهام فرعية قابلة للتنفيذ",
        "تحديد الموارد التعليمية والمراجع الأساسية المطلوبة",
        "إعداد جدول زمني مرن لتنفيذ الخطة خطوة بخطوة",
        "مراجعة المخرجات وتحسين الاستيعاب بناءً على التقدم",
    ]
    if context:
        base_steps.insert(2, f"تضمين السياق الإضافي ({', '.join(context)}) لتعزيز الفهم")
    return base_steps


async def _generate_plan(
    goal: str, context: list[str], settings: PlanningAgentSettings
) -> list[str]:
    """
    يولد خطة باستخدام الرسم البياني الذكي (LangGraph + DSPy).
    """

    if not settings.OPENROUTER_API_KEY:
        logger.warning("مفتاح API غير موجود، استخدام الخطة الاحتياطية")
        return _get_fallback_plan(goal, context)

    initial_state = {"goal": goal, "context": context, "iterations": 0}

    try:
        logger.info("Executing Planning Graph", extra={"goal": goal})
        # Run synchronous graph in a thread to prevent blocking the event loop
        result = await asyncio.to_thread(graph.invoke, initial_state)

        if result and "plan" in result and result["plan"]:
            return result["plan"]

        logger.warning("Graph returned no plan")
        return _get_fallback_plan(goal, context)

    except Exception as e:
        logger.error("Graph Execution Failed", extra={"error": str(e)})
        return _get_fallback_plan(goal, context)


def _build_router() -> APIRouter:
    """ينشئ موجهات الوكيل."""

    router = APIRouter()

    @router.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check(settings: PlanningAgentSettings = Depends(get_settings)) -> HealthResponse:
        """يفحص جاهزية الوكيل بشكل مستقل."""

        return build_health_payload(settings)

    @router.post(
        "/plans",
        response_model=PlanResponse,
        tags=["Planning"],
        summary="إنشاء خطة جديدة",
    )
    async def create_plan(
        payload: PlanRequest,
        session: AsyncSession = Depends(get_session),
        settings: PlanningAgentSettings = Depends(get_settings),
    ) -> PlanResponse:
        """ينشئ خطة تعليمية جديدة بناءً على الهدف والسياق ويحفظها."""

        logger.info("Start planning", extra={"goal": payload.goal})

        steps = await _generate_plan(payload.goal, payload.context, settings)

        plan = Plan(goal=payload.goal, steps=steps)
        session.add(plan)
        await session.commit()
        await session.refresh(plan)

        return PlanResponse(plan_id=plan.id, goal=plan.goal, steps=plan.steps)

    @router.get(
        "/plans",
        response_model=list[PlanResponse],
        tags=["Planning"],
        summary="عرض الخطط المحفوظة",
    )
    async def list_plans(session: AsyncSession = Depends(get_session)) -> list[PlanResponse]:
        """يعرض جميع الخطط المحفوظة."""

        statement = select(Plan)
        result = await session.execute(statement)
        plans = result.scalars().all()

        return [PlanResponse(plan_id=p.id, goal=p.goal, steps=p.steps) for p in plans]

    @router.post("/execute", response_model=AgentResponse, tags=["Agent"], include_in_schema=False)
    async def execute(
        request: AgentRequest,
        session: AsyncSession = Depends(get_session),
        settings: PlanningAgentSettings = Depends(get_settings),
    ) -> AgentResponse:
        """Unified Agent Execution Endpoint."""
        try:
            if request.action in ["generate_plan", "plan"]:
                goal = request.payload.get("goal", "")
                context = request.payload.get("context", [])

                # Use internal logic
                steps = await _generate_plan(goal, context, settings)

                # Optional: Persist
                plan = Plan(goal=goal, steps=steps)
                session.add(plan)
                await session.commit()

                return AgentResponse(status="success", data={"steps": steps})

            return AgentResponse(status="error", error=f"Action {request.action} not supported")
        except Exception as e:
            return AgentResponse(status="error", error=str(e))

    return router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """يدير دورة حياة وكيل التخطيط."""

    settings = get_settings()
    setup_logging(settings.SERVICE_NAME)

    # Configure DSPy
    if settings.OPENROUTER_API_KEY:
        dspy_module = _load_dspy()
        if dspy_module:
            try:
                lm = dspy_module.OpenAI(
                    model=settings.AI_MODEL,
                    api_key=settings.OPENROUTER_API_KEY.get_secret_value(),
                    api_base=settings.AI_BASE_URL,
                    max_tokens=2000,
                )
                dspy_module.settings.configure(lm=lm)
                logger.info("DSPy Configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure DSPy: {e}")
        else:
            logger.warning("DSPy غير متاح، سيتم الاعتماد على الخطة الاحتياطية")
    else:
        logger.warning("No API Key configured for DSPy")

    logger.info("Planning Agent Started")
    await init_db()

    # Start Outbox Worker
    worker_task = asyncio.create_task(run_outbox_worker(session_factory=async_session_factory))

    yield

    # Graceful Shutdown
    worker_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await worker_task

    logger.info("Planning Agent Stopped")


def create_app(settings: PlanningAgentSettings | None = None) -> FastAPI:
    """ينشئ تطبيق FastAPI للوكيل مع حقن الإعدادات."""

    effective_settings = settings or get_settings()

    app = FastAPI(
        title="Planning Agent",
        version=effective_settings.SERVICE_VERSION,
        description="وكيل مستقل لتوليد الخطط التعليمية (Smart Micro-service)",
        lifespan=lifespan,
    )
    setup_exception_handlers(app)

    # Register Idempotency Middleware
    app.add_middleware(IdempotencyMiddleware)

    app.include_router(_build_router())

    return app


app = create_app()
