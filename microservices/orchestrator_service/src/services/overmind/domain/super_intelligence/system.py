"""
نظام الذكاء الجماعي الفائق (Super Collective Intelligence System).

الواجهة الرئيسية (Facade) للنظام.
"""

import inspect
from datetime import datetime

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.agents import AgentCouncil
from microservices.orchestrator_service.src.services.overmind.collaboration import CollaborationHub
from microservices.orchestrator_service.src.services.overmind.domain.super_intelligence.analyzer import (
    SituationAnalyzer,
)
from microservices.orchestrator_service.src.services.overmind.domain.super_intelligence.models import (
    Decision,
)
from microservices.orchestrator_service.src.services.overmind.domain.super_intelligence.synthesizer import (
    DecisionSynthesizer,
)

logger = get_logger(__name__)

_SUCCESS_CONFIDENCE_THRESHOLD = 70.0
_AGENT_SPEC_NAMES = (
    ("strategist", "strategist"),
    ("architect", "architect"),
    ("operator", "operator"),
    ("auditor", "auditor"),
)


class SuperCollectiveIntelligence:
    """
    الذكاء الجماعي الفائق.

    يوفر نقطة دخول موحدة (Facade) لعمليات اتخاذ القرار المعقدة.
    """

    def __init__(
        self,
        agent_council: AgentCouncil,
        collaboration_hub: CollaborationHub,
    ) -> None:
        self.council = agent_council
        self.hub = collaboration_hub

        # الحالة
        self.decision_history: list[Decision] = []
        self.total_decisions = 0
        self.successful_decisions = 0
        self.failed_decisions = 0

        logger.info("Super Collective Intelligence initialized (Refactored)")

    async def make_autonomous_decision(
        self,
        situation: str,
        context: dict[str, object] | None = None,
    ) -> Decision:
        """
        اتخاذ قرار مستقل بشكل كامل.
        """
        logger.info("=== Making Autonomous Decision ===")
        context = context or {}

        analysis = await SituationAnalyzer.analyze(situation, context)
        consultations = await self._consult_agents(situation, analysis)
        decision = await DecisionSynthesizer.synthesize(situation, analysis, consultations)
        self._store_decision_in_hub(decision)
        self._record_decision(decision)

        return decision

    async def _consult_agents(
        self,
        situation: str,
        analysis: dict[str, object],
    ) -> dict[str, object]:
        """
        استشارة الوكلاء بشكل فعلي وبأسلوب موحد.
        """
        logger.info("Consulting agents...")

        consultations: dict[str, object] = {}
        for agent_name, agent in self._get_agent_specs():
            consultations[agent_name] = await self._consult_agent(
                agent_name=agent_name,
                agent=agent,
                situation=situation,
                analysis=analysis,
            )

        self._record_consultations(situation=situation, consultations=consultations)

        return consultations

    async def execute_decision(self, decision: Decision) -> dict[str, object]:
        """
        تنفيذ القرار.
        """
        logger.info("Executing decision: %s", decision.id)

        decision.executed = True
        execution_success = self._is_confident_success(decision.confidence_score)

        self._update_execution_outcome(decision, execution_success)
        return self._build_execution_result(decision, execution_success)

    def get_statistics(self) -> dict[str, object]:
        """
        إحصائيات النظام.
        """
        success_rate = self._calculate_success_rate()

        return {
            "total_decisions": self.total_decisions,
            "successful": self.successful_decisions,
            "failed": self.failed_decisions,
            "success_rate": success_rate,
        }

    def _calculate_success_rate(self) -> float:
        """يحسب معدل النجاح كنسبة مئوية مع تفادي القسمة على صفر."""
        return self._safe_ratio(self.successful_decisions, self.total_decisions) * 100

    def _record_decision(self, decision: Decision) -> None:
        """يسجل القرار داخلياً ويحدث العدادات."""
        self.decision_history.append(decision)
        self.total_decisions += 1

    def _store_decision_in_hub(self, decision: Decision) -> None:
        """يحاول حفظ القرار الأخير داخل مركز التعاون إن توفر."""
        if not self.hub:
            return

        try:
            self.hub.store_data("last_autonomous_decision", decision.model_dump())
        except Exception as exc:
            logger.warning("Failed to store decision in hub: %s", exc)

    def _get_agent_specs(self) -> list[tuple[str, object]]:
        """يعيد قائمة الوكلاء الفعليين مع أسمائهم لتسهيل التكرار المنظم."""
        return [(label, getattr(self.council, attribute)) for label, attribute in _AGENT_SPEC_NAMES]

    async def _consult_agent(
        self,
        *,
        agent_name: str,
        agent: object,
        situation: str,
        analysis: dict[str, object],
    ) -> object:
        """ينفذ استشارة وكيل واحد مع تحقق صريح من توفر التابع المطلوب."""
        consult = getattr(agent, "consult", None)
        if not callable(consult):
            raise ValueError(f"Agent '{agent_name}' does not implement consult()")

        result = consult(situation, analysis)
        if inspect.isawaitable(result):
            return await result
        return result

    def _record_consultations(
        self,
        *,
        situation: str,
        consultations: dict[str, object],
    ) -> None:
        """يسجل نتائج الاستشارات داخل مركز التعاون عند توفره."""
        if not self.hub:
            return

        for agent, data in consultations.items():
            self.hub.record_contribution(
                agent_name=agent,
                action="consultation",
                input_data=self._build_consultation_input(situation),
                output_data=data,
                success=True,
            )

    def _update_execution_outcome(self, decision: Decision, success: bool) -> None:
        """يحدث نتيجة التنفيذ ويعدل عدادات النجاح والفشل."""
        if success:
            self.successful_decisions += 1
            decision.outcome = "success"
            return

        self.failed_decisions += 1
        decision.outcome = "failed"

    def _build_execution_result(
        self,
        decision: Decision,
        success: bool,
    ) -> dict[str, object]:
        """يبني نتيجة التنفيذ بصيغة موحدة."""
        return {
            "decision_id": decision.id,
            "executed": True,
            "success": success,
            "timestamp": self._now_iso(),
        }

    @staticmethod
    def _safe_ratio(numerator: int, denominator: int) -> float:
        """يعيد نسبة آمنة مع حماية القسمة على صفر."""
        if denominator <= 0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _is_confident_success(confidence_score: float) -> bool:
        """يتحقق من تجاوز الثقة للحد المعتمد."""
        return confidence_score > _SUCCESS_CONFIDENCE_THRESHOLD

    @staticmethod
    def _now_iso() -> str:
        """يعيد توقيتاً موحداً بصيغة ISO."""
        return datetime.utcnow().isoformat()

    @staticmethod
    def _truncate_text(text: str, limit: int) -> str:
        """يعيد نصاً مختصراً بطول محدد مع الحفاظ على السلوك الآمن."""
        if limit <= 0:
            return ""
        return text[:limit]

    @classmethod
    def _build_consultation_input(cls, situation: str) -> dict[str, str]:
        """ينشئ حمولة الاستشارة المختصرة بطريقة موحدة."""
        return {"situation": cls._truncate_text(situation, 50)}
