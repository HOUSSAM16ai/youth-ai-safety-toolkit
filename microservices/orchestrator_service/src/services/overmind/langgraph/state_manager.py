from __future__ import annotations

from collections.abc import AsyncGenerator

from app.core.protocols import MissionStateManagerProtocol
from microservices.orchestrator_service.src.models.mission import (
    Mission,
    MissionEvent,
    MissionEventType,
    MissionStatus,
)


class EphemeralMissionStateManager(MissionStateManagerProtocol):
    """
    مدير حالة مؤقت لدعم تشغيل LangGraph بدون قاعدة بيانات.

    يوفر هذا الصف تنفيذات آمنة وقابلة للاختبار لبروتوكول MissionStateManager،
    مع الحفاظ على حدود التجريد وتجنب الاعتماد على التخزين الدائم.
    """

    async def get_mission(self, mission_id: int) -> Mission | None:
        """
        استرجاع مهمة غير متوفر في الوضع المؤقت.
        """
        return None

    async def update_mission_status(
        self, mission_id: int, status: MissionStatus, note: str | None = None
    ) -> None:
        """
        تحديث حالة المهمة دون تخزين دائم.
        """
        return

    async def log_event(
        self, mission_id: int, event_type: MissionEventType, payload: dict[str, object]
    ) -> None:
        """
        تسجيل الحدث بشكل مؤقت دون تخزين دائم.
        """
        return

    async def mark_task_running(self, task_id: int) -> None:
        """
        تسجيل حالة المهمة كقيد التشغيل في الذاكرة المؤقتة.
        """
        return

    async def mark_task_complete(
        self, task_id: int, result_text: str, meta: dict[str, object] | None = None
    ) -> None:
        """
        تسجيل اكتمال المهمة في الذاكرة المؤقتة.
        """
        return

    async def mark_task_failed(self, task_id: int, error_text: str) -> None:
        """
        تسجيل فشل المهمة في الذاكرة المؤقتة.
        """
        return

    async def monitor_mission_events(
        self, mission_id: int, poll_interval: float = 1.0
    ) -> AsyncGenerator[MissionEvent, None]:
        """
        مراقبة أحداث غير متاحة في الوضع المؤقت.
        """
        if False:
            yield MissionEvent(
                mission_id=mission_id,
                event_type=MissionEventType.STATUS_CHANGE,
                payload_json={},
            )
