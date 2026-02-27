"""
خدمة تخطيط الوكلاء (Agent Plan Service).
---------------------------------------
تنفذ هذه الخدمة منطق توليد الخطط وتطبيعها للاستهلاك عبر API،
مع فصل واضح بين المنطق المعرفي وعرض البيانات.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.ai_gateway import get_ai_client
from app.core.di import get_logger
from app.services.overmind.agents.strategist import StrategistAgent
from app.services.overmind.domain.api_schemas import (
    AgentPlanData,
    AgentPlanStepResponse,
    AgentsPlanRequest,
)
from app.services.overmind.domain.context import InMemoryCollaborationContext
from app.services.overmind.plan_registry import AgentPlanRecord

logger = get_logger(__name__)


class AgentPlanService:
    """
    منسق توليد خطط الوكلاء.

    يعتمد على وكيل الاستراتيجي لتوليد خطة أولية ثم يحولها إلى نموذج
    استجابة متوافق مع العقد.
    """

    def __init__(self, strategist: StrategistAgent | None = None) -> None:
        self._strategist = strategist or StrategistAgent(get_ai_client())

    async def create_plan(self, payload: AgentsPlanRequest) -> AgentPlanRecord:
        """
        إنشاء خطة وكيل جديدة.

        Args:
            payload: بيانات الطلب الواردة من API.

        Returns:
            AgentPlanRecord: السجل النهائي للخطة.
        """
        collab_context = self._build_collaboration_context(payload)

        plan_payload = await self._strategist.create_plan(payload.objective, collab_context)
        steps = self._normalize_steps(plan_payload)

        plan_id = f"plan_{uuid4().hex}"
        created_at = datetime.now(UTC)

        logger.info("Agent plan created", extra={"plan_id": plan_id})

        plan_data = self._build_plan_data(
            plan_id=plan_id,
            objective=payload.objective,
            steps=steps,
            created_at=created_at,
        )

        return AgentPlanRecord(data=plan_data)

    def _build_collaboration_context(
        self,
        payload: AgentsPlanRequest,
    ) -> InMemoryCollaborationContext:
        """
        بناء سياق التعاون بشكل صريح.

        Args:
            payload: بيانات الطلب الواردة من API.

        Returns:
            InMemoryCollaborationContext: سياق التعاون المجهز.
        """
        collab_context = InMemoryCollaborationContext(payload.context)
        collab_context.update("constraints", payload.constraints)
        collab_context.update("priority", payload.priority.value)
        return collab_context

    def _build_plan_data(
        self,
        *,
        plan_id: str,
        objective: str,
        steps: list[AgentPlanStepResponse],
        created_at: datetime,
    ) -> AgentPlanData:
        """
        بناء بيانات الخطة النهائية القابلة للإرجاع.

        Args:
            plan_id: معرف الخطة.
            objective: الهدف المطلوب.
            steps: الخطوات المطابقة للعقد.
            created_at: وقت الإنشاء.

        Returns:
            AgentPlanData: بيانات الخطة المهيكلة.
        """
        return AgentPlanData(
            plan_id=plan_id,
            objective=objective,
            steps=steps,
            created_at=created_at,
        )

    def _normalize_steps(self, plan_data: dict[str, object]) -> list[AgentPlanStepResponse]:
        """
        تطبيع خطوات الخطة القادمة من وكيل الاستراتيجي.

        Args:
            plan_data: البيانات الخام من نموذج الذكاء الاصطناعي.

        Returns:
            list[AgentPlanStepResponse]: خطوات منظمة وفق العقد.
        """
        raw_steps = _coerce_steps_list(plan_data.get("steps"))
        return [
            _build_step_response(step, index)
            for index, step in enumerate(_iter_step_dicts(raw_steps), start=1)
        ]


def _coerce_steps_list(raw_steps: object) -> list[object]:
    """يضمن تحويل الخطوات إلى قائمة قابلة للتكرار."""

    return raw_steps if isinstance(raw_steps, list) else []


def _iter_step_dicts(raw_steps: list[object]) -> list[dict[str, object]]:
    """يعيد فقط العناصر التي تمثل قواميس للخطوات."""

    return [step for step in raw_steps if isinstance(step, dict)]


def _build_step_response(step: dict[str, object], index: int) -> AgentPlanStepResponse:
    """يبني استجابة خطوة منظمة انطلاقاً من البيانات الخام."""

    return AgentPlanStepResponse(
        step_id=f"step-{index:02d}",
        title=_get_step_title(step, index),
        description=_get_step_description(step),
        dependencies=_get_step_dependencies(step),
        estimated_effort=_get_step_effort(step),
    )


def _get_step_title(step: dict[str, object], index: int) -> str:
    """تستخلص عنوان الخطوة مع قيمة احتياطية واضحة."""

    name = step.get("name") or step.get("title") or f"Step {index}"
    return str(name)


def _get_step_description(step: dict[str, object]) -> str:
    """تستخلص وصف الخطوة بشكل آمن."""

    return str(step.get("description") or "")


def _get_step_dependencies(step: dict[str, object]) -> list[str]:
    """تطبع تبعيات الخطوة وتحولها إلى قائمة نصوص."""

    dependencies = step.get("dependencies") or []
    if not isinstance(dependencies, list):
        dependencies = [dependencies]
    return [str(dep) for dep in dependencies]


def _get_step_effort(step: dict[str, object]) -> str | None:
    """تستخرج تقدير الجهد بصيغة نصية قابلة للإرجاع."""

    estimated_effort = step.get("estimated_effort") or step.get("effort")
    return str(estimated_effort) if estimated_effort is not None else None
