"""
خدمة قدرات Overmind الموحدة (Unified Overmind Capabilities Service).

Facade Pattern يوفر واجهة موحدة لجميع قدرات Overmind.

المبادئ:
- Facade Pattern: واجهة بسيطة لنظام معقد
- Delegation: تفويض العمليات للمكونات المتخصصة
- Single Entry Point: نقطة دخول واحدة لجميع العمليات
"""

from pathlib import Path

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.capabilities.file_operations import (
    FileOperations,
)
from microservices.orchestrator_service.src.services.overmind.capabilities.shell_operations import (
    ShellOperations,
)

logger = get_logger(__name__)


class OvermindCapabilities:
    """
    قدرات Overmind الكاملة (Overmind Full Capabilities).

    يجمع جميع القدرات في واجهة واحدة:
    - عمليات الملفات
    - عمليات Shell
    - عمليات Git

    الاستخدام:
        >>> capabilities = OvermindCapabilities()
        >>> await capabilities.read_file("app/main.py")
        >>> await capabilities.execute_shell("git status")
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """تهيئة قدرات Overmind."""
        self.file_ops = FileOperations(project_root)
        self.shell_ops = ShellOperations()
        logger.info("OvermindCapabilities initialized")

    # =========================================================================
    # File operations (تفويض إلى FileOperations)
    # =========================================================================

    async def read_file(self, path: str | Path) -> str:
        """قراءة ملف."""
        return await self.file_ops.read_file(path)

    async def write_file(self, path: str | Path, content: str, overwrite: bool = False) -> bool:
        """كتابة ملف."""
        return await self.file_ops.write_file(path, content, overwrite)

    async def edit_file(self, path: str | Path, old_text: str, new_text: str) -> bool:
        """تعديل ملف."""
        return await self.file_ops.edit_file(path, old_text, new_text)

    async def delete_file(self, path: str | Path, force: bool = False) -> bool:
        """حذف ملف."""
        return await self.file_ops.delete_file(path, force)

    async def create_directory(self, path: str | Path) -> bool:
        """إنشاء مجلد."""
        return await self.file_ops.create_directory(path)

    async def list_directory(self, path: str | Path = ".") -> list[str]:
        """عرض محتويات مجلد."""
        return await self.file_ops.list_directory(path)

    # =========================================================================
    # Shell operations (تفويض إلى ShellOperations)
    # =========================================================================

    async def execute_shell(self, command: str, timeout: int = 30) -> dict[str, object]:
        """تنفيذ أمر Shell."""
        return await self.shell_ops.execute_command(
            command,
            cwd=self.file_ops.project_root,
            timeout=timeout,
        )

    # =========================================================================
    # Git operations (استخدام ShellOperations)
    # =========================================================================

    async def git_status(self) -> dict[str, object]:
        """عرض حالة Git."""
        return await self.execute_shell("git status")

    async def git_add(self, files: str = ".") -> dict[str, object]:
        """إضافة ملفات إلى Git staging."""
        return await self.execute_shell(f"git add {files}")

    async def git_commit(self, message: str) -> dict[str, object]:
        """إنشاء commit."""
        # تنظيف الرسالة من علامات الاقتباس الخطيرة
        safe_message = message.replace('"', '\\"')
        return await self.execute_shell(f'git commit -m "{safe_message}"')
