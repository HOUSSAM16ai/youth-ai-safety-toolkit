"""
Intent handlers using Strategy pattern.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

# Import chat domain to ensure AdminConversation is registered, preventing mapping errors
import app.core.domain.chat  # noqa: F401
from app.core.agents.system_principles import (
    format_architecture_system_principles,
    format_system_principles,
)
from app.core.patterns.strategy import Strategy
from app.services.chat.context import ChatContext

logger = logging.getLogger(__name__)


class IntentHandler(Strategy[ChatContext, AsyncGenerator[str | dict, None]]):
    """Base intent handler."""

    def __init__(self, intent_name: str, priority: int = 0):
        self._intent_name = intent_name
        self._priority = priority

    async def can_handle(self, context: ChatContext) -> bool:
        """Check if handler can process this intent."""
        return context.intent == self._intent_name

    @property
    def priority(self) -> int:
        return self._priority


class FileReadHandler(IntentHandler):
    """Handle file read requests."""

    def __init__(self):
        super().__init__("FILE_READ", priority=10)

    async def execute(self, context: ChatContext) -> AsyncGenerator[str, None]:
        """Execute file read."""
        path = context.get_param("path", "")

        if not path:
            yield "❌ لم يتم تحديد مسار الملف\n"
            return

        try:
            yield f"📖 قراءة الملف: `{path}`\n\n"
            content = await self._read_file(path)
            yield f"```\n{content}\n```\n"
            logger.info(f"File read successful: {path}", extra={"user_id": context.user_id})
        except FileNotFoundError:
            yield f"❌ الملف غير موجود: `{path}`\n"
        except PermissionError:
            yield f"❌ لا توجد صلاحية لقراءة الملف: `{path}`\n"
        except Exception as e:
            yield f"❌ خطأ في قراءة الملف: {e!s}\n"
            logger.error(f"File read error: {e}", extra={"path": path, "user_id": context.user_id})

    async def _read_file(self, path: str) -> str:
        """Read file contents in a non-blocking way."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._read_file_sync(path))

    def _read_file_sync(self, path: str) -> str:
        """Synchronous file read."""
        with open(path, encoding="utf-8") as f:
            return f.read()


class FileWriteHandler(IntentHandler):
    """Handle file write requests."""

    def __init__(self):
        super().__init__("FILE_WRITE", priority=10)

    async def execute(self, context: ChatContext) -> AsyncGenerator[str, None]:
        """Execute file write."""
        path = context.get_param("path", "")

        if not path:
            yield "❌ لم يتم تحديد مسار الملف\n"
            return

        yield f"📝 لإنشاء ملف `{path}`، يرجى تحديد المحتوى.\n"
        yield "يمكنك كتابة المحتوى في الرسالة التالية.\n"


class CodeSearchHandler(IntentHandler):
    """Handle code search requests."""

    def __init__(self):
        super().__init__("CODE_SEARCH", priority=10)

    async def execute(self, context: ChatContext) -> AsyncGenerator[str, None]:
        """Execute code search."""
        query = context.get_param("query", "")

        if not query:
            yield "❌ لم يتم تحديد استعلام البحث\n"
            return

        yield f"🔍 البحث عن: `{query}`\n\n"
        results = await self._search_code(query, context.user_id)

        if not results:
            yield "لم يتم العثور على نتائج\n"
            return

        yield f"تم العثور على {len(results)} نتيجة:\n\n"
        for result in results:
            yield f"- `{result['file']}:{result['line']}`\n"

    async def _search_code(self, query: str, user_id: int) -> list[dict]:
        """Search code (placeholder)."""
        logger.info(f"Code search: {query}", extra={"user_id": user_id})
        return []


class ProjectIndexHandler(IntentHandler):
    """Handle project indexing requests."""

    def __init__(self):
        super().__init__("PROJECT_INDEX", priority=10)

    async def execute(self, context: ChatContext) -> AsyncGenerator[str, None]:
        """Execute project indexing."""
        yield "📊 فهرسة المشروع...\n\n"
        stats = await self._index_project(context.user_id)

        yield "✅ تمت الفهرسة بنجاح:\n"
        yield f"- الملفات: {stats.get('files', 0)}\n"
        yield f"- الأسطر: {stats.get('lines', 0)}\n"

    async def _index_project(self, user_id: int) -> dict:
        """Index project (placeholder)."""
        logger.info("Project indexing started", extra={"user_id": user_id})
        return {"files": 0, "lines": 0}


class DeepAnalysisHandler(IntentHandler):
    """Handle deep analysis requests."""

    def __init__(self):
        super().__init__("DEEP_ANALYSIS", priority=10)

    async def execute(self, context: ChatContext) -> AsyncGenerator[str, None]:
        """Execute deep analysis."""
        yield "🧠 تحليل عميق للسؤال...\n\n"

        analysis = await self._analyze(context.question, context.ai_client)

        yield f"{analysis}\n"

    async def _analyze(self, question: str, ai_client) -> str:
        """Perform deep analysis."""
        return "تحليل عميق (قيد التطوير)"

    def _build_identity_context(self) -> str:
        """
        بناء سياق الهوية التفصيلي لـ Overmind.

        Returns:
            str: نص هوية شامل للمؤسس ودور النظام.
        """
        founder = self._identity.get_founder_info()
        overmind = self._identity.get_overmind_info()
        principles_text = format_system_principles(
            header="المبادئ الصارمة للنظام (تُطبّق على الشيفرة بالكامل):",
            bullet="-",
            include_header=True,
        )
        architecture_principles_text = format_architecture_system_principles(
            header="مبادئ المعمارية وحوكمة البيانات (تُطبّق على الشيفرة بالكامل):",
            bullet="-",
            include_header=True,
        )
        return f"""أنت {overmind["name_ar"]} (Overmind)، {overmind["role_ar"]}.

معلومات المؤسس (مهمة جداً):
- الاسم الكامل: {founder["name_ar"]} ({founder["name"]})
- الاسم الأول: {founder["first_name_ar"]} ({founder["first_name"]})
- اللقب: {founder["last_name_ar"]} ({founder["last_name"]})
- تاريخ الميلاد: {founder["birth_date"]} (11 أغسطس 1997)
- الدور: {founder["role_ar"]} ({founder["role"]})
- GitHub: @{founder["github"]}

{principles_text}

{architecture_principles_text}

عندما يسأل أحد عن المؤسس أو مؤسس النظام أو من أنشأ Overmind، أجب بهذه المعلومات بدقة تامة.
"""
