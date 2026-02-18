# app/services/overmind/agents/operator.py
"""
الوكيل المنفذ (Operator Agent) - الذراع الضارب.
---------------------------------------------------------
يقوم هذا الوكيل باستلام التصميم التقني وتنفيذ المهام الواحدة تلو الأخرى
باستخدام محرك التنفيذ (TaskExecutor).

المعايير:
- CS50 2025 Strict Mode.
- توثيق "Legendary" باللغة العربية.
- استخدام واجهات صارمة.
"""

import asyncio
import json
import re

from app.core.di import get_logger
from app.core.protocols import AgentExecutor, CollaborationContext
from microservices.orchestrator_service.src.core.ai_gateway import AIClient
from microservices.orchestrator_service.src.models.mission import Task, TaskStatus
from microservices.orchestrator_service.src.services.overmind.dec_pomdp_proof import (
    build_dec_pomdp_consultation_payload,
    is_dec_pomdp_proof_question,
)
from microservices.orchestrator_service.src.services.overmind.executor import TaskExecutor

logger = get_logger(__name__)


class OperatorAgent(AgentExecutor):
    """
    المنفذ الميداني (The Executioner).

    المسؤوليات:
    1. استلام قائمة المهام (Tasks) من التصميم.
    2. المرور على المهام وتنفيذها بالتسلسل.
    3. تسجيل نتائج التنفيذ وتمريرها للمدقق.
    4. تقديم استشارات حول قابلية التنفيذ والموارد.
    """

    def __init__(self, task_executor: TaskExecutor, ai_client: AIClient | None = None) -> None:
        """
        تهيئة المنفذ.

        Args:
            task_executor: محرك تنفيذ المهام الفعلي.
            ai_client: عميل الذكاء الاصطناعي (اختياري للاستشارات).
        """
        self.executor = task_executor
        self.ai = ai_client

    async def execute_tasks(
        self, design: dict[str, object], context: CollaborationContext
    ) -> dict[str, object]:
        """
        تنفيذ المهام الواردة في التصميم.
        Execute tasks from the design plan.

        Args:
            design: التصميم التقني المحتوي على قائمة المهام
            context: السياق المشترك

        Returns:
            dict: تقرير التنفيذ الشامل
        """
        logger.info("Operator is starting execution...")

        # 1. التحقق من صحة التصميم | Validate design
        validation_result = self._validate_design(design)
        if validation_result:
            return validation_result

        # 2. استخراج المهام | Extract tasks
        tasks_data = design.get("tasks", [])
        if not tasks_data:
            return self._create_empty_tasks_report()

        # 3. تنفيذ المهام | Execute tasks
        logger.info(f"Operator: Executing {len(tasks_data)} tasks")
        results, overall_status = await self._execute_task_list(tasks_data, context)

        # 4. إنشاء التقرير النهائي | Create final report
        report = self._create_execution_report(overall_status, results)
        context.update("last_execution_report", report)
        return report

    async def consult(self, situation: str, analysis: dict[str, object]) -> dict[str, object]:
        """
        تقديم استشارة حول الموقف من منظور تشغيلي.
        Provide consultation on the situation from an operational perspective.

        Args:
            situation: وصف الموقف
            analysis: تحليل الموقف

        Returns:
            dict: التوصية والثقة
        """
        logger.info("Operator is being consulted...")

        if is_dec_pomdp_proof_question(situation):
            return build_dec_pomdp_consultation_payload("operator")

        if self.ai:
            return await self._consult_with_ai(situation, analysis)

        # Fallback if no AI is available
        return {
            "recommendation": "Check system resources and task queue availability.",
            "confidence": 80.0,
        }

    async def _consult_with_ai(
        self, situation: str, analysis: dict[str, object]
    ) -> dict[str, object]:
        """
        استخدام AI لتقديم الاستشارة.
        """
        system_prompt = """
        أنت "المشغل" (The Operator)، المسؤول عن التنفيذ العملي والموارد.
        دورك هو تحليل الموقف من منظور:
        1. توافر الموارد.
        2. قابلية التنفيذ العملي.
        3. المخاطر التشغيلية.

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
            logger.warning(f"Operator consultation failed: {e}")
            return {
                "recommendation": "Proceed with caution (AI consultation failed)",
                "confidence": 50.0,
            }

    def _validate_design(self, design: dict[str, object]) -> dict[str, object] | None:
        """
        التحقق من صحة التصميم.
        Validate design for errors.

        Returns:
            dict | None: تقرير خطأ إذا كان التصميم غير صالح، None إذا كان صالحاً
        """
        if "error" in design:
            logger.error(f"Operator received failed design: {design.get('error')}")
            return {
                "status": "failed",
                "tasks_executed": 0,
                "results": [],
                "error": f"Design failed: {design.get('error')}",
            }
        return None

    def _create_empty_tasks_report(self) -> dict[str, object]:
        """
        إنشاء تقرير للتصميم بدون مهام.
        Create report for design with no tasks.
        """
        logger.warning("Operator received design with no tasks")
        return {
            "status": "success",
            "tasks_executed": 0,
            "results": [],
            "note": "No tasks to execute",
        }

    async def _execute_task_list(
        self, tasks_data: list[dict[str, object]], context: CollaborationContext
    ) -> tuple[list[dict[str, object]], str]:
        """
        تنفيذ قائمة المهام.
        Execute list of tasks, optimizing for parallelism where safe.

        Returns:
            tuple: (النتائج، الحالة الإجمالية)
        """
        results = []
        overall_status = "success"

        # Parallelizable tools (Read-Only / Side-effect free)
        parallel_tools = {
            "search_content",
            "search_educational_content",
            "read_file",
            "retrieve",
            "deep_research",
            "get_content_raw",
        }

        i = 0
        while i < len(tasks_data):
            batch = []
            j = i

            # Identify a sequence of parallelizable tasks
            while j < len(tasks_data):
                task = tasks_data[j]
                tool = task.get("tool_name")
                if tool in parallel_tools:
                    batch.append((j, task))
                    j += 1
                else:
                    # If batch is empty, include this non-parallel task to execute it singly
                    if not batch:
                        batch.append((j, task))
                        j += 1
                    break

            # Execute the identified batch
            if len(batch) > 1:
                logger.info(f"Operator: Executing batch of {len(batch)} tasks in parallel...")
                futures = [
                    self._execute_single_task(idx, t, tasks_data, context) for idx, t in batch
                ]
                batch_results = await asyncio.gather(*futures)
                results.extend(batch_results)
            else:
                # Single execution
                idx, t = batch[0]
                result = await self._execute_single_task(idx, t, tasks_data, context)
                results.append(result)

            i = j

        # Check overall status
        for res in results:
            if res.get("status") == "skipped":
                continue
            if res.get("result", {}).get("status") == "failed":
                overall_status = "partial_failure"

        return results, overall_status

    async def _execute_single_task(
        self,
        index: int,
        task_def: dict[str, object],
        tasks_data: list[dict[str, object]],
        context: CollaborationContext,
    ) -> dict[str, object]:
        """
        تنفيذ مهمة واحدة.
        Execute a single task.
        """
        prepared_task = self._prepare_task_definition(task_def, context)
        task_name = prepared_task.get("name", f"Task-{index}")
        tool_name = prepared_task.get("tool_name")

        # التحقق من وجود أداة | Validate tool
        if not tool_name:
            logger.warning(f"Skipping task '{task_name}': No tool_name provided.")
            return {"name": task_name, "status": "skipped", "reason": "no_tool_name"}

        should_skip, skip_reason = self._should_skip_task(tool_name, context)
        if should_skip:
            logger.warning(f"Skipping task '{task_name}': {skip_reason}.")
            return {"name": task_name, "status": "skipped", "reason": skip_reason}

        logger.info(
            f"Executing Task [{index + 1}/{len(tasks_data)}]: {task_name} using {tool_name}"
        )

        # إنشاء المهمة وتنفيذها | Create and execute task
        temp_task = self._create_task_object(prepared_task, context)
        exec_result = await self._execute_task_safely(temp_task, task_name)

        return {"name": task_name, "tool": tool_name, "result": exec_result}

    def _create_task_object(
        self, task_def: dict[str, object], context: CollaborationContext
    ) -> Task:
        """
        إنشاء كائن مهمة مؤقت.
        Create ephemeral task object for execution.
        """
        mission_id = self._extract_mission_id(context)
        tool_args = task_def.get("tool_args", {})
        args_json = json.dumps(tool_args) if isinstance(tool_args, dict) else str(tool_args)

        return Task(
            mission_id=mission_id,
            name=task_def.get("name", "Unnamed Task"),
            tool_name=task_def.get("tool_name"),
            tool_args_json=args_json,
            status=TaskStatus.PENDING,
        )

    def _extract_mission_id(self, context: CollaborationContext) -> int:
        """
        استخراج معرف المهمة من السياق.
        Extract mission ID from context.
        """
        if hasattr(context, "shared_memory"):
            return context.shared_memory.get("mission_id", 0)
        return 0

    async def _execute_task_safely(self, task: Task, task_name: str) -> dict[str, object]:
        """
        تنفيذ المهمة مع معالجة الأخطاء.
        Execute task with error handling.
        """
        try:
            exec_result = await self.executor.execute_task(task)
            logger.info(
                f"Task '{task_name}' completed with status: {exec_result.get('status', 'unknown')}"
            )
            return exec_result
        except Exception as e:
            logger.exception(f"Task '{task_name}' raised exception: {e}")
            return {"status": "failed", "error": f"{type(e).__name__}: {e!s}"}

    def _create_execution_report(
        self, overall_status: str, results: list[dict[str, object]]
    ) -> dict[str, object]:
        """
        إنشاء تقرير التنفيذ النهائي.
        Create final execution report.
        """
        return {"status": overall_status, "tasks_executed": len(results), "results": results}

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

    def _prepare_task_definition(
        self, task_def: dict[str, object], context: CollaborationContext
    ) -> dict[str, object]:
        """
        تهيئة مهمة قبل التنفيذ عبر تنقية الوسائط وتغذية بيانات التمرين.

        الهدف: منع أخطاء الوسائط الشائعة وضمان تمرير بيانات الطلب التعليمي.
        """
        prepared = dict(task_def)
        tool_name = prepared.get("tool_name")
        raw_args = prepared.get("tool_args", {})
        tool_args = raw_args if isinstance(raw_args, dict) else {}

        if tool_name == "search_educational_content":
            tool_args = self._prepare_search_educational_args(tool_args, context)
            tool_name, tool_args = self._upgrade_search_tool(tool_name, tool_args)
        if tool_name in {"write_file", "write_file_if_changed", "append_file"}:
            tool_args = self._inject_exercise_content(tool_args, context)

        prepared["tool_name"] = tool_name
        prepared["tool_args"] = tool_args
        return prepared

    def _prepare_search_educational_args(
        self, tool_args: dict[str, object], context: CollaborationContext
    ) -> dict[str, object]:
        """
        تنقية وسائط البحث التعليمي وإضافة البيانات الناقصة من السياق.
        """
        normalized: dict[str, object] = {}
        allowed_keys = {"query", "year", "subject", "branch", "exam_ref", "exercise_id"}

        query_value = tool_args.get("query") or tool_args.get("q")
        if query_value:
            normalized["query"] = query_value

        metadata = self._get_exercise_metadata(context)
        for key in allowed_keys:
            if key in tool_args and tool_args.get(key):
                normalized[key] = tool_args[key]
            elif key in metadata and metadata.get(key):
                normalized[key] = metadata[key]

        if "query" not in normalized:
            objective = self._get_objective_from_context(context)
            if objective:
                normalized["query"] = objective

        return {key: value for key, value in normalized.items() if key in allowed_keys}

    def _upgrade_search_tool(
        self, tool_name: str | None, tool_args: dict[str, object]
    ) -> tuple[str | None, dict[str, object]]:
        """
        ترقية أداة البحث التعليمية القديمة إلى الأداة الحديثة مع ضبط الوسائط.
        """
        if tool_name != "search_educational_content":
            return tool_name, tool_args

        query = tool_args.get("query")
        exercise_id = tool_args.get("exercise_id")
        if exercise_id and query:
            query = f"{query} {exercise_id}"

        year_value = tool_args.get("year")
        year_int = None
        if isinstance(year_value, int):
            year_int = year_value
        elif isinstance(year_value, str) and year_value.isdigit():
            year_int = int(year_value)

        upgraded_args: dict[str, object] = {
            "q": query,
            "subject": tool_args.get("subject"),
            "branch": tool_args.get("branch"),
            "year": year_int,
            "set_name": tool_args.get("exam_ref"),
            "limit": 5,
        }
        return "search_content", {k: v for k, v in upgraded_args.items() if v}

    def _get_exercise_metadata(self, context: CollaborationContext) -> dict[str, object]:
        """
        قراءة بيانات التمرين من السياق المشترك.
        """
        if hasattr(context, "get"):
            metadata = context.get("exercise_metadata")
            if isinstance(metadata, dict):
                return metadata
        if hasattr(context, "shared_memory"):
            shared_memory = getattr(context, "shared_memory", {})
            if isinstance(shared_memory, dict):
                metadata = shared_memory.get("exercise_metadata")
                if isinstance(metadata, dict):
                    return metadata
        return {}

    def _get_objective_from_context(self, context: CollaborationContext) -> str | None:
        """
        استخراج الهدف الأصلي من السياق لاستخدامه كسؤال بحث.
        """
        if hasattr(context, "get"):
            value = context.get("objective")
            return value if isinstance(value, str) else None
        if hasattr(context, "shared_memory"):
            shared_memory = getattr(context, "shared_memory", {})
            if isinstance(shared_memory, dict):
                value = shared_memory.get("objective")
                return value if isinstance(value, str) else None
        return None

    def _inject_exercise_content(
        self, tool_args: dict[str, object], context: CollaborationContext
    ) -> dict[str, object]:
        """
        حقن نص التمرين داخل مهام الكتابة عند توفره في السياق.
        """
        content_value = tool_args.get("content")
        if isinstance(content_value, str) and content_value.strip():
            return tool_args

        exercise_content = None
        if hasattr(context, "get"):
            value = context.get("exercise_content")
            if isinstance(value, str):
                exercise_content = value
        if exercise_content is None and hasattr(context, "shared_memory"):
            shared_memory = getattr(context, "shared_memory", {})
            if isinstance(shared_memory, dict):
                value = shared_memory.get("exercise_content")
                if isinstance(value, str):
                    exercise_content = value

        if exercise_content:
            tool_args = dict(tool_args)
            tool_args["content"] = exercise_content
        return tool_args

    def _should_skip_task(self, tool_name: str, context: CollaborationContext) -> tuple[bool, str]:
        """
        تحديد ما إذا كان يجب تجاوز المهمة حمايةً لجودة المهمة الخارقة.

        الهدف: منع أدوات غير مناسبة عند طلب تمارين تعليمية حساسة، مع الإبقاء على الأدوات
        المعرفية المتخصصة التي تُنتج محتوى التمرين مباشرة.
        """
        if not tool_name:
            return True, "no_tool_name"

        has_exercise_context = False
        has_exercise_content = False

        if hasattr(context, "get"):
            has_exercise_content = bool(context.get("exercise_content"))
            has_exercise_context = bool(
                context.get("exercise_content") or context.get("exercise_metadata")
            )
        elif hasattr(context, "shared_memory"):
            shared_memory = getattr(context, "shared_memory", {})
            if isinstance(shared_memory, dict):
                has_exercise_content = bool(shared_memory.get("exercise_content"))
                has_exercise_context = bool(
                    shared_memory.get("exercise_content") or shared_memory.get("exercise_metadata")
                )

        if not has_exercise_context:
            return False, ""

        blocked_tools = {
            "run_shell",
            "execute_shell",
            "shell",
            "bash",
            "sh",
            "powershell",
            "cmd",
        }
        redundant_tools = {
            "read_file",
            "file_exists",
            "list_dir",
            "analyze_path_semantics",
        }
        if tool_name == "get_content_raw" and has_exercise_content:
            return True, "content_already_seeded"

        # Only block redundant tools if we actually have the content
        if tool_name in redundant_tools and has_exercise_content:
            return True, "redundant_with_seeded_content"

        if tool_name in blocked_tools:
            return True, "unsafe_tool_for_education_request"

        return False, ""
