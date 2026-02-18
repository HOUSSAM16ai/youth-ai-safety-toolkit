# app/services/overmind/agents/architect.py
"""
الوكيل المعماري (Architect Agent) - المصمم التقني.
---------------------------------------------------------
يقوم هذا الوكيل بتحويل الخطة الاستراتيجية (النظرية) إلى تصميم تقني قابل للتنفيذ
(Technical Specification). يحدد الأدوات الدقيقة والمعاملات المطلوبة لكل خطوة.

المعايير:
- CS50 2025 Strict Mode.
- توثيق "Legendary" باللغة العربية.
- استخدام واجهات صارمة.
"""

import json
import re

from microservices.orchestrator_service.src.core.ai_gateway import AIClient
from microservices.orchestrator_service.src.core.logging import get_logger
from microservices.orchestrator_service.src.core.protocols import AgentArchitect, CollaborationContext
from microservices.orchestrator_service.src.services.overmind.dec_pomdp_proof import (
    build_dec_pomdp_consultation_payload,
    is_dec_pomdp_proof_question,
)

logger = get_logger(__name__)


class ArchitectAgent(AgentArchitect):
    """
    المهندس المعماري للنظام.

    المسؤوليات:
    1. ترجمة الخطوات البشرية (Human Steps) إلى مهام تقنية (Technical Tasks).
    2. اختيار الأدوات المناسبة من السجل (Tool Registry) لكل مهمة.
    3. صياغة المعاملات (Arguments) بصيغة JSON دقيقة.
    """

    def __init__(self, ai_client: AIClient) -> None:
        self.ai = ai_client

    async def design_solution(
        self, plan: dict[str, object], context: CollaborationContext
    ) -> dict[str, object]:
        """
        تحويل الخطة الاستراتيجية إلى تصميم تقني.
        Convert strategic plan to technical design.

        Args:
            plan: الخطة الناتجة عن الاستراتيجي (Strategist)
            context: السياق المشترك

        Returns:
            dict: تصميم يحتوي على قائمة المهام الجاهزة للتنفيذ
        """
        logger.info("Architect is designing the technical solution...")

        # 1. إعداد السياق والطلب | Prepare context and request
        system_prompt = self._create_architect_system_prompt()
        user_content = self._format_plan_for_design(plan)

        # 2. استدعاء AI للتصميم | Call AI for design
        try:
            design_data = await self._generate_design_with_ai(system_prompt, user_content)

            # 3. تخزين في السياق | Store in context
            context.update("last_design", design_data)
            return design_data

        except json.JSONDecodeError as e:
            return self._create_json_error_design(e)
        except Exception as e:
            return self._create_general_error_design(e)

    def _create_architect_system_prompt(self) -> str:
        """
        إنشاء توجيه النظام للمعماري.
        Create system prompt for the Architect agent.
        """
        return """
        أنت "المعماري" (The Architect)، خبير تقني ضمن منظومة Overmind.

        مهمتك:
        تحويل خطوات الخطة الاستراتيجية إلى مهام تقنية دقيقة قابلة للتنفيذ بواسطة أدوات النظام.

        الأدوات المتاحة (Common Tools):
        - read_file(path)
        - write_file(path, content)
        - list_files(path)
        - run_shell(command) (Use carefully)
        - git_status()
        - git_commit(message)
        - get_project_metrics()
        - count_files(directory, extension)
        - search_educational_content(query, year, subject, branch, exam_ref, exercise_id)
        - search_content(q, level, subject, branch, set_name, year, type, lang, limit)
        - get_content_raw(content_id, include_solution)

        القواعد:
        1. كل خطوة في الخطة يجب أن تتحول إلى مهمة واحدة أو أكثر.
        2. يجب تحديد اسم الأداة (tool_name) بدقة.
        3. معاملات الأداة (tool_args) يجب أن تكون JSON object.
        4. عند طلب تمرين أو محتوى تعليمي محدد، ابدأ بـ search_educational_content مع تمرير السنة والشعبة والموضوع ورقم التمرين، ثم استخدم get_content_raw إذا عاد معرف محتوى.
        5. المخرجات يجب أن تكون JSON صالح فقط.
        6. يفضل استخدام أدوات البحث الداخلية (search_content, search_educational_content)، ولكن يُسمح باستخدام `run_shell` للبحث في الإنترنت (curl/wget) عند الضرورة القصوى أو بطلب صريح من المستخدم للتحقق من المصادر الخارجية.

        صيغة JSON المطلوبة:
        {
            "design_name": "اسم التصميم",
            "tasks": [
                {
                    "name": "اسم المهمة",
                    "tool_name": "write_file",
                    "tool_args": {"path": "src/main.py", "content": "logger.info('hello')"},
                    "description": "وصف تقني"
                }
            ]
        }
        """

    def _format_plan_for_design(self, plan: dict[str, object]) -> str:
        """
        تنسيق الخطة للإرسال إلى AI.
        Format plan for sending to AI.
        """
        plan_str = json.dumps(plan, default=str)
        return f"Plan: {plan_str}\nConvert this into executable tasks."

    async def _generate_design_with_ai(
        self, system_prompt: str, user_content: str
    ) -> dict[str, object]:
        """
        توليد التصميم باستخدام AI.
        Generate design using AI with error handling.
        """
        logger.info("Architect: Calling AI for design generation...")
        response_text = await self.ai.send_message(
            system_prompt=system_prompt,
            user_message=user_content,
            temperature=0.1,  # دقة قصوى
        )
        logger.info(f"Architect: Received AI response ({len(response_text)} chars)")

        # تنظيف وتحليل الاستجابة | Clean and parse response
        cleaned_response = self._clean_json_block(response_text)
        design_data = json.loads(cleaned_response)

        # التحقق من الصحة | Validate
        if "tasks" not in design_data:
            raise ValueError("Design missing 'tasks' field")

        logger.info(f"Architect: Design created with {len(design_data.get('tasks', []))} tasks")
        return design_data

    def _create_json_error_design(self, error: json.JSONDecodeError) -> dict[str, object]:
        """
        إنشاء تصميم خطأ JSON.
        Create error design for JSON parsing failures.
        """
        logger.error(f"Architect JSON parsing error: {error}")
        return {
            "design_name": "Failed Design - JSON Error",
            "error": f"JSON parsing failed: {error}",
            "tasks": [],
        }

    def _create_general_error_design(self, error: Exception) -> dict[str, object]:
        """
        إنشاء تصميم خطأ عام.
        Create general error design.
        """
        logger.exception(f"Architect failed to design: {error}")
        return {
            "design_name": "Failed Design",
            "error": f"{type(error).__name__}: {error!s}",
            "tasks": [],
        }

    def _clean_json_block(self, text: str) -> str:
        """استخراج JSON من نص قد يحتوي على Markdown code blocks."""
        text = text.strip()

        # 1. محاولة استخراج JSON من كتل الكود (Markdown)
        json_code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_code_block_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 2. محاولة استخراج JSON من بين الأقواس (Outermost Braces)
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            return text[start : end + 1].strip()

        # 3. في حال عدم العثور على أي هيكل JSON، نعيد كائن فارغ نصي لتجنب الانهيار
        return "{}"

    async def consult(self, situation: str, analysis: dict[str, object]) -> dict[str, object]:
        """
        تقديم استشارة معمارية وتقنية.
        Provide architectural and technical consultation.

        Args:
            situation: وصف الموقف
            analysis: تحليل الموقف

        Returns:
            dict: التوصية والثقة
        """
        logger.info("Architect is being consulted...")

        if is_dec_pomdp_proof_question(situation):
            return build_dec_pomdp_consultation_payload("architect")

        system_prompt = """
        أنت "المعماري" (The Architect).
        دورك هو تحليل الموقف من منظور تقني ومعماري.

        النقاط الأساسية:
        1. الجدوى التقنية (Feasibility).
        2. قابلية التوسع (Scalability) والأداء.
        3. الأدوات والتقنيات المناسبة.

        قدم توصية موجزة ومباشرة.
        الرد يجب أن يكون JSON فقط:
        {
            "recommendation": "string (english)",
            "confidence": float (0-100)
        }
        """

        user_message = f"Situation: {situation}\nAnalysis: {json.dumps(analysis, default=str)}"

        try:
            response_text = await self.ai.send_message(
                system_prompt=system_prompt, user_message=user_message, temperature=0.3
            )

            clean_json = self._clean_json_block(response_text)
            return json.loads(clean_json)
        except Exception as e:
            logger.warning(f"Architect consultation failed: {e}")
            return {
                "recommendation": "Ensure technical feasibility and scalability (AI consultation failed).",
                "confidence": 50.0,
            }
