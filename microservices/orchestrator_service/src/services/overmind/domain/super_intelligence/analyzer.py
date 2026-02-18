"""
محلل المواقف (Situation Analyzer).

مسؤول عن تحليل المواقف وفهم السياق بشكل عميق عبر إشارات كمية واضحة.
"""

from dataclasses import dataclass
from datetime import datetime

from app.core.di import get_logger
from microservices.orchestrator_service.src.services.overmind.domain.super_intelligence.expertise import (
    build_expertise_profile,
)

logger = get_logger(__name__)

_COMPLEXITY_KEYWORDS = ("complex", "difficult", "challenging", "معقد", "صعب")
_URGENCY_KEYWORDS = ("urgent", "critical", "immediate", "عاجل", "حرج", "فوري")
_NOVELTY_KEYWORDS = ("new", "novel", "innovative", "غير مسبوق", "ابتكار")
_DEFAULT_STAKEHOLDERS = ["system", "users", "developers", "overmind"]
_COMPLEXITY_SCORE_DIVISOR = 3
_URGENCY_SCORE_DIVISOR = 2
_NOVELTY_SCORE_DIVISOR = 2
_RISK_COMPLEXITY_WEIGHT = 0.5
_RISK_URGENCY_WEIGHT = 0.3
_RISK_NOVELTY_WEIGHT = 0.2
_STRATEGIC_NOVELTY_WEIGHT = 0.6
_STRATEGIC_OPPORTUNITY_WEIGHT = 0.4
_STRATEGIC_COMPLEXITY_WEIGHT = 0.2
_CONTEXT_RICHNESS_DIVISOR = 6
_NARRATIVE_WORD_DIVISOR = 40
_CONTEXT_RICHNESS_WEIGHT = 0.5
_SIGNAL_DIVERSITY_WEIGHT = 0.3
_NARRATIVE_DENSITY_WEIGHT = 0.2
_VERY_COMPLEX_TOKEN = "very complex"
_OPPORTUNITY_BONUS_DIVISOR = 5
_SIGNAL_DIVERSITY_DIVISOR = 3


@dataclass(frozen=True)
class WeightedFactor:
    """عامل موزون لتجميع القيم ضمن تقييم موحد."""

    name: str
    weight: float


_RISK_FACTORS = (
    WeightedFactor("complexity", _RISK_COMPLEXITY_WEIGHT),
    WeightedFactor("urgency", _RISK_URGENCY_WEIGHT),
    WeightedFactor("novelty", _RISK_NOVELTY_WEIGHT),
)
_STRATEGIC_FACTORS = (
    WeightedFactor("novelty", _STRATEGIC_NOVELTY_WEIGHT),
    WeightedFactor("opportunity", _STRATEGIC_OPPORTUNITY_WEIGHT),
    WeightedFactor("complexity", _STRATEGIC_COMPLEXITY_WEIGHT),
)
_DEPTH_FACTORS = (
    WeightedFactor("context_richness", _CONTEXT_RICHNESS_WEIGHT),
    WeightedFactor("signal_diversity", _SIGNAL_DIVERSITY_WEIGHT),
    WeightedFactor("narrative_density", _NARRATIVE_DENSITY_WEIGHT),
)


@dataclass(frozen=True)
class SignalDefinition:
    """تعريف موحد لإشارة التحليل لتقليل التكرار وتعزيز الاتساق."""

    name: str
    keywords: tuple[str, ...]
    divisor: int


_SIGNAL_DEFINITIONS = (
    SignalDefinition("complexity", _COMPLEXITY_KEYWORDS, _COMPLEXITY_SCORE_DIVISOR),
    SignalDefinition("urgency", _URGENCY_KEYWORDS, _URGENCY_SCORE_DIVISOR),
    SignalDefinition("novelty", _NOVELTY_KEYWORDS, _NOVELTY_SCORE_DIVISOR),
)


class SituationAnalyzer:
    """
    محلل المواقف الذكي.
    """

    @staticmethod
    async def analyze(
        situation: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        """
        تحليل الموقف بشكل شامل ومتعدد الأبعاد.

        Args:
            situation: وصف الموقف
            context: السياق والمعلومات الإضافية

        Returns:
            dict[str, object]: تحليل شامل (SWOT متقدم)
        """
        logger.info("Analyzing situation: %s...", situation[:50])

        normalized = SituationAnalyzer._normalize_text(situation)
        signal_scores = SituationAnalyzer._calculate_signal_scores(normalized)
        risk_index = SituationAnalyzer._aggregate_risk_index(signal_scores)
        strategic_value = SituationAnalyzer._estimate_strategic_value(signal_scores, context)
        depth_profile = SituationAnalyzer._build_depth_profile(situation, context, signal_scores)
        expertise_profile = build_expertise_profile(situation)

        analysis = SituationAnalyzer._build_base_analysis(
            situation=situation,
            signal_scores=signal_scores,
            risk_index=risk_index,
            strategic_value=strategic_value,
            depth_profile=depth_profile,
            expertise_profile=expertise_profile,
        )

        analysis["complexity_level"] = SituationAnalyzer._determine_complexity_level(normalized)
        analysis["urgency"] = SituationAnalyzer._determine_urgency(normalized)
        SituationAnalyzer._apply_context(analysis, context)

        logger.info(
            "Situation analyzed: complexity=%s, urgency=%s",
            analysis["complexity_level"],
            analysis["urgency"],
        )

        return analysis

    @staticmethod
    def _calculate_signal_scores(normalized: str) -> dict[str, float]:
        """
        استخراج درجات الإشارات الأساسية من وصف الموقف.

        Args:
            normalized: وصف الموقف بعد التوحيد

        Returns:
            dict[str, float]: درجات الإشارات (0.0 - 1.0)
        """
        scores: dict[str, float] = {}
        for definition in _SIGNAL_DEFINITIONS:
            score = SituationAnalyzer._score_keywords(
                normalized=normalized,
                keywords=definition.keywords,
                divisor=definition.divisor,
            )
            scores[definition.name] = SituationAnalyzer._round_score(score)

        return scores

    @staticmethod
    def _aggregate_risk_index(signal_scores: dict[str, float]) -> float:
        """
        دمج الإشارات لإنتاج مؤشر مخاطرة موحد.

        Args:
            signal_scores: درجات الإشارات الأساسية

        Returns:
            float: مؤشر المخاطرة (0.0 - 1.0)
        """
        risk_index = SituationAnalyzer._apply_weighted_factors(
            values=signal_scores,
            factors=_RISK_FACTORS,
        )
        return SituationAnalyzer._round_score(SituationAnalyzer._clamp_ratio(risk_index))

    @staticmethod
    def _estimate_strategic_value(
        signal_scores: dict[str, float],
        context: dict[str, object],
    ) -> float:
        """
        تقدير القيمة الاستراتيجية استناداً إلى الإشارات والسياق.

        Args:
            signal_scores: درجات الإشارات الأساسية
            context: سياق إضافي للمهمة

        Returns:
            float: قيمة استراتيجية (0.0 - 1.0)
        """
        opportunities = SituationAnalyzer._ensure_list(context.get("opportunities"))
        opportunity_bonus = SituationAnalyzer._calculate_opportunity_bonus(opportunities)
        inputs = {
            "novelty": signal_scores.get("novelty", 0.0),
            "opportunity": opportunity_bonus,
            "complexity": signal_scores.get("complexity", 0.0),
        }
        strategic_value = SituationAnalyzer._apply_weighted_factors(
            values=inputs,
            factors=_STRATEGIC_FACTORS,
        )
        return SituationAnalyzer._round_score(SituationAnalyzer._clamp_ratio(strategic_value))

    @staticmethod
    def _build_depth_profile(
        situation: str,
        context: dict[str, object],
        signal_scores: dict[str, float],
    ) -> dict[str, float]:
        """
        قياس عمق التحليل وفقاً لغنى المعطيات والسياق.

        Args:
            situation: وصف الموقف
            context: سياق إضافي للمهمة
            signal_scores: درجات الإشارات الأساسية

        Returns:
            dict[str, float]: ملف عمق التحليل ومكوناته
        """
        constraint_count, opportunity_count, threat_count = SituationAnalyzer._count_context_items(
            context
        )

        context_richness = SituationAnalyzer._normalize_ratio(
            float(constraint_count + opportunity_count + threat_count),
            _CONTEXT_RICHNESS_DIVISOR,
        )
        signal_diversity = SituationAnalyzer._calculate_signal_diversity(signal_scores)
        narrative_density = SituationAnalyzer._normalize_ratio(
            float(len(situation.split())),
            _NARRATIVE_WORD_DIVISOR,
        )

        depth_inputs = {
            "context_richness": context_richness,
            "signal_diversity": signal_diversity,
            "narrative_density": narrative_density,
        }
        depth_score = SituationAnalyzer._apply_weighted_factors(
            values=depth_inputs,
            factors=_DEPTH_FACTORS,
        )
        return {
            "context_richness": SituationAnalyzer._round_score(context_richness),
            "signal_diversity": SituationAnalyzer._round_score(signal_diversity),
            "narrative_density": SituationAnalyzer._round_score(narrative_density),
            "depth_score": SituationAnalyzer._round_score(
                SituationAnalyzer._clamp_ratio(depth_score),
            ),
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """يوحد النص لتسهيل المطابقة والتحليل دون التأثير على المعنى."""
        return text.strip().lower()

    @staticmethod
    def _count_keywords(text: str, keywords: tuple[str, ...]) -> int:
        """يحسب عدد الكلمات المفتاحية الموجودة في النص بعد التوحيد."""
        return sum(1 for keyword in keywords if keyword in text)

    @staticmethod
    def _score_keywords(
        *,
        normalized: str,
        keywords: tuple[str, ...],
        divisor: int,
    ) -> float:
        """يحول عدد الكلمات المفتاحية إلى درجة معيارية بين صفر وواحد."""
        count = SituationAnalyzer._count_keywords(normalized, keywords)
        return SituationAnalyzer._normalize_ratio(float(count), divisor)

    @staticmethod
    def _calculate_opportunity_bonus(opportunities: list[object]) -> float:
        """يحسب أثر الفرص المتاحة على القيمة الاستراتيجية."""
        return SituationAnalyzer._normalize_ratio(
            float(len(opportunities)),
            _OPPORTUNITY_BONUS_DIVISOR,
        )

    @staticmethod
    def _calculate_signal_diversity(signal_scores: dict[str, float]) -> float:
        """يحسب تنوع الإشارات لتحويله إلى مقياس موحد."""
        total = sum(signal_scores.get(definition.name, 0.0) for definition in _SIGNAL_DEFINITIONS)
        return SituationAnalyzer._normalize_ratio(total, _SIGNAL_DIVERSITY_DIVISOR)

    @staticmethod
    def _apply_weighted_factors(
        values: dict[str, float],
        factors: tuple[WeightedFactor, ...],
    ) -> float:
        """يجمع القيم وفق عوامل موزونة مع تجاهل المدخلات المفقودة."""
        return sum(values.get(factor.name, 0.0) * factor.weight for factor in factors)

    @staticmethod
    def _round_score(value: float) -> float:
        """يعيد القيمة مقربة إلى منزلتين عشريتين لضمان الاتساق."""
        return round(value, 2)

    @staticmethod
    def _normalize_ratio(numerator: float, divisor: int) -> float:
        """يضبط القيم النسبية داخل النطاق [0, 1] مع حماية القسمة."""
        if divisor <= 0:
            return 0.0
        return SituationAnalyzer._clamp_ratio(numerator / divisor)

    @staticmethod
    def _clamp_ratio(value: float) -> float:
        """يحصر القيمة ضمن المجال [0, 1] لتوحيد الدرجات."""
        return min(max(value, 0.0), 1.0)

    @staticmethod
    def _determine_complexity_level(normalized: str) -> str:
        """يحدد مستوى التعقيد بناءً على الكلمات المفتاحية ومُعززات الوصف."""
        complexity_score = SituationAnalyzer._count_keywords(normalized, _COMPLEXITY_KEYWORDS)
        if _VERY_COMPLEX_TOKEN in normalized:
            complexity_score += 1

        if complexity_score >= 2:
            return "high"
        if complexity_score == 1:
            return "medium"
        return "low"

    @staticmethod
    def _determine_urgency(normalized: str) -> str:
        """يحدد مستوى الإلحاح بناءً على الكلمات المفتاحية."""
        if SituationAnalyzer._count_keywords(normalized, _URGENCY_KEYWORDS) > 0:
            return "high"
        return "normal"

    @staticmethod
    def _ensure_list(value: object) -> list[object]:
        """يعيد قائمة آمنة حتى عند غياب أو عدم صحة البيانات المدخلة."""
        return value if isinstance(value, list) else []

    @staticmethod
    def _count_context_items(context: dict[str, object]) -> tuple[int, int, int]:
        """يعيد أعداد القيود والفرص والتهديدات من السياق بشكل منظم."""
        constraints = SituationAnalyzer._ensure_list(context.get("constraints"))
        opportunities = SituationAnalyzer._ensure_list(context.get("opportunities"))
        threats = SituationAnalyzer._ensure_list(context.get("threats"))
        return len(constraints), len(opportunities), len(threats)

    @staticmethod
    def _build_base_analysis(
        *,
        situation: str,
        signal_scores: dict[str, float],
        risk_index: float,
        strategic_value: float,
        depth_profile: dict[str, float],
        expertise_profile: dict[str, object],
    ) -> dict[str, object]:
        """يبني البنية الأساسية للتحليل قبل دمج السياق والتقييمات."""
        return {
            "situation": situation,
            "timestamp": datetime.utcnow().isoformat(),
            "complexity_level": "medium",
            "urgency": "normal",
            "complexity_score": signal_scores["complexity"],
            "urgency_score": signal_scores["urgency"],
            "novelty_score": signal_scores["novelty"],
            "risk_index": risk_index,
            "strategic_value_score": strategic_value,
            "depth_score": depth_profile["depth_score"],
            "depth_profile": depth_profile,
            "expertise_profile": expertise_profile,
            "stakeholders": [],
            "constraints": [],
            "opportunities": [],
            "threats": [],
        }

    @staticmethod
    def _apply_context(analysis: dict[str, object], context: dict[str, object]) -> None:
        """يدمج بيانات السياق في التحليل مع ضمان الاتساق."""
        analysis["constraints"] = SituationAnalyzer._ensure_list(context.get("constraints"))
        analysis["opportunities"] = SituationAnalyzer._ensure_list(context.get("opportunities"))
        analysis["threats"] = SituationAnalyzer._ensure_list(context.get("threats"))
        analysis["stakeholders"] = list(_DEFAULT_STAKEHOLDERS)
