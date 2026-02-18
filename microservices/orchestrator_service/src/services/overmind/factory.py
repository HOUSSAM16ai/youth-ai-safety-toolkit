"""
مصنع العقل المدبر (Overmind Factory).

يقوم هذا المصنع بتجميع الوكيل الخارق (Super Agent) وحقن كافة التبعيات اللازمة.
يضمن هذا الملف تطبيق مبدأ انقلاب التبعية (Dependency Inversion).

المعايير:
- CS50 2025: توثيق عربي، صرامة في النوع.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.protocols import MissionStateManagerProtocol

# استيراد الأدوات (يجب ضمان وجود هذا المسار أو استخدام واجهة بديلة)
from app.services.agent_tools import get_registry
from microservices.orchestrator_service.src.core.ai_gateway import get_ai_client
from microservices.orchestrator_service.src.infrastructure.clients.auditor_client import (
    AuditorClient,
)
from microservices.orchestrator_service.src.services.overmind.agents.architect import ArchitectAgent

# from microservices.orchestrator_service.src.services.overmind.agents.auditor import AuditorAgent  # Removed: Now using Microservice
from microservices.orchestrator_service.src.services.overmind.agents.operator import OperatorAgent
from microservices.orchestrator_service.src.services.overmind.agents.strategist import (
    StrategistAgent,
)
from microservices.orchestrator_service.src.services.overmind.executor import TaskExecutor
from microservices.orchestrator_service.src.services.overmind.langgraph.context_enricher import (
    ContextEnricher,
)
from microservices.orchestrator_service.src.services.overmind.langgraph.engine import (
    LangGraphOvermindEngine,
)
from microservices.orchestrator_service.src.services.overmind.langgraph.service import (
    LangGraphAgentService,
)
from microservices.orchestrator_service.src.services.overmind.langgraph.state_manager import (
    EphemeralMissionStateManager,
)
from microservices.orchestrator_service.src.services.overmind.orchestrator import (
    OvermindOrchestrator,
)
from microservices.orchestrator_service.src.services.overmind.state import MissionStateManager

__all__ = ["create_langgraph_service", "create_overmind"]


def _build_engine_with_components(
    state_manager: MissionStateManagerProtocol,
    tool_timeout_seconds: float,
) -> tuple[LangGraphOvermindEngine, TaskExecutor]:
    """
    بناء المحرك ومكوناته الأساسية بناءً على مدير الحالة الممرر.
    """
    # 1. Execution Layer
    registry = get_registry()

    # Register Content tools dynamically to avoid circular dependency
    from app.services.chat.tools.content import register_content_tools
    from app.services.chat.tools.retrieval import search_educational_content

    register_content_tools(registry)
    registry["search_educational_content"] = search_educational_content

    # تم تحديث TaskExecutor ليقبل السجل صراحةً (Dependency Injection)
    executor = TaskExecutor(
        state_manager=state_manager,
        registry=registry,
        tool_timeout_seconds=tool_timeout_seconds,
    )

    # 2. AI Gateway
    ai_client = get_ai_client()

    # 3. The Council of Wisdom
    strategist = StrategistAgent(ai_client)
    architect = ArchitectAgent(ai_client)
    operator = OperatorAgent(executor, ai_client=ai_client)

    # Use Microservice Client (Decoupled Architecture)
    auditor = AuditorClient()

    context_enricher = ContextEnricher()

    # Initialize the LangGraph Engine
    engine = LangGraphOvermindEngine(
        strategist=strategist,
        architect=architect,
        operator=operator,
        auditor=auditor,
        context_enricher=context_enricher,
    )
    return engine, executor


async def create_overmind(db: AsyncSession) -> OvermindOrchestrator:
    """
    دالة المصنع لتجميع العقل المدبر مع مجلس الحكمة.

    Args:
        db (AsyncSession): جلسة قاعدة البيانات.

    Returns:
        OvermindOrchestrator: مثيل جاهز للعمل.
    """
    # 1. State Layer
    state_manager = MissionStateManager(db)

    # 2. Build Engine
    tool_timeout_seconds = _resolve_tool_timeout_seconds()
    engine, executor = _build_engine_with_components(state_manager, tool_timeout_seconds)

    # 3. The Orchestrator
    return OvermindOrchestrator(state_manager=state_manager, executor=executor, brain=engine)


def create_langgraph_service(db: AsyncSession | None = None) -> LangGraphAgentService:
    """
    دالة مصنع لإنشاء خدمة LangGraphAgentService مع كافة الاعتماديات محقونة.

    Args:
        db (AsyncSession | None): جلسة قاعدة البيانات (اختياري).
                                 في حالة عدم التوفير، يتم استخدام مدير حالة مؤقت.

    Returns:
        LangGraphAgentService: الخدمة جاهزة للاستخدام.
    """
    state_manager = MissionStateManager(db) if db else EphemeralMissionStateManager()

    tool_timeout_seconds = _resolve_tool_timeout_seconds()
    engine, _ = _build_engine_with_components(state_manager, tool_timeout_seconds)
    return LangGraphAgentService(engine=engine)


def _resolve_tool_timeout_seconds() -> float:
    """
    قراءة الحد الزمني لتنفيذ الأدوات من متغيرات البيئة مع ضبط الحدود.
    """
    raw = os.environ.get("OVERMIND_TOOL_TIMEOUT_SECONDS", "60")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 60.0
    if value <= 0:
        return 60.0
    return min(value, 300.0)
