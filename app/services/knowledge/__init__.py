"""
خدمات الرسم البياني المعرفي (Knowledge Services).
=================================================

تتضمن:
- PrerequisiteChecker: فاحص المتطلبات السابقة (Refactored to use Memory Service)

تتكامل مع:
- Memory Agent: عبر MemoryClient
- Reranker: لترتيب المتطلبات حسب الأهمية
- DSPy: لتحسين البحث عن المفاهيم
"""

from app.services.knowledge.prerequisite_checker import (
    PrerequisiteChecker,
    ReadinessReport,
    get_prerequisite_checker,
)

__all__ = [
    # Prerequisite Checker
    "PrerequisiteChecker",
    "ReadinessReport",
    "get_prerequisite_checker",
]
