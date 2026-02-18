# app/services/overmind/domain/cognitive.py
"""
الدماغ الخارق (SuperBrain) - المجال المعرفي للعقل المدبر.
---------------------------------------------------------
يحدد هذا الملف البنية المعرفية عالية المستوى للوكيل الخارق.
يقوم بتنسيق "مجلس الحكمة" باستخدام نمط الاستراتيجية (Strategy Pattern)
لحل المشكلات المعقدة باستقلالية تامة وتصحيح ذاتي.

المعايير:
- CS50 2025 Strict Mode.
- توثيق "Legendary" باللغة العربية.
- استخدام بروتوكولات صارمة.
- MIT 6.0001: التجريد والخوارزميات (Abstraction & Algorithms).
"""

import logging
import re
from collections.abc import Awaitable, Callable

from microservices.orchestrator_service.src.core.protocols import (
    AgentArchitect,
    AgentExecutor,
    AgentMemory,
    AgentPlanner,
    AgentReflector,
)
from microservices.orchestrator_service.src.models.mission import Mission
from microservices.orchestrator_service.src.services.overmind.collaboration import CollaborationHub
from microservices.orchestrator_service.src.services.overmind.domain.context import (
    InMemoryCollaborationContext,
)
from microservices.orchestrator_service.src.services.overmind.domain.council_session import (
    CouncilSession,
)
from microservices.orchestrator_service.src.services.overmind.domain.enums import (
    CognitiveEvent,
    CognitivePhase,
)
from microservices.orchestrator_service.src.services.overmind.domain.exceptions import (
    StalemateError,
)
from microservices.orchestrator_service.src.services.overmind.domain.phase_runner import (
    CognitivePhaseRunner,
)
from microservices.orchestrator_service.src.services.overmind.domain.phases import (
    DesignPhase,
    ExecutionPhase,
    PlanningPhase,
    ReflectionPhase,
)
from microservices.orchestrator_service.src.services.overmind.domain.primitives import (
    CognitiveState,
    EventLogger,
)
from microservices.orchestrator_service.src.services.tools.retrieval import (
    search_educational_content,
)

logger = logging.getLogger(__name__)


class SuperBrain:
    """
    المعالج المعرفي المركزي (The Central Cognitive Processor).

    ينسق الوكلاء في حلقة "مجلس الحكمة" باستخدام استراتيجيات محددة لكل مرحلة:
    1. الاستراتيجي (Strategist): تخطيط.
    2. المعماري (Architect): تصميم.
    3. المنفذ (Operator): تنفيذ.
    4. المدقق (Auditor): مراجعة.
    """

    def __init__(
        self,
        strategist: AgentPlanner,
        architect: AgentArchitect,
        operator: AgentExecutor,
        auditor: AgentReflector,
        collaboration_hub: CollaborationHub | None = None,
        memory_agent: AgentMemory | None = None,
    ) -> None:
        self.collaboration_hub = collaboration_hub

        # تهيئة المشغل والاستراتيجيات
        self.runner = CognitivePhaseRunner(memory_agent)

        self.planning_phase = PlanningPhase(strategist, auditor)
        self.design_phase = DesignPhase(architect)
        self.execution_phase = ExecutionPhase(operator)
        self.reflection_phase = ReflectionPhase(auditor)

    async def process_mission(
        self,
        mission: Mission,
        *,
        context: dict[str, object] | None = None,
        log_event: Callable[[str, dict[str, object]], Awaitable[None]] | None = None,
    ) -> dict[str, object]:
        """
        تنفيذ الحلقة المعرفية الكاملة للمهمة.
        Execute complete cognitive loop for mission.

        Args:
            mission: كائن المهمة
            context: سياق إضافي
            log_event: دالة استدعاء لتسجيل الأحداث

        Returns:
            dict: النتيجة النهائية للمهمة

        Raises:
            RuntimeError: في حال فشل المهمة بعد استنفاد المحاولات
        """
        state = CognitiveState(mission_id=mission.id, objective=mission.objective)
        base_context = dict(context or {})
        base_context["mission_id"] = mission.id
        base_context["objective"] = mission.objective

        collab_context = InMemoryCollaborationContext(base_context)
        await self._seed_education_context(mission.objective, collab_context)
        session = CouncilSession(hub=self.collaboration_hub, context=collab_context)
        safe_log = await self.runner.create_safe_logger(log_event)

        while state.iteration_count < state.max_iterations:
            state.iteration_count += 1
            await safe_log(
                CognitiveEvent.LOOP_START,
                {
                    "iteration": state.iteration_count,
                    "chief_agent": "رئيس الوكلاء",
                    "graph_mode": "cognitive_graph",
                },
            )

            try:
                # محاولة تنفيذ دورة معرفية كاملة
                result = await self._execute_cognitive_cycle(
                    state, collab_context, safe_log, session
                )

                if result is not None:
                    return result

            except StalemateError as se:
                self._handle_stalemate(se, state, collab_context, safe_log, session)

            except Exception as e:
                await self._handle_phase_error(e, state, safe_log)

        # فشل نهائي
        raise RuntimeError(f"Mission failed after {state.max_iterations} iterations.")

    async def _execute_cognitive_cycle(
        self,
        state: CognitiveState,
        collab_context: InMemoryCollaborationContext,
        safe_log: EventLogger,
        session: CouncilSession | None,
    ) -> dict[str, object] | None:
        """
        تنفيذ دورة معرفية كاملة.
        Execute one complete cognitive cycle (plan → design → execute → review).
        """
        # المرحلة 1: التخطيط | Planning phase
        if not state.plan or state.current_phase == CognitivePhase.RE_PLANNING:
            critique = await self.planning_phase.execute(
                state, collab_context, self.runner, session, safe_log
            )

            if not critique.approved:
                state.current_phase = CognitivePhase.RE_PLANNING
                collab_context.update("feedback_from_previous_attempt", critique.feedback)
                return None  # إعادة المحاولة

        # المرحلة 2: التصميم | Design phase
        await self.design_phase.execute(state, collab_context, self.runner, session, safe_log)

        # المرحلة 3: التنفيذ | Execution phase
        await self.execution_phase.execute(state, collab_context, self.runner, session, safe_log)

        # المرحلة 4: المراجعة | Review phase
        await self.reflection_phase.execute(state, collab_context, self.runner, session, safe_log)

        # التحقق من النجاح | Check success
        if state.critique and state.critique.approved:
            await safe_log(CognitiveEvent.MISSION_SUCCESS, {"result": state.execution_result})
            return state.execution_result or {}

        # إعداد للإعادة | Prepare for retry
        await self._prepare_for_retry(state, collab_context, safe_log, session)
        return None

    async def _prepare_for_retry(
        self,
        state: CognitiveState,
        collab_context: InMemoryCollaborationContext,
        safe_log: EventLogger,
        session: CouncilSession | None,
    ) -> None:
        """
        إعداد الحالة لإعادة المحاولة.
        """
        if state.critique:
            await safe_log(
                CognitiveEvent.MISSION_CRITIQUE_FAILED, {"critique": state.critique.model_dump()}
            )
            state.current_phase = CognitivePhase.RE_PLANNING
            collab_context.update("feedback_from_execution", state.critique.feedback)
            if session:
                session.notify_agent(
                    "strategist",
                    {
                        "type": "critique_failed",
                        "feedback": state.critique.feedback,
                        "iteration": state.iteration_count,
                    },
                )

    def _handle_stalemate(
        self,
        error: StalemateError,
        state: CognitiveState,
        collab_context: InMemoryCollaborationContext,
        safe_log: EventLogger,
        session: CouncilSession | None,
    ) -> None:
        """
        معالجة حالة الجمود.
        """
        logger.error(f"Stalemate trapped in main loop: {error}")
        collab_context.update(
            "system_override",
            "CRITICAL: INFINITE LOOP DETECTED. TRY SOMETHING DRASTICALLY DIFFERENT.",
        )
        # Force re-planning by invalidating the current plan
        state.plan = None
        state.current_phase = CognitivePhase.RE_PLANNING
        if session:
            session.notify_agent(
                "strategist",
                {"type": "critical_stalemate", "reason": str(error)},
            )

    async def _seed_education_context(
        self, objective: str, context: InMemoryCollaborationContext
    ) -> None:
        """
        تهيئة سياق تعليمي مسبقاً عند رصد طلب تمرين محدد.

        الهدف: تحسين نجاح المهمة الخارقة عبر تزويد الوكلاء بنص التمرين بشكل مبكر.
        """
        if not objective:
            return

        extracted = _extract_exercise_request(objective)
        if not extracted:
            return

        try:
            content = await search_educational_content(**extracted)
        except Exception as exc:
            logger.warning("Educational content retrieval failed: %s", exc)
            return

        if content:
            context.update("exercise_content", content)
            context.update("exercise_metadata", extracted)

    async def _handle_phase_error(
        self,
        error: Exception,
        state: CognitiveState,
        safe_log: EventLogger,
    ) -> None:
        """
        معالجة الأخطاء في المراحل.
        """
        logger.error(f"Error in phase {state.current_phase}: {error}")
        await safe_log(
            CognitiveEvent.PHASE_ERROR, {"phase": state.current_phase, "error": str(error)}
        )

    async def _execute_phase(
        self,
        *,
        phase_name: str | CognitivePhase,
        agent_name: str,
        action: Callable[[], Awaitable[dict[str, object]]],
        timeout: float,
        log_func: Callable[[str, dict[str, object]], Awaitable[None]],
    ) -> dict[str, object]:
        """
        تنفيذ مرحلة واحدة مع تسجيل الأحداث وإدارة المهلة الزمنية.

        يوفر هذا الغلاف واجهة بسيطة متوافقة مع الاختبارات القديمة.
        """
        return await self.runner._execute_phase_core(
            phase_name=phase_name,
            agent_name=agent_name,
            action=action,
            timeout=timeout,
            log_func=log_func,
        )


def _extract_exercise_request(objective: str) -> dict[str, str | None] | None:
    """
    استخراج بيانات طلب تمرين من نص الهدف بأسلوب بسيط وقابل للتوسع.
    """
    text = objective.strip()
    if not text:
        return None

    normalized = _normalize_digits(text)

    year_match = re.search(r"(20\d{2})", normalized)
    year = year_match.group(1) if year_match else None

    exam_ref = _extract_exam_ref(normalized)
    exercise_id = _extract_exercise_id(normalized)

    subject = "رياضيات" if "رياضيات" in normalized or "math" in normalized.lower() else None
    branch = "علوم تجريبية" if "علوم تجريبية" in normalized else None

    has_exercise_hint = "تمرين" in normalized or "exercise" in normalized.lower()
    if not (year or exam_ref or exercise_id or subject or branch or has_exercise_hint):
        return None

    return {
        "query": text,
        "year": year,
        "subject": subject,
        "branch": branch,
        "exam_ref": exam_ref,
        "exercise_id": exercise_id,
    }


def _normalize_digits(text: str) -> str:
    """
    توحيد الأرقام العربية الهندية إلى أرقام ASCII لتسهيل الاستخراج.
    """
    translations = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return text.translate(translations)


def _extract_exam_ref(text: str) -> str | None:
    """
    استخراج رقم الموضوع إذا كان مذكوراً في النص.
    """
    lower_text = text.lower()
    if "الموضوع" not in text and "subject" not in lower_text:
        return None

    if "الثاني" in text or "2" in text or "subject 2" in lower_text:
        return "الموضوع الثاني"
    if "الثالث" in text or "3" in text or "subject 3" in lower_text:
        return "الموضوع الثالث"
    if "الأول" in text or "الاول" in text or "1" in text or "subject 1" in lower_text:
        return "الموضوع الأول"
    return None


def _extract_exercise_id(text: str) -> str | None:
    """
    استخراج رقم التمرين إذا كان مذكوراً في النص.
    """
    lower_text = text.lower()
    if "التمرين" not in text and "exercise" not in lower_text:
        return None

    if "الثاني" in text or "2" in text or "exercise 2" in lower_text:
        return "2"
    if "الثالث" in text or "3" in text or "exercise 3" in lower_text:
        return "3"
    if "الأول" in text or "الاول" in text or "1" in text or "exercise 1" in lower_text:
        return "1"
    return None
