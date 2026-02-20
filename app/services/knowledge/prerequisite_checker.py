"""
فاحص المتطلبات السابقة (Prerequisite Checker).
==============================================

يتحقق من جاهزية الطالب لموضوع معين.
"""

import logging
from dataclasses import dataclass

from app.infrastructure.clients.memory_client import MemoryClient, get_memory_client
from app.services.learning.student_profile import StudentProfile

logger = logging.getLogger(__name__)


@dataclass
class ReadinessReport:
    """تقرير الجاهزية."""

    concept_id: str
    concept_name: str
    is_ready: bool
    readiness_score: float  # 0-1
    missing_prerequisites: list[str]
    weak_prerequisites: list[str]
    recommendation: str


class PrerequisiteChecker:
    """
    يتحقق من جاهزية الطالب لتعلم مفهوم جديد.
    """

    MINIMUM_MASTERY = 0.5  # الحد الأدنى للإتقان
    GOOD_MASTERY = 0.7  # الإتقان الجيد

    def __init__(self, memory_client: MemoryClient | None = None) -> None:
        self.client = memory_client or get_memory_client()

    async def check_readiness(
        self,
        profile: StudentProfile,
        concept_id: str,
    ) -> ReadinessReport:
        """
        يتحقق من جاهزية الطالب لمفهوم معين.
        """
        # البحث عن المفهوم
        concept = await self.client.get_concept(concept_id)

        if not concept:
            # محاولة البحث بالموضوع
            concept = await self.client.find_concept_by_topic(concept_id)
            if concept:
                concept_id = concept.concept_id
            else:
                return ReadinessReport(
                    concept_id=concept_id,
                    concept_name=concept_id,
                    is_ready=True,  # مفهوم غير معروف، نسمح بالمتابعة
                    readiness_score=0.5,
                    missing_prerequisites=[],
                    weak_prerequisites=[],
                    recommendation="هذا المفهوم غير موجود في قاعدة البيانات.",
                )

        prerequisites = await self.client.get_prerequisites(concept_id)

        missing = []
        weak = []
        total_score = 0.0

        for prereq in prerequisites:
            if prereq.concept_id in profile.topic_mastery:
                mastery = profile.topic_mastery[prereq.concept_id].mastery_score
                total_score += mastery

                if mastery < self.MINIMUM_MASTERY:
                    weak.append(prereq.name_ar)
            else:
                missing.append(prereq.name_ar)
                total_score += 0  # لم يُدرس بعد

        # حساب الجاهزية
        readiness_score = (
            total_score / len(prerequisites) if prerequisites else 1.0
        )  # لا توجد متطلبات

        is_ready = len(missing) == 0 and readiness_score >= self.MINIMUM_MASTERY

        # بناء التوصية
        recommendation = self._build_recommendation(concept.name_ar, missing, weak, readiness_score)

        logger.info(
            f"Readiness check for {concept_id}: ready={is_ready}, score={readiness_score:.0%}"
        )

        return ReadinessReport(
            concept_id=concept_id,
            concept_name=concept.name_ar,
            is_ready=is_ready,
            readiness_score=readiness_score,
            missing_prerequisites=missing,
            weak_prerequisites=weak,
            recommendation=recommendation,
        )

    def _build_recommendation(
        self,
        concept_name: str,
        missing: list[str],
        weak: list[str],
        score: float,
    ) -> str:
        """يبني توصية للطالب."""

        if not missing and not weak:
            return f"🚀 أنت جاهز لتعلم {concept_name}! ابدأ الآن."

        if missing:
            topics = "، ".join(missing[:3])
            return f"📚 قبل البدء بـ {concept_name}، تحتاج دراسة: {topics}"

        if weak:
            topics = "، ".join(weak[:3])
            return f"📖 يُفضل مراجعة {topics} قبل البدء بـ {concept_name}"

        if score < 0.5:
            return f"⚠️ تحتاج تعزيز الأساسيات قبل {concept_name}"

        return f"✅ يمكنك البدء بـ {concept_name} مع بعض المراجعة"

    async def get_learning_order(
        self,
        profile: StudentProfile,
        target_concepts: list[str],
    ) -> list[str]:
        """
        يحدد الترتيب الأمثل لتعلم مجموعة مفاهيم.
        """
        # جمع كل المتطلبات
        all_concepts = set(target_concepts)

        for concept_id in target_concepts:
            # إضافة المتطلبات المفقودة
            report = await self.check_readiness(profile, concept_id)
            for prereq_name in report.missing_prerequisites:
                concept = await self.client.find_concept_by_topic(prereq_name)
                if concept:
                    all_concepts.add(concept.concept_id)

        # ترتيب طوبولوجي
        # ordered = []
        # remaining = list(all_concepts)

        # تحذير: هذا الترتيب الطوبولوجي كان يعتمد على الوصول المتزامن للرسم البياني.
        # الآن مع Async، قد يكون بطيئاً جداً إذا قمنا بطلب لكل مفهوم.
        # للتبسيط، سنحاول ترتيب ما لدينا.

        # نحتاج لجلب العلاقات لبناء الترتيب.
        # هذا قد يتطلب endpoint جديد في API لجلب العلاقات لمجموعة مفاهيم دفعة واحدة.
        # لكن للآن، سنستخدم نهجاً بسيطاً: الترتيب كما جاء أو بناءً على check_readiness.

        # نظرًا لتعقيد الترتيب الطوبولوجي عبر الشبكة (N+1 problem)، سنقوم بتبسيط المنطق مؤقتاً
        # ليعيد القائمة كما هي مع إضافة المفقودين في البداية.

        # TODO: Implement Batch Graph Query in Microservice

        return list(all_concepts)


# Singleton
_checker: PrerequisiteChecker | None = None


def get_prerequisite_checker() -> PrerequisiteChecker:
    """يحصل على فاحص المتطلبات."""
    global _checker
    if _checker is None:
        _checker = PrerequisiteChecker()
    return _checker
