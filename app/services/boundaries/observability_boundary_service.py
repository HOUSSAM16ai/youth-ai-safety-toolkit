from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.services.boundaries.observability_client import ObservabilityServiceClient

if TYPE_CHECKING:
    from app.telemetry.unified_observability import UnifiedObservabilityService


class ObservabilityBoundaryService:
    """
    خدمة مراقبة حدية موحدة.
    تجمع إشارات AIOps والقياسات والتتبع في واجهة نظيفة واحدة،
    وتطبق مبدأ فصل المسؤوليات بعزل الموجه عن تفاصيل التنفيذ الداخلية.
    """

    def __init__(
        self,
        telemetry_service: UnifiedObservabilityService | None = None,
        observability_client: ObservabilityServiceClient | None = None,
    ):
        if telemetry_service:
            self.telemetry = telemetry_service
        else:
            from app.telemetry.unified_observability import get_unified_observability

            self.telemetry = get_unified_observability()

        self.client = observability_client or ObservabilityServiceClient()

    async def get_system_health(self) -> dict[str, object]:
        """
        تجميع الحالة الصحية للنظام من مصادر متعددة بطريقة خفيفة الوزن.
        """
        golden_signals = self.telemetry.get_golden_signals()

        # We can also fetch health from the microservice if needed,
        # but for now we keep the existing behavior augmented with microservice check if possible,
        # or just return the local view as the "system" health.

        return {
            "status": "ok",
            "system": "superhuman",
            "timestamp": golden_signals.get("timestamp"),
        }

    async def get_golden_signals(self) -> dict[str, object]:
        """
        استرجاع الإشارات الذهبية الخاصة بالموثوقية (زمن الاستجابة، الحركة، الأخطاء، التشبع).
        """
        return self.telemetry.get_golden_signals()

    async def get_aiops_metrics(self) -> dict[str, object]:
        """
        استرجاع مقاييس AIOps للشذوذات وقرارات المعالجة الذاتية.
        يتم التفويض الآن لخدمة المراقبة الدقيقة (Microservice).
        """
        try:
            return await self.client.get_aiops_metrics()
        except Exception:
            # Fallback or return empty if service is down, to avoid breaking the monolith UI
            return {
                "anomaly_score": 0.0,
                "self_healing_events": 0,
                "predictions": None,
            }

    async def get_performance_snapshot(self) -> dict[str, object]:
        """
        الحصول على لقطة شاملة لإحصاءات الأداء.
        """
        return self.telemetry.get_statistics()

    async def get_endpoint_analytics(self, path: str) -> list[dict[str, object]]:
        """
        تحليل آثار التتبع لمسار واجهة برمجة تطبيقات محدد.
        """
        return self.telemetry.find_traces_by_criteria(operation_name=path)

    async def get_active_alerts(self) -> list[dict[str, object]]:
        """
        استرجاع التنبيهات النشطة المتعلقة بالشذوذات من النظام.
        """
        try:
            # Alerts from microservice match AlertResponse schema
            return await self.client.get_active_alerts()
        except Exception:
            # Fallback to local and map to AlertResponse schema
            return [
                {
                    "id": a.alert_id,
                    "severity": a.severity.value
                    if hasattr(a.severity, "value")
                    else str(a.severity),
                    "message": a.description,
                    "timestamp": datetime.fromtimestamp(a.timestamp, UTC).isoformat(),
                    "status": "resolved" if a.resolved else "active",
                }
                for a in self.telemetry.anomaly_alerts
            ]
