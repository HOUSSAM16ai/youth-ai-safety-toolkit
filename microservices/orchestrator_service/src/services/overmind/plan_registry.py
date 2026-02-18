"""
سجل خطط الوكلاء (Agent Plan Registry).
---------------------------------------
يوفر هذا الملف مخزناً بسيطاً داخل الذاكرة لتخزين خطط الوكلاء
واسترجاعها عبر معرفات واضحة. يعتمد على نمط "مستودع البيانات"
مع إبقاء الحالة ضمن حدود التطبيق (App State).
"""

from __future__ import annotations

from dataclasses import dataclass

from microservices.orchestrator_service.src.services.overmind.domain.api_schemas import (
    AgentPlanData,
)


@dataclass(frozen=True)
class AgentPlanRecord:
    """
    تمثيل داخلي لخطة الوكلاء.

    يحتوي على البيانات الأساسية اللازمة لعرض الخطة للعملاء.
    """

    data: AgentPlanData


class AgentPlanRegistry:
    """
    مستودع خطط الوكلاء في الذاكرة.

    يُستخدم لتسجيل الخطط المؤقتة واسترجاعها بسرعة عبر معرف الخطة.
    """

    def __init__(self) -> None:
        self._plans: dict[str, AgentPlanRecord] = {}

    def store(self, plan: AgentPlanRecord) -> None:
        """
        حفظ خطة جديدة داخل السجل.

        Args:
            plan: الخطة المراد تخزينها.
        """
        self._plans[plan.data.plan_id] = plan

    def get(self, plan_id: str) -> AgentPlanRecord | None:
        """
        استرجاع خطة من السجل.

        Args:
            plan_id: معرف الخطة.

        Returns:
            AgentPlanRecord | None: الخطة إذا وجدت أو None إذا لم توجد.
        """
        return self._plans.get(plan_id)
