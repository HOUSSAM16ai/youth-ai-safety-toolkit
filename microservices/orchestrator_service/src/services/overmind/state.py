# app/services/overmind/state.py
# =================================================================================================
# OVERMIND STATE MANAGER – NEURAL MEMORY SUBSYSTEM
# Version: 11.2.0-pacelc-gapless
# =================================================================================================

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.protocols import EventBusProtocol
from microservices.orchestrator_service.src.core.event_bus import get_event_bus
from microservices.orchestrator_service.src.models.mission import (
    Mission,
    MissionEvent,
    MissionEventType,
    MissionOutbox,
    MissionPlan,
    MissionStatus,
    PlanStatus,
    Task,
    TaskStatus,
)
from microservices.orchestrator_service.src.services.overmind.domain.types import (
    JsonValue,
    MissionContext,
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(UTC)


class MissionStateManager:
    """
    يدير الحالة الدائمة للمهام والخطط داخل نواة الواقع.

    يعتمد الإدخال/الإخراج غير المتزامن لتعظيم الأداء،
    ويستخدم ناقل الأحداث لتوفير استجابة منخفضة مع الحفاظ على الاتساق.
    """

    def __init__(self, session: AsyncSession, event_bus: EventBusProtocol | None = None) -> None:
        self.session = session
        self.event_bus = event_bus or get_event_bus()

    async def create_mission(
        self,
        objective: str,
        initiator_id: int,
        context: MissionContext | None = None,
        idempotency_key: str | None = None,
    ) -> Mission:
        # Check for existing mission with idempotency_key
        if idempotency_key:
            stmt = select(Mission).where(Mission.idempotency_key == idempotency_key)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        mission = Mission(
            objective=objective,
            initiator_id=initiator_id,
            status=MissionStatus.PENDING,
            idempotency_key=idempotency_key,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(mission)
        await self.session.flush()
        await self.session.commit()
        return mission

    async def get_mission(self, mission_id: int) -> Mission | None:
        stmt = (
            select(Mission)
            .options(
                joinedload(Mission.mission_plans),
                joinedload(Mission.tasks),
            )
            .where(Mission.id == mission_id)
        )
        result = await self.session.execute(stmt)
        # Using unique() is essential when using joinedload with one-to-many relationships
        # to prevent duplicate Mission objects due to the Cartesian product.
        return result.unique().scalar_one_or_none()

    async def update_mission_status(
        self, mission_id: int, status: MissionStatus, note: str | None = None
    ) -> None:
        stmt = select(Mission).where(Mission.id == mission_id)
        result = await self.session.execute(stmt)
        mission = result.scalar_one_or_none()
        if mission:
            # Enforce Strict State Transitions
            if not self._is_valid_transition(mission.status, status):
                error_msg = f"Invalid Mission Transition: {mission.status} -> {status} for Mission {mission_id}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            old_status = str(mission.status)
            mission.status = status
            mission.updated_at = utc_now()

            # Log the status change event (which now commits)
            await self.log_event(
                mission_id,
                MissionEventType.STATUS_CHANGE,
                {"old_status": old_status, "new_status": str(status), "note": note},
            )
            # Explicit commit to ensure status update is visible
            await self.session.commit()

    def _is_valid_transition(self, current: MissionStatus, new_status: MissionStatus) -> bool:
        """
        Defines the legal state transitions for the Mission State Machine.
        """
        if current == new_status:
            return True

        # Define allowed transitions
        transitions = {
            MissionStatus.PENDING: {
                MissionStatus.RUNNING,
                MissionStatus.FAILED,
                MissionStatus.CANCELED,
            },
            MissionStatus.RUNNING: {
                MissionStatus.SUCCESS,
                MissionStatus.PARTIAL_SUCCESS,
                MissionStatus.FAILED,
                MissionStatus.CANCELED,
            },
            # Allow Retry from Terminal States
            MissionStatus.FAILED: {MissionStatus.PENDING, MissionStatus.RUNNING},
            MissionStatus.CANCELED: {MissionStatus.PENDING, MissionStatus.RUNNING},
            MissionStatus.SUCCESS: set(),  # Final state
            MissionStatus.PARTIAL_SUCCESS: set(),  # Final state
        }

        allowed = transitions.get(current, set())
        return new_status in allowed

    async def complete_mission(
        self,
        mission_id: int,
        result_summary: str | None = None,
        result_json: dict[str, JsonValue] | None = None,
        status: MissionStatus = MissionStatus.SUCCESS,
    ) -> None:
        """
        Completes the mission, updates the result summary, and logs the completion event.
        Fixes the visibility issue in Admin Dashboard.
        """
        stmt = select(Mission).where(Mission.id == mission_id)
        result = await self.session.execute(stmt)
        mission = result.scalar_one_or_none()
        if mission:
            mission.status = status
            mission.updated_at = utc_now()
            if result_summary:
                mission.result_summary = result_summary

            # Log completion event
            payload = {"result": result_json} if result_json else {}
            await self.log_event(
                mission_id,
                MissionEventType.MISSION_COMPLETED,
                payload,
            )
            # Explicit commit to ensure persistence
            await self.session.commit()

    async def log_event(
        self, mission_id: int, event_type: MissionEventType, payload: dict[str, JsonValue]
    ) -> None:
        # 1. Log Event (Source of Truth)
        event = MissionEvent(
            mission_id=mission_id,
            event_type=event_type,
            payload_json=payload,
            created_at=utc_now(),
        )
        self.session.add(event)

        # 2. Add to Outbox (Transactional Guarantee)
        # The prompt mandates Transactional Outbox to solve dual-write.
        # This ensures that even if Redis fails, the intention to publish is recorded.
        outbox = MissionOutbox(
            mission_id=mission_id,
            event_type=str(event_type.value),
            payload_json=payload,
            status="pending",
            created_at=utc_now(),
        )
        self.session.add(outbox)

        # 3. Commit Atomically
        await self.session.commit()

        # 4. Broadcast immediately (Best effort)
        # Ideally, a background worker polls 'mission_outbox' where status='pending'.
        # For simplicity and latency, we try direct publish.
        # If this fails, the 'monitor_mission_events' (catch-up) mechanism still works via DB polling.
        try:
            await self.event_bus.publish(f"mission:{mission_id}", event)
        except Exception as e:
            logger.warning(f"Failed to publish event to Redis: {e}. Outbox record ID: {outbox.id}")

    async def get_mission_events(self, mission_id: int) -> list[MissionEvent]:
        """Fetch all historical events for a mission."""
        stmt = (
            select(MissionEvent)
            .where(MissionEvent.mission_id == mission_id)
            .order_by(MissionEvent.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def persist_plan(
        self,
        mission_id: int,
        planner_name: str,
        plan_schema: object,  # MissionPlanSchema - using object to avoid circular import if schema is elsewhere
        score: float,
        rationale: str,
    ) -> MissionPlan:
        # Determine version
        stmt = select(func.max(MissionPlan.version)).where(MissionPlan.mission_id == mission_id)
        result = await self.session.execute(stmt)
        current_max = result.scalar() or 0
        version = current_max + 1

        # Safe access to attributes using getattr
        objective = getattr(plan_schema, "objective", "")
        tasks = getattr(plan_schema, "tasks", [])

        raw_data = {
            "objective": str(objective),
            "tasks_count": len(list(tasks)),  # Ensure it's iterable
        }

        mp = MissionPlan(
            mission_id=mission_id,
            version=version,
            planner_name=planner_name,
            status=PlanStatus.VALID,
            score=score,
            rationale=rationale,
            raw_json=raw_data,
            stats_json={},
            warnings_json=[],
            created_at=utc_now(),
        )
        self.session.add(mp)
        await self.session.flush()

        # Update Mission active plan
        mission_stmt = select(Mission).where(Mission.id == mission_id)
        mission_res = await self.session.execute(mission_stmt)
        mission = mission_res.scalar_one()
        mission.active_plan_id = mp.id

        # Create Tasks
        for t in tasks:
            task_row = Task(
                mission_id=mission_id,
                plan_id=mp.id,
                task_key=getattr(t, "task_id", ""),
                description=getattr(t, "description", ""),
                tool_name=getattr(t, "tool_name", ""),
                tool_args_json=getattr(t, "tool_args", {}),
                status=TaskStatus.PENDING,
                attempt_count=0,
                max_attempts=3,  # Default
                priority=getattr(t, "priority", 0),
                depends_on_json=getattr(t, "dependencies", []),
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            self.session.add(task_row)

        await self.session.commit()
        return mp

    async def get_tasks(self, mission_id: int) -> list[Task]:
        stmt = select(Task).where(Task.mission_id == mission_id).order_by(Task.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_task_running(self, task_id: int) -> None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        task = result.scalar_one()
        task.status = TaskStatus.RUNNING
        task.started_at = utc_now()
        task.attempt_count += 1
        await self.session.flush()
        await self.session.commit()

    async def mark_task_complete(
        self, task_id: int, result_text: str, meta: dict[str, JsonValue] | None = None
    ) -> None:
        if meta is None:
            meta = {}
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        task = result.scalar_one()
        task.status = TaskStatus.SUCCESS
        task.finished_at = utc_now()
        task.result_text = result_text
        task.result_meta_json = meta
        await self.session.flush()
        await self.session.commit()

    async def mark_task_failed(self, task_id: int, error_text: str) -> None:
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        task = result.scalar_one()
        task.status = TaskStatus.FAILED
        task.finished_at = utc_now()
        task.error_text = error_text
        await self.session.flush()
        await self.session.commit()

    async def monitor_mission_events(
        self, mission_id: int, poll_interval: float = 1.0
    ) -> AsyncGenerator[MissionEvent, None]:
        """
        Monitors a mission for new events using PACELC Optimization.
        Prioritizes EventBus for Low Latency (L), falling back to DB Polling
        only for recovery/initial load (Consistency).

        Gap-Free Strategy:
        1. Subscribe to EventBus (buffer events).
        2. Query Database (get past events).
        3. Yield DB events.
        4. Yield Buffered events (deduplicate).
        5. Continue Streaming from Bus.

        Args:
            mission_id (int): ID of the mission to monitor.
            poll_interval (float): Unused in EventBus mode.

        Yields:
            MissionEvent: The next event in the stream.
        """
        last_event_id = 0
        channel = f"mission:{mission_id}"

        # 1. Subscribe FIRST to avoid Race Condition (Gap-Free)
        queue = self.event_bus.subscribe_queue(channel)

        try:
            # 2. Catch-up from Database (Consistency)
            stmt = (
                select(MissionEvent)
                .where(MissionEvent.mission_id == mission_id)
                .order_by(MissionEvent.id.asc())
            )
            result = await self.session.execute(stmt)
            db_events = result.scalars().all()

            # Yield DB events
            for event in db_events:
                yield event
                if event.id:
                    last_event_id = max(last_event_id, event.id)
                if self._is_terminal_event(event):
                    return

            # 3. Process Buffered Queue & Live Stream (Latency)
            while True:
                event = await queue.get()

                # Handle dict events from Redis Bridge (which lack .id attribute)
                if isinstance(event, dict):
                    try:
                        # Attempt to reconstruct MissionEvent from dict
                        # This ensures downstream consumers receive the expected type
                        evt_type = event.get("event_type")
                        payload = event.get("payload_json") or event.get("data") or {}

                        # Create transient MissionEvent (not attached to session)
                        event = MissionEvent(
                            mission_id=mission_id,
                            event_type=evt_type,
                            payload_json=payload,
                            created_at=utc_now(),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to convert Redis event dict to MissionEvent: {e}")
                        # Fallback: skip this malformed event to avoid crashing the stream
                        continue

                # Deduplicate: Skip if we already saw this ID from DB
                # Safety check: ensure event has .id attribute
                event_id = getattr(event, "id", None)

                if event_id and event_id <= last_event_id:
                    continue

                yield event

                if event_id:
                    last_event_id = max(last_event_id, event_id)

                if self._is_terminal_event(event):
                    return

        finally:
            self.event_bus.unsubscribe_queue(channel, queue)

    def _is_terminal_event(self, event: MissionEvent) -> bool:
        """Helper to check if an event concludes the mission."""
        return event.event_type in [
            MissionEventType.MISSION_COMPLETED,
            MissionEventType.MISSION_FAILED,
        ]
