"""
ترسانة الأدوات الخارقة لقواعد البيانات (Super Database Tools Arsenal).

تم تقسيم هذا النظام إلى modules منفصلة حسب المسؤوليات:
- table_manager: إدارة الجداول (إنشاء، حذف، قائمة، تفاصيل)
- column_manager: إدارة الأعمدة (إضافة، حذف)
- data_manager: إدارة البيانات (إدخال، استعلام، تعديل، حذف)
- index_manager: إدارة الفهارس (إنشاء، حذف)
- query_executor: تنفيذ استعلامات SQL مخصصة
- operations_logger: تسجيل العمليات

المبدأ: Single Responsibility Principle (SOLID)
كل module مسؤول عن جزء واحد فقط من الوظائف.
"""

from microservices.orchestrator_service.src.services.overmind.database_tools.facade import (
    SuperDatabaseTools,
)

__all__ = ["SuperDatabaseTools"]
