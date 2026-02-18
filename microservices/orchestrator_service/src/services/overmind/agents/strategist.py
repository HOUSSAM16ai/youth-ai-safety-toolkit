# app/services/overmind/agents/strategist.py
"""
الوكيل الاستراتيجي (Strategist Agent) - مخطط العبقري.
---------------------------------------------------------
يقوم هذا الوكيل بتحليل الأهداف المعقدة وتفكيكها باستخدام خوارزميات التفكير
الشجري (Tree of Thoughts) والتحليل العودي (Recursive Decomposition).

تم تحويله لاستخدام Microservice (planning-agent) بدلاً من التنفيذ المحلي.

المعايير:
- CS50 2025 Strict Mode.
- توثيق "Legendary" باللغة العربية.
- استخدام واجهات صارمة.
"""

import json
import re

from app.core.di import get_logger
from app.core.protocols import AgentPlanner, CollaborationContext
from microservices.orchestrator_service.src.core.ai_gateway import AIClient
from microservices.orchestrator_service.src.infrastructure.clients.planning_client import (
    planning_client,
)
from microservices.orchestrator_service.src.services.overmind.dec_pomdp_proof import (
    build_dec_pomdp_consultation_payload,
    is_dec_pomdp_proof_question,
)

logger = get_logger(__name__)


class StrategistAgent(AgentPlanner):
    """
    العقل المدبر للتخطيط الاستراتيجي.

    المسؤوليات:
    1. فهم النوايا الخفية وراء طلب المستخدم.
    2. تفكيك المشكلة الكبرى إلى خطوات ذرية قابلة للتنفيذ.
    3. تحديد التبعيات بين الخطوات (DAG Construction).
    """

    def __init__(self, ai_client: AIClient) -> None:
        self.ai = ai_client

    async def create_plan(self, objective: str, context: CollaborationContext) -> dict[str, object]:
        """
        إنشاء خطة استراتيجية محكمة.

        يستخدم خدمة Planning Agent لتوليد الخطة.
        """
        logger.info("Strategist is requesting a plan for: %s", objective)

        try:
            # استخدام خدمة التخطيط المستقلة (Decoupled Microservice Call)
            plan_data = await planning_client.create_plan(
                objective=objective, context=context.shared_memory
            )

            # تحديث الذاكرة المشتركة
            self._record_plan_in_context(context, plan_data)
            logger.info("Strategist: Plan received with %s steps", _count_steps(plan_data))

            return plan_data

        except Exception as e:
            return self._handle_general_error(e)

    def _handle_general_error(self, error: Exception) -> dict[str, object]:
        """
        معالجة الأخطاء العامة.

        Handle general errors.

        Args:
            error: الخطأ

        Returns:
            خطة طوارئ
        """
        logger.exception(f"Strategist failed to plan: {error}")
        return {
            "strategy_name": "Emergency Fallback",
            "reasoning": f"Planning failed due to: {type(error).__name__}: {error}",
            "steps": [
                {
                    "name": "Analyze Failure",
                    "description": f"Check why planning failed: {type(error).__name__}: {str(error)[:200]}",
                    "tool_hint": "unknown",
                }
            ],
        }

    async def consult(self, situation: str, analysis: dict[str, object]) -> dict[str, object]:
        """
        تقديم استشارة استراتيجية.
        Provide strategic consultation on the situation.

        Args:
            situation: وصف الموقف
            analysis: تحليل الموقف

        Returns:
            dict: التوصية والثقة
        """
        logger.info("Strategist is being consulted...")

        if is_dec_pomdp_proof_question(situation):
            return build_dec_pomdp_consultation_payload("strategist")

        system_prompt = self._build_consult_system_prompt()
        user_message = self._build_consult_user_message(situation, analysis)

        try:
            response_text = await self.ai.send_message(
                system_prompt=system_prompt, user_message=user_message, temperature=0.3
            )

            return self._parse_json_response(response_text)
        except Exception as exc:
            return self._handle_consult_error(exc)

    def _record_plan_in_context(
        self,
        context: CollaborationContext,
        plan_data: dict[str, object],
    ) -> None:
        """
        تسجيل الخطة في سياق التعاون.

        Args:
            context: سياق التعاون
            plan_data: بيانات الخطة
        """
        context.update("last_plan", plan_data)

    def _build_consult_system_prompt(self) -> str:
        """
        بناء تعليمات الاستشارة الاستراتيجية للنظام.
        """
        return """
        أنت "الاستراتيجي" (The Strategist).
        دورك هو تحليل الموقف من منظور استراتيجي بعيد المدى.

        النقاط الأساسية:
        1. التوافق مع الأهداف العليا.
        2. تحليل الفرص والتهديدات الاستراتيجية.
        3. اقتراح نهج عام للحل.

        قدم توصية موجزة ومباشرة.
        الرد يجب أن يكون JSON فقط:
        {
            "recommendation": "string (english)",
            "confidence": float (0-100)
        }
        """

    def _build_consult_user_message(self, situation: str, analysis: dict[str, object]) -> str:
        """
        بناء رسالة المستخدم للاستشارة الاستراتيجية.
        """
        return f"Situation: {situation}\nAnalysis: {json.dumps(analysis, default=str)}"

    def _handle_consult_error(self, error: Exception) -> dict[str, object]:
        """
        معالجة أخطاء الاستشارة وإرجاع توصية احتياطية.
        """
        logger.warning("Strategist consultation failed: %s", error)
        return {
            "recommendation": "Adopt a cautious strategic approach (AI consultation failed).",
            "confidence": 50.0,
        }

    def _parse_json_response(self, response_text: str) -> dict[str, object]:
        """
        تحليل رد الذكاء الاصطناعي كـ JSON منظم.
        """
        cleaned_response = self._clean_json_block(response_text)
        parsed = json.loads(cleaned_response)
        if not isinstance(parsed, dict):
            raise ValueError("AI response did not contain a JSON object")
        return parsed

    def _clean_json_block(self, text: str) -> str:
        """استخراج JSON من نص قد يحتوي على Markdown code blocks."""
        text = text.strip()
        json_code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1].strip()
        return "{}"


def _count_steps(plan_data: dict[str, object]) -> int:
    """يحسب عدد خطوات الخطة بشكل آمن."""

    steps = plan_data.get("steps")
    return len(steps) if isinstance(steps, list) else 0
