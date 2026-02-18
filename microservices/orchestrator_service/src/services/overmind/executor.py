"""
محرك التنفيذ (Task Executor).
الذراع التنفيذي للنظام (The Hands).

المعايير:
- CS50 2025: توثيق عربي، صرامة في النوع.
- Dependency Injection: يعتمد على السجل (Registry) ومدير الحالة (State).
- SICP: Abstraction Barriers (لا يعرف تفاصيل التسجيل، فقط يستقبله).
"""

import asyncio
import inspect
import json
import logging
from collections.abc import Awaitable, Callable

from app.core.protocols import MissionStateManagerProtocol
from microservices.orchestrator_service.src.models.mission import Task
from microservices.orchestrator_service.src.services.overmind.tool_canonicalizer import (
    canonicalize_tool_name,
)

logger = logging.getLogger(__name__)

__all__ = ["TaskExecutor"]

# تعريف نوع السجل: قاموس يربط الاسم بدالة (متزامنة أو غير متزامنة)
# نستخدم object بدلاً من object للدلالة على أن النتيجة يمكن أن تكون أي شيء
type ToolRegistry = dict[str, Callable[..., Awaitable[object] | object]]


class TaskExecutor:
    """
    منفذ المهام.
    مسؤول عن استدعاء الأدوات وتشغيلها في بيئة آمنة.
    """

    def __init__(
        self,
        *,
        state_manager: MissionStateManagerProtocol,
        registry: ToolRegistry,
        tool_timeout_seconds: float = 60.0,
    ) -> None:
        """
        تهيئة المنفذ.

        Args:
            state_manager (MissionStateManagerProtocol): مدير الحالة (لتسجيل النتائج الجزئية إذا لزم الأمر).
            registry (ToolRegistry): سجل الأدوات المحقون (Dependency Injection).
            tool_timeout_seconds (float): حد زمني افتراضي لتنفيذ كل أداة (بالثواني).
        """
        self.state_manager = state_manager
        self.registry = registry
        self.tool_timeout_seconds = tool_timeout_seconds

        if not self.registry:
            logger.warning("TaskExecutor initialized with empty registry.")

    async def execute_task(self, task: Task) -> dict[str, object]:
        """
        تنفيذ مهمة واحدة باستخدام الأداة المحددة.

        Args:
            task (Task): كائن المهمة.

        Returns:
            dict[str, object]: نتيجة التنفيذ (status, result_text, meta, error).
        """
        tool_name = task.tool_name
        tool_args = self._parse_args(task.tool_args_json)

        # 1. التحقق من وجود السجل
        if not self.registry:
            return {"status": "failed", "error": "Agent tools registry is empty."}

        if not tool_name:
            return {"status": "failed", "error": "Task is missing tool_name."}

        resolved_name, canonical_notes = self._resolve_tool_name(tool_name, task.description or "")

        try:
            # 2. البحث عن الأداة
            tool_func = self.registry.get(resolved_name)

            if not tool_func:
                return {
                    "status": "failed",
                    "error": f"Tool '{resolved_name}' not found in registry.",
                    "meta": {
                        "tool": resolved_name,
                        "original_tool": tool_name,
                        "canonical_notes": canonical_notes,
                    },
                }

            # 3. التنفيذ (Execution)
            # دعم الأدوات المتزامنة وغير المتزامنة
            result = await self._execute_tool_with_timeout(tool_func, tool_args)

            # 4. تنسيق النتيجة
            result_text = str(result)
            result_data = None

            if isinstance(result, dict):
                result_text = json.dumps(result, default=str)
                result_data = result
            elif hasattr(result, "to_dict"):
                result_data = result.to_dict()
                result_text = json.dumps(result_data, default=str)

            return {
                "status": "success",
                "result_text": result_text,
                "result_data": result_data,
                "meta": {
                    "tool": resolved_name,
                    "original_tool": tool_name,
                    "canonical_notes": canonical_notes,
                },
            }

        except TimeoutError:
            logger.error("Task Execution Timeout (%s)", tool_name)
            return {
                "status": "failed",
                "error": "Tool execution timed out.",
                "meta": {
                    "tool": resolved_name,
                    "original_tool": tool_name,
                    "canonical_notes": canonical_notes,
                },
            }
        except Exception as e:
            logger.error(f"Task Execution Error ({tool_name}): {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "meta": {
                    "tool": resolved_name,
                    "original_tool": tool_name,
                    "canonical_notes": canonical_notes,
                },
            }

    async def _execute_tool_with_timeout(
        self, tool_func: Callable[..., Awaitable[object] | object], tool_args: dict[str, object]
    ) -> object:
        """
        تنفيذ الأداة مع تطبيق حد زمني لضمان عدم التعليق.
        """
        timeout = self._normalize_timeout(self.tool_timeout_seconds)
        if asyncio.iscoroutinefunction(tool_func):
            return await asyncio.wait_for(tool_func(**tool_args), timeout=timeout)

        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: tool_func(**tool_args)), timeout=timeout
        )
        if inspect.isawaitable(result):
            return await asyncio.wait_for(result, timeout=timeout)
        return result

    def _normalize_timeout(self, timeout: float) -> float:
        """
        توحيد قيمة الحد الزمني بحيث تكون ضمن نطاق آمن.
        """
        try:
            normalized = float(timeout)
        except (TypeError, ValueError):
            return 60.0
        if normalized <= 0:
            return 60.0
        return min(normalized, 300.0)

    def _parse_args(self, args_json: str | dict[str, object] | None) -> dict[str, object]:
        """
        تحليل وسائط الأداة بشكل آمن.

        Args:
            args_json: سلسلة نصية JSON أو قاموس أو None.

        Returns:
            dict: قاموس الوسائط.
        """
        if args_json is None:
            return {}
        if isinstance(args_json, dict):
            return args_json
        try:
            parsed = json.loads(args_json)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except json.JSONDecodeError:
            logger.warning("Failed to decode tool arguments JSON.")
            return {}

    def _resolve_tool_name(self, tool_name: str, description: str) -> tuple[str, list[str]]:
        """
        توحيد اسم الأداة قبل التنفيذ لضمان التوافق مع سجل الأدوات.

        Args:
            tool_name: الاسم الخام للأداة القادمة من الوكلاء.
            description: وصف المهمة لاستخلاص النية عند الحاجة.

        Returns:
            tuple[str, list[str]]: الاسم الموحّد وملاحظات التوحيد.
        """
        canonical_name, notes = canonicalize_tool_name(tool_name, description)
        return canonical_name, notes
