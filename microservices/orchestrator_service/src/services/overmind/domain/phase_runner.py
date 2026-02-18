"""
Cognitive Phase Runner.
-----------------------
Encapsulates the execution machinery for cognitive phases.
Handles logging, timeout management, session recording, and memory snapshots.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.protocols import AgentMemory
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
from microservices.orchestrator_service.src.services.overmind.domain.primitives import (
    AgentUnitOfWork,
    EventLogger,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CognitivePhaseRunner:
    """
    Infrastructure runner for executing cognitive agent actions safely.
    """

    def __init__(self, memory_agent: AgentMemory | None = None) -> None:
        self.memory_agent = memory_agent

    async def create_safe_logger(
        self, log_event: Callable[[str, dict[str, object]], Awaitable[None]] | None
    ) -> EventLogger:
        """
        Creates a safe logging function that handles None check.
        """

        async def safe_log(evt_type: str, data: dict[str, object]) -> None:
            if log_event:
                await log_event(evt_type, data)

        return safe_log

    async def execute_action(
        self,
        *,
        phase_name: str | CognitivePhase,
        agent_name: str,
        action: Callable[[], Awaitable[T]],
        timeout: float,
        log_func: EventLogger,
        session: CouncilSession | None,
        input_data: dict[str, object],
        collab_context: InMemoryCollaborationContext,
    ) -> T:
        """
        Executes an agent action with full observability (logging, session, memory).
        """
        phase_label = str(phase_name)
        try:
            result = await self._execute_phase_core(
                phase_name=phase_name,
                agent_name=agent_name,
                action=action,
                timeout=timeout,
                log_func=log_func,
            )
            self._record_session_action(
                session=session,
                agent_name=agent_name,
                phase_label=phase_label,
                input_data=input_data,
                output_data=result,  # type: ignore
                success=True,
                error_message=None,
            )
            await self._capture_memory_snapshot(
                collab_context=collab_context,
                agent_name=agent_name,
                phase_label=phase_label,
                input_data=input_data,
                output_data=result,  # type: ignore
                error_message=None,
            )
            return result
        except Exception as exc:
            self._record_session_action(
                session=session,
                agent_name=agent_name,
                phase_label=phase_label,
                input_data=input_data,
                output_data={"error": str(exc)},
                success=False,
                error_message=str(exc),
            )
            await self._capture_memory_snapshot(
                collab_context=collab_context,
                agent_name=agent_name,
                phase_label=phase_label,
                input_data=input_data,
                output_data=None,
                error_message=str(exc),
            )
            raise

    async def _execute_phase_core(
        self,
        *,
        phase_name: str | CognitivePhase,
        agent_name: str,
        action: Callable[[], Awaitable[T]],
        timeout: float,
        log_func: EventLogger,
    ) -> T:
        """
        Core execution logic with timeout and logging.
        """
        unit = self._build_unit_of_work(phase_name=phase_name, agent_name=agent_name)
        await log_func(
            CognitiveEvent.PHASE_START,
            {"phase": phase_name, "agent": agent_name, "unit_of_work": unit.model_dump()},
        )
        try:
            result = await asyncio.wait_for(action(), timeout=timeout)
            phase_str = self._phase_event_label(phase_name)
            completed_unit = unit.model_copy(
                update={
                    "status": "completed",
                    "summary": "تم إنجاز وحدة العمل بنجاح",
                }
            )
            await log_func(
                f"{phase_str}_completed",
                {
                    "summary": "Phase completed successfully",
                    "unit_of_work": completed_unit.model_dump(),
                },
            )
            return result
        except TimeoutError:
            error_msg = f"{agent_name} timeout during {phase_name} (exceeded {timeout}s)"
            logger.error(error_msg)
            phase_str = self._phase_event_label(phase_name)
            failed_unit = unit.model_copy(
                update={
                    "status": "timeout",
                    "summary": "تجاوزت وحدة العمل المهلة المحددة",
                }
            )
            await log_func(
                f"{phase_str}_timeout",
                {"error": error_msg, "unit_of_work": failed_unit.model_dump()},
            )
            raise RuntimeError(error_msg) from None

    @staticmethod
    def summarize_keys(payload: dict[str, object] | None) -> list[str]:
        """Summarizes keys safely."""
        return list(payload.keys()) if isinstance(payload, dict) else []

    @staticmethod
    def _phase_event_label(phase_name: str | CognitivePhase) -> str:
        return str(phase_name).lower()

    @staticmethod
    def _build_unit_of_work(
        *, phase_name: str | CognitivePhase, agent_name: str
    ) -> AgentUnitOfWork:
        """
        بناء وحدة عمل تمثل الوكيل كوحدة تنفيذية مستقلة.
        """
        phase_value = (
            phase_name
            if isinstance(phase_name, CognitivePhase)
            else CognitivePhase(str(phase_name))
        )
        unit_id = f"{agent_name}-{phase_value.value}"
        return AgentUnitOfWork(
            unit_id=unit_id,
            agent=agent_name,
            phase=phase_value,
            summary="جاري تنفيذ وحدة العمل وفق خطة المرحلة",
        )

    @staticmethod
    def _record_session_action(
        *,
        session: CouncilSession | None,
        agent_name: str,
        phase_label: str,
        input_data: dict[str, object],
        output_data: dict[str, object] | None,
        success: bool,
        error_message: str | None,
    ) -> None:
        if not session:
            return
        session.record_action(
            agent_name=agent_name,
            action=phase_label,
            input_data=input_data,
            output_data=output_data or {},
            success=success,
            error_message=error_message,
        )

    async def _capture_memory_snapshot(
        self,
        *,
        collab_context: InMemoryCollaborationContext,
        agent_name: str,
        phase_label: str,
        input_data: dict[str, object],
        output_data: dict[str, object] | None,
        error_message: str | None,
    ) -> None:
        if not self.memory_agent:
            return
        payload, label_suffix = self._build_memory_payload(
            agent_name=agent_name,
            input_data=input_data,
            output_data=output_data,
            error_message=error_message,
        )
        await self.memory_agent.capture_memory(
            collab_context,
            label=f"{phase_label}{label_suffix}",
            payload=payload,
        )

    @staticmethod
    def _build_memory_payload(
        *,
        agent_name: str,
        input_data: dict[str, object],
        output_data: dict[str, object] | None,
        error_message: str | None,
    ) -> tuple[dict[str, object], str]:
        payload: dict[str, object] = {
            "agent": agent_name,
            "input": input_data,
        }
        label_suffix = ""
        if error_message:
            payload["error"] = error_message
            label_suffix = "_error"
        if output_data is not None:
            payload["output"] = output_data
        return payload, label_suffix
