"""
وكيل الذاكرة (Memory Agent).

يدير هذا الوكيل تخزين واسترجاع السياق محلياً مع الالتزام
بمبدأ العزل وعدم مشاركة قاعدة بيانات مركزية.

المبادئ المطبقة:
- SOLID: Single Responsibility Principle (طبقات منفصلة)
- SOLID: Dependency Inversion Principle (حقن التبعيات)
- Clean Architecture: فصل الطبقات
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Query
from sqlalchemy.ext.asyncio import AsyncSession

from microservices.memory_agent.database import get_session, init_db
from microservices.memory_agent.errors import setup_exception_handlers
from microservices.memory_agent.health import HealthResponse, build_health_payload
from microservices.memory_agent.logging import get_logger, setup_logging
from microservices.memory_agent.security import verify_service_token
from microservices.memory_agent.settings import MemoryAgentSettings, get_settings

# استيراد الطبقات الجديدة (SOLID Refactoring)
from microservices.memory_agent.src.repositories.memory_repository import (
    MemoryRepository,
)
from microservices.memory_agent.src.schemas.memory_schemas import (
    MemoryCreateRequest,
    MemoryResponse,
    MemorySearchRequest,
)
from microservices.memory_agent.src.services.memory_service import MemoryService
from microservices.memory_agent.src.api.knowledge import router as knowledge_router

logger = get_logger("memory-agent")


def _build_public_router(settings: MemoryAgentSettings) -> APIRouter:
    """ينشئ موجهات الوكيل العامة."""
    router = APIRouter()

    @router.get("/health", response_model=HealthResponse, tags=["System"])
    def health_check() -> HealthResponse:
        """يفحص جاهزية الوكيل دون اعتماد خارجي."""

        return build_health_payload(settings)

    return router


def _build_protected_router() -> APIRouter:
    """ينشئ موجهات الوكيل المحمية."""
    router = APIRouter()

    @router.post(
        "/memories",
        response_model=MemoryResponse,
        tags=["Memory"],
        summary="إنشاء عنصر ذاكرة",
    )
    async def create_memory(
        payload: MemoryCreateRequest, session: AsyncSession = Depends(get_session)
    ) -> MemoryResponse:
        """ينشئ عنصر ذاكرة جديد ويعيده."""
        # استخدام طبقة Service (SOLID: SRP + DIP)
        repository = MemoryRepository(session)
        service = MemoryService(repository)
        return await service.create_memory(payload)

    @router.get(
        "/memories/search",
        response_model=list[MemoryResponse],
        tags=["Memory"],
        summary="بحث عبر الاستعلام النصي",
    )
    async def search_memories(
        query: str = Query(default="", description="نص البحث"),
        limit: int = Query(default=10, ge=1, le=50, description="حد النتائج"),
        session: AsyncSession = Depends(get_session),
    ) -> list[MemoryResponse]:
        """
        يبحث عن عناصر ذاكرة مطابقة للاستعلام.
        يتم البحث في المحتوى والوسوم باستخدام قاعدة البيانات.
        """
        # استخدام طبقة Service (SOLID: SRP + DIP)
        repository = MemoryRepository(session)
        service = MemoryService(repository)
        return await service.search_memories(query, limit)

    @router.post(
        "/memories/search",
        response_model=list[MemoryResponse],
        tags=["Memory"],
        summary="بحث عبر حمولة موسعة",
    )
    async def search_memories_post(
        payload: MemorySearchRequest, session: AsyncSession = Depends(get_session)
    ) -> list[MemoryResponse]:
        """
        يبحث عن عناصر ذاكرة مع دعم مرشحات الوسوم عبر POST.
        """
        # استخدام طبقة Service (SOLID: SRP + DIP)
        repository = MemoryRepository(session)
        service = MemoryService(repository)
        return await service.search_memories_with_filters(payload)

    return router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """يدير دورة حياة التطبيق لوكيل الذاكرة."""

    setup_logging(get_settings().SERVICE_NAME)
    logger.info("بدء تشغيل وكيل الذاكرة")
    await init_db()
    yield
    logger.info("إيقاف وكيل الذاكرة")


def create_app(settings: MemoryAgentSettings | None = None) -> FastAPI:
    """يبني تطبيق FastAPI للوكيل مع مخزن ذاكرة مستقل."""

    effective_settings = settings or get_settings()

    app = FastAPI(
        title="Memory Agent",
        version=effective_settings.SERVICE_VERSION,
        description="وكيل مستقل لإدارة السياق والذاكرة",
        lifespan=lifespan,
    )
    setup_exception_handlers(app)

    # تطبيق Zero Trust: التحقق من الهوية عند البوابة
    app.include_router(_build_public_router(effective_settings))
    app.include_router(_build_protected_router(), dependencies=[Depends(verify_service_token)])
    app.include_router(knowledge_router, dependencies=[Depends(verify_service_token)])

    return app


app = create_app()
