"""
عمليات Shell الآمنة (Safe Shell Operations).

يوفر تنفيذ آمن لأوامر Shell.

المبادئ:
- Safety First: استخدام قائمة بيضاء للأوامر
- Single Responsibility: فقط تنفيذ Shell
- Logging: تسجيل جميع الأوامر
"""

# from app.core.di import get_logger -> Need to fix DI import too?
import logging
import shlex
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class ShellOperations:
    """
    عمليات Shell (Shell Operations).

    توفر تنفيذ آمن لأوامر Shell.

    تحذير:
        - ⚠️ استخدام أوامر Shell خطير!
        - ⚠️ لا تثق بمدخلات المستخدم
        - ⚠️ استخدم القائمة البيضاء للأوامر المسموحة
    """

    def __init__(self) -> None:
        """تهيئة نظام عمليات Shell."""
        # الأوامر المسموحة (Whitelist)
        self.allowed_commands = {
            "git",
            "python",
            "pytest",
            "pip",
            "ls",
            "cat",
            "grep",
            "find",
        }

    async def execute_command(
        self,
        command: str,
        cwd: Path | None = None,
        timeout: int = 30,
    ) -> dict[str, object]:
        """
        تنفيذ أمر Shell.

        Args:
            command: الأمر المراد تنفيذه
            cwd: المجلد الحالي للتنفيذ
            timeout: المهلة الزمنية بالثواني

        Returns:
            dict: نتيجة التنفيذ (stdout, stderr, returncode)
        """
        # استخراج الأمر الأول
        command_name = command.split(maxsplit=1)[0] if command.strip() else ""

        # التحقق من القائمة البيضاء
        if command_name not in self.allowed_commands:
            logger.error(f"Command not allowed: {command_name}")
            return {
                "success": False,
                "error": f"Command '{command_name}' is not in the allowed list",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

        try:
            # تنفيذ الأمر
            logger.info(f"Executing command: {command}")

            # Use shlex to split arguments and disable shell=True
            args = shlex.split(command)

            # Double check the command after split
            if not args or args[0] not in self.allowed_commands:
                return {
                    "success": False,
                    "error": f"Command '{args[0] if args else ''}' is not in the allowed list",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                }

            result = subprocess.run(
                args,
                check=False,
                shell=False,  # Secure
                cwd=cwd,
                timeout=timeout,
                capture_output=True,
                text=True,
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }
