"""
نظام قدرات Overmind - التعديل على المشروع (Overmind Capabilities System).

هذا النظام يوفر لـ Overmind القدرة الكاملة على التعامل مع المشروع من خلال
بنية معمارية نظيفة تفصل المسؤوليات.

المكونات (Components):
- service: واجهة موحدة (Facade) لجميع العمليات
- file_operations: عمليات الملفات والمجلدات
- shell_operations: تنفيذ أوامر Shell

المبادئ المطبقة:
- Safety First: التحقق من الصلاحيات والأمان
- Single Responsibility: كل module مسؤول عن نوع واحد من العمليات
- Facade Pattern: واجهة بسيطة لنظام معقد
- Logging: تسجيل جميع العمليات
"""

from microservices.orchestrator_service.src.services.overmind.capabilities.file_operations import (
    FileOperations,
)
from microservices.orchestrator_service.src.services.overmind.capabilities.service import (
    OvermindCapabilities,
)
from microservices.orchestrator_service.src.services.overmind.capabilities.shell_operations import (
    ShellOperations,
)

__all__ = [
    "FileOperations",
    "OvermindCapabilities",
    "ShellOperations",
]
