"""
Cognitive Phases Strategies.
----------------------------
Implements the Strategy Pattern for each cognitive phase.
Each phase encapsulates the specific logic for a step in the Council of Wisdom loop.
"""

import logging
from abc import ABC, abstractmethod

from app.core.protocols import (
    AgentArchitect,
    AgentExecutor,
    AgentPlanner,
    AgentReflector,
)
from microservices.orchestrator_service.src.services.overmind.domain.context import (
    InMemoryCollaborationContext,
)
from microservices.orchestrator_service.src.services.overmind.domain.council_session import (
    CouncilSession,
)
from microservices.orchestrator_service.src.services.overmind.domain.enums import (
    CognitiveEvent,
    CognitivePhase,
    OvermindMessage,
)
from microservices.orchestrator_service.src.services.overmind.domain.exceptions import (
    StalemateError,
)
from microservices.orchestrator_service.src.services.overmind.domain.phase_runner import (
    CognitivePhaseRunner,
)
from microservices.orchestrator_service.src.services.overmind.domain.primitives import (
    CognitiveCritique,
    CognitiveState,
    EventLogger,
)

logger = logging.getLogger(__name__)


class CognitivePhaseStrategy(ABC):
    """
    Abstract Base Class for a Cognitive Phase Strategy.
    """

    @abstractmethod
    async def execute(
        self,
        state: CognitiveState,
        context: InMemoryCollaborationContext,
        runner: CognitivePhaseRunner,
        session: CouncilSession | None,
        safe_log: EventLogger,
    ) -> None:
        """
        Execute the phase logic.
        """
        pass


class PlanningPhase(CognitivePhaseStrategy):
    """
    Handles the Planning Phase: Strategist creates plan -> Auditor reviews it.
    """

    def __init__(self, strategist: AgentPlanner, auditor: AgentReflector):
        self.strategist = strategist
        self.auditor = auditor

    async def execute(
        self,
        state: CognitiveState,
        context: InMemoryCollaborationContext,
        runner: CognitivePhaseRunner,
        session: CouncilSession | None,
        safe_log: EventLogger,
    ) -> CognitiveCritique:
        """
        Executes planning and returns the critique.
        """
        # 1. Create Plan
        state.plan = await runner.execute_action(
            phase_name=CognitivePhase.PLANNING,
            agent_name="Strategist",
            action=lambda: self.strategist.create_plan(state.objective, context),
            timeout=120.0,
            log_func=safe_log,
            session=session,
            input_data={"objective": state.objective},
            collab_context=context,
        )

        # 2. Stalemate Detection
        await self._detect_and_handle_stalemate(state, context, safe_log, session)

        # 3. Review Plan
        raw_critique = await runner.execute_action(
            phase_name=CognitivePhase.REVIEW_PLAN,
            agent_name="Auditor",
            action=lambda: self.auditor.review_work(
                state.plan, f"Plan for: {state.objective}", context
            ),
            timeout=60.0,
            log_func=safe_log,
            session=session,
            input_data={"plan_keys": runner.summarize_keys(state.plan)},
            collab_context=context,
        )

        critique = CognitiveCritique(
            approved=raw_critique.get("approved", False),
            feedback=raw_critique.get("feedback", "No feedback provided"),
            score=raw_critique.get("score", 0.0),
        )

        if not critique.approved:
            await safe_log(CognitiveEvent.PLAN_REJECTED, {"critique": critique.model_dump()})
            if "OPENROUTER_API_KEY" in critique.feedback:
                raise RuntimeError(OvermindMessage.AI_SERVICE_UNAVAILABLE)
        else:
            await safe_log(CognitiveEvent.PLAN_APPROVED, {"critique": critique.model_dump()})

        return critique

    async def _detect_and_handle_stalemate(
        self,
        state: CognitiveState,
        collab_context: InMemoryCollaborationContext,
        safe_log: EventLogger,
        session: CouncilSession | None,
    ) -> None:
        try:
            if hasattr(self.auditor, "detect_loop"):
                self.auditor.detect_loop(state.history_hashes, state.plan)

            if hasattr(self.auditor, "_compute_hash"):
                state.history_hashes.append(self.auditor._compute_hash(state.plan))

        except StalemateError as e:
            logger.warning(f"Stalemate detected: {e}")
            await safe_log("stalemate_detected", {"reason": str(e)})

            collab_context.update(
                "system_override",
                "Warning: You are repeating failed plans. CHANGE STRATEGY IMMEDIATELY. "
                "Do not use the same tools or logic.",
            )
            if session:
                session.notify_agent(
                    "strategist",
                    {
                        "type": "stalemate_detected",
                        "reason": str(e),
                        "guidance": "Change strategy immediately.",
                    },
                )
            raise


class DesignPhase(CognitivePhaseStrategy):
    """
    Handles the Design Phase: Architect designs solution based on plan.
    """

    def __init__(self, architect: AgentArchitect):
        self.architect = architect

    async def execute(
        self,
        state: CognitiveState,
        context: InMemoryCollaborationContext,
        runner: CognitivePhaseRunner,
        session: CouncilSession | None,
        safe_log: EventLogger,
    ) -> None:
        state.design = await runner.execute_action(
            phase_name=CognitivePhase.DESIGN,
            agent_name="Architect",
            action=lambda: self.architect.design_solution(state.plan, context),
            timeout=120.0,
            log_func=safe_log,
            session=session,
            input_data={"plan_keys": runner.summarize_keys(state.plan)},
            collab_context=context,
        )


class ExecutionPhase(CognitivePhaseStrategy):
    """
    Handles the Execution Phase: Operator executes the design.
    """

    def __init__(self, operator: AgentExecutor):
        self.operator = operator

    async def execute(
        self,
        state: CognitiveState,
        context: InMemoryCollaborationContext,
        runner: CognitivePhaseRunner,
        session: CouncilSession | None,
        safe_log: EventLogger,
    ) -> None:
        state.execution_result = await runner.execute_action(
            phase_name=CognitivePhase.EXECUTION,
            agent_name="Operator",
            action=lambda: self.operator.execute_tasks(state.design, context),
            timeout=300.0,
            log_func=safe_log,
            session=session,
            input_data={"design_keys": runner.summarize_keys(state.design)},
            collab_context=context,
        )


class ReflectionPhase(CognitivePhaseStrategy):
    """
    Handles the Reflection Phase: Auditor reviews the final execution.
    """

    def __init__(self, auditor: AgentReflector):
        self.auditor = auditor

    async def execute(
        self,
        state: CognitiveState,
        context: InMemoryCollaborationContext,
        runner: CognitivePhaseRunner,
        session: CouncilSession | None,
        safe_log: EventLogger,
    ) -> None:
        raw_final_critique = await runner.execute_action(
            phase_name=CognitivePhase.REFLECTION,
            agent_name="Auditor",
            action=lambda: self.auditor.review_work(
                state.execution_result, state.objective, context
            ),
            timeout=60.0,
            log_func=safe_log,
            session=session,
            input_data={"execution_keys": runner.summarize_keys(state.execution_result)},
            collab_context=context,
        )

        state.critique = CognitiveCritique(
            approved=raw_final_critique.get("approved", False),
            feedback=raw_final_critique.get("feedback", "No feedback provided"),
            score=raw_final_critique.get("score", 0.0),
        )
