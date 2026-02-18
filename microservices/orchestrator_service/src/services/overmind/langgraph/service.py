from __future__ import annotations

import uuid

from microservices.orchestrator_service.src.services.overmind.domain.api_schemas import (
    LangGraphRunData,
    LangGraphRunRequest,
)
from microservices.orchestrator_service.src.services.overmind.langgraph.engine import (
    LangGraphOvermindEngine,
)


class LangGraphAgentService:
    """
    خدمة تشغيل LangGraph للوكلاء المتعددين.

    تقوم هذه الخدمة بتشغيل محرك LangGraph متسق مع
    مبادئ API First وبنية الخدمات المصغرة.
    """

    def __init__(self, *, engine: LangGraphOvermindEngine) -> None:
        """
        تهيئة الخدمة عبر حقن المحرك (Dependency Injection).
        """
        self.engine = engine

    async def run(self, payload: LangGraphRunRequest) -> LangGraphRunData:
        """
        تشغيل LangGraph وإرجاع بيانات التشغيل.
        """
        run_id = str(uuid.uuid4())
        result = await self.engine.run(
            run_id=run_id,
            objective=payload.objective,
            context=payload.context,
            constraints=payload.constraints,
            priority=payload.priority.value,
        )
        state = result.state
        return LangGraphRunData(
            run_id=run_id,
            objective=payload.objective,
            plan=state.get("plan"),
            design=state.get("design"),
            execution=state.get("execution"),
            audit=state.get("audit"),
            timeline=state.get("timeline", []),
        )
