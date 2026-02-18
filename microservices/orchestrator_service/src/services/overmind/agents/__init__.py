"""
نظام الوكلاء الذكية (Intelligent Agents System).

هذا الملف يوفر واجهة موحدة للوصول إلى جميع الوكلاء في نظام Overmind.
كل وكيل له دور محدد ومسؤوليات واضحة.

المبادئ المطبقة:
- Single Responsibility: كل وكيل مسؤولية واحدة فقط
- Interface Segregation: واجهات محددة لكل نوع وكيل
- Dependency Inversion: الاعتماد على البروتوكولات لا التطبيقات

الوكلاء المتاحة (Available Agents):
---------------------------------------
1. StrategistAgent: المخطط الاستراتيجي
   - يحلل الأهداف ويفككها إلى خطوات
   - يستخدم التفكير الشجري (Tree of Thoughts)

2. ArchitectAgent: المصمم التقني
   - يحول الخطة إلى تصميم تقني قابل للتنفيذ
   - يحدد الأدوات والمعاملات المطلوبة

3. OperatorAgent: المنفذ الميداني
   - ينفذ المهام واحدة تلو الأخرى
   - يسجل النتائج والأخطاء

4. AuditorAgent: المدقق والمراجع
   - يراجع النتائج للتأكد من الجودة
   - يكتشف الأخطاء والحلقات المفرغة

التعاون بين الوكلاء (Agent Collaboration):
-------------------------------------------
الوكلاء يعملون معاً في pipeline متسلسل:

  Objective → [Strategist] → Plan → [Architect] → Design → [Operator] → Results → [Auditor] → Approval

كل وكيل:
- يستقبل مخرجات الوكيل السابق
- يعالجها حسب تخصصه
- يمرر النتائج للوكيل التالي
- يستخدم CollaborationContext للذاكرة المشتركة

الاستخدام (Usage):
------------------
    from microservices.orchestrator_service.src.services.overmind.agents import (
        StrategistAgent,
        ArchitectAgent,
        OperatorAgent,
        AuditorAgent,
        create_agent_council
    )

    # إنشاء مجلس الوكلاء
    council = await create_agent_council(ai_client, task_executor)

    # استخدام الوكلاء
    plan = await council.strategist.create_plan(objective, context)
    design = await council.architect.design_solution(plan, context)
    results = await council.operator.execute_tasks(design, context)
    review = await council.auditor.review_work(results, objective, context)
"""

from typing import NamedTuple

from microservices.orchestrator_service.src.core.ai_gateway import AIClient
from microservices.orchestrator_service.src.core.protocols import (
    AgentArchitect,
    AgentExecutor,
    AgentPlanner,
    AgentReflector,
)

from .architect import ArchitectAgent
from .auditor import AuditorAgent
from .operator import OperatorAgent
from .strategist import StrategistAgent

__all__ = [
    "AgentCouncil",
    "ArchitectAgent",
    "AuditorAgent",
    "OperatorAgent",
    "StrategistAgent",
    "create_agent_council",
]


class AgentCouncil(NamedTuple):
    """
    مجلس الوكلاء (Council of Agents).

    يجمع جميع الوكلاء في هيكل واحد لسهولة الوصول والإدارة.

    Attributes:
        strategist: الوكيل الاستراتيجي (المخطط)
        architect: الوكيل المعماري (المصمم)
        operator: الوكيل المنفذ (المشغل)
        auditor: الوكيل المدقق (المراجع)

    ملاحظة:
        - NamedTuple تُستخدم لإنشاء هيكل بيانات بسيط وثابت (immutable)
        - كل وكيل يتبع بروتوكولاً محدداً (AgentPlanner, AgentArchitect, إلخ)
    """

    strategist: AgentPlanner  # المخطط: يفكك الأهداف إلى خطوات
    architect: AgentArchitect  # المصمم: يحول الخطوات إلى مهام تقنية
    operator: AgentExecutor  # المنفذ: ينفذ المهام الواحدة تلو الأخرى
    auditor: AgentReflector  # المدقق: يراجع النتائج ويتأكد من الجودة


async def create_agent_council(
    ai_client: AIClient,
    task_executor,  # من نوع TaskExecutor
) -> AgentCouncil:
    """
    إنشاء مجلس الوكلاء مع جميع التبعيات المطلوبة.

    هذه دالة مصنع (Factory Function) توفر طريقة بسيطة لإنشاء
    جميع الوكلاء دفعة واحدة مع التبعيات الصحيحة.

    Args:
        ai_client: عميل الذكاء الاصطناعي للوكلاء التي تحتاج LLM
        task_executor: محرك تنفيذ المهام للوكيل المنفذ

    Returns:
        AgentCouncil: مجلس يحتوي على جميع الوكلاء الجاهزة للعمل

    مثال (Example):
        >>> ai_client = AIClient(...)
        >>> executor = TaskExecutor(...)
        >>> council = await create_agent_council(ai_client, executor)
        >>> plan = await council.strategist.create_plan("Build API", context)

    ملاحظة توضيحية:
        - القوس () يستدعي الكونستركتر (Constructor) للكلاس
        - الفاصلة (,) تفصل بين المعاملات
        - النقطة (.) تصل إلى attribute أو method
        - الشرطة السفلية (_) في أسماء الدوال تشير إلى دالة خاصة
    """
    # إنشاء كل وكيل مع التبعيات المناسبة
    # كل سطر يُنشئ كائن وكيل جديد
    strategist = StrategistAgent(ai_client)  # يحتاج AI لإنشاء الخطط
    architect = ArchitectAgent(ai_client)  # يحتاج AI لتصميم المهام
    operator = OperatorAgent(task_executor, ai_client)  # يحتاج executor و AI للاستشارة
    auditor = AuditorAgent(ai_client)  # يحتاج AI لمراجعة النتائج

    # إرجاع المجلس كـ NamedTuple
    # القوس () هنا ينشئ instance من AgentCouncil
    return AgentCouncil(
        strategist=strategist,  # المخطط
        architect=architect,  # المصمم
        operator=operator,  # المنفذ
        auditor=auditor,  # المدقق
    )
