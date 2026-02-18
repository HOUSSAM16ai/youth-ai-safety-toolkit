"""
نظام معرفة المستخدمين الشامل لـ Overmind (Comprehensive User Knowledge System).

هذا النظام يوفر لـ Overmind معرفة كاملة ومفصلة عن جميع المستخدمين من خلال
بنية معمارية نظيفة تفصل المسؤوليات.

المكونات (Components):
- service: واجهة موحدة (Facade) لجميع العمليات
- basic_info: المعلومات الأساسية للمستخدمين
- statistics: الإحصائيات والنشاطات
- performance: مقاييس الأداء
- relations: العلاقات مع الكيانات الأخرى
- search: البحث وعرض القوائم

المبادئ المطبقة:
- Single Responsibility: كل module مسؤول عن جانب واحد
- Separation of Concerns: فصل واضح بين المسؤوليات
- DRY: لا تكرار في الكود
- KISS: بساطة وسهولة الصيانة
"""

from microservices.orchestrator_service.src.services.overmind.user_knowledge.service import (
    UserKnowledge,
)

__all__ = ["UserKnowledge"]
