"""
محلل المكونات الأساسية.

يحدد الملفات الجوهرية في النظام ويعيد وصفًا موحدًا لها مع عدد الأسطر
لتسهيل التحليل والتوثيق.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.services.project_context.domain.models import KeyComponent


@dataclass(frozen=True)
class KeyFileSpec:
    """وصف ملف رئيسي ضمن النظام مع تعريفه ووصفه."""

    path: str
    name: str
    description: str


@dataclass
class ComponentAnalyzer:
    """محلل مسؤول عن استخراج المكونات الأساسية للنظام."""

    project_root: Path

    def analyze(self) -> list[KeyComponent]:
        """تحديد المكونات الجوهرية وإرجاعها ضمن قائمة منظمة."""
        components: list[KeyComponent] = []

        for spec in self._iter_key_files():
            full_path = self.project_root / spec.path
            if not full_path.exists():
                continue

            lines = self._safe_count_lines(full_path)
            if lines is None:
                continue

            components.append(
                KeyComponent(
                    name=spec.name,
                    path=spec.path,
                    description=spec.description,
                    lines=lines,
                )
            )

        return components

    def _iter_key_files(self) -> Iterator[KeyFileSpec]:
        """يبني قائمة الملفات الأساسية بطريقة واضحة وقابلة للتوسعة."""
        yield KeyFileSpec("app/main.py", "Application Entry Point", "FastAPI app creation")
        yield KeyFileSpec("app/core/database.py", "Database Engine", "Async database connections")
        yield KeyFileSpec(
            "app/core/domain/models.py",
            "Database Models",
            "SQLModel entities and relationships",
        )
        yield KeyFileSpec(
            "app/models.py",
            "Database Models",
            "Legacy SQLModel definitions",
        )
        yield KeyFileSpec("app/core/ai_gateway.py", "AI Gateway", "Neural routing mesh for AI")
        yield KeyFileSpec("app/core/prompts.py", "System Prompts", "OVERMIND identity and context")
        yield KeyFileSpec(
            "app/services/agent_tools/__init__.py",
            "Agent Tools",
            "File ops, search, reasoning",
        )
        yield KeyFileSpec("app/api/routers/admin.py", "Admin API", "Chat and admin endpoints")

    def _safe_count_lines(self, file_path: Path) -> int | None:
        """يحسب عدد الأسطر بأمان ويعيد None عند تعذر القراءة."""
        try:
            return len(file_path.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            return None
