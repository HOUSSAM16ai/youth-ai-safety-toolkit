"""
مُنشئ تقارير HTML للخريطة الحرارية | HTML Heatmap Report Generator.

هذا الملف مسؤول عن إنشاء تقارير تحليل الكود بصيغة HTML.
تم تبسيطه وتقسيمه وفق مبادئ SOLID و KISS.
"""

from pathlib import Path

from app.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    ProjectAnalysis,
)

from .html_templates import create_complete_html, create_file_row_html

logger = get_logger(__name__)


def _extract_code_smells(file_metrics) -> str:
    """
    استخراج الروائح البنيوية من metrics الملف.

    Args:
        file_metrics: كائن يحتوي على معلومات الملف

    Returns:
        str: نص يصف الروائح البنيوية أو "لا توجد"

    ملاحظة: كل فاصلة (,) تفصل بين رائحة بنيوية واضحة
    """
    smells = []

    if file_metrics.is_god_class:
        smells.append("God Class")

    if file_metrics.has_layer_mixing:
        smells.append("Layer Mixing")

    if file_metrics.has_cross_layer_imports:
        smells.append("Cross-Layer Imports")

    # الفاصلة (,) هنا تُستخدم لربط العناصر في نص واحد
    # join() تجمع القائمة إلى string واحد
    return ", ".join(smells) if smells else "لا توجد"


def _build_file_rows(analysis: ProjectAnalysis, max_files: int = 50) -> str:
    """
    بناء HTML لصفوف الملفات في الخريطة الحرارية.

    Args:
        analysis: نتائج تحليل المشروع
        max_files: الحد الأقصى لعدد الملفات المعروضة

    Returns:
        str: HTML كامل لجميع صفوف الملفات

    ملاحظة:
        - القوس [] يُستخدم للوصول إلى slice من القائمة
        - [:50] تعني أول 50 عنصر من القائمة
        - القوس () يُستخدم لاستدعاء الدالة
    """
    file_rows_html = []

    # القوس المربع [:max_files] يحدد عدد الملفات
    for file_metrics in analysis.files[:max_files]:
        smells_html = _extract_code_smells(file_metrics)

        # القوس () يستدعي الدالة بالمعاملات
        row_html = create_file_row_html(
            relative_path=file_metrics.relative_path,
            priority_tier=file_metrics.priority_tier,
            hotspot_score=file_metrics.hotspot_score,
            file_complexity=file_metrics.file_complexity,
            code_lines=file_metrics.code_lines,
            num_functions=file_metrics.num_functions,
            commits_last_12months=file_metrics.commits_last_12months,
            bugfix_commits=file_metrics.bugfix_commits,
            smells_html=smells_html,
        )

        # القوس () يستدعي method من الكائن list
        file_rows_html.append(row_html)

    # join() تجمع جميع صفوف HTML إلى string واحد
    # الفاصلة "" تعني عدم وجود فاصل بين العناصر
    return "".join(file_rows_html)


def generate_heatmap_html(analysis: ProjectAnalysis, output_path: Path) -> None:
    """
    إنشاء تقرير HTML كامل للخريطة الحرارية.

    Args:
        analysis: كائن ProjectAnalysis يحتوي على نتائج التحليل
        output_path: مسار Path لحفظ ملف HTML

    Returns:
        None: الدالة لا تُرجع قيمة، فقط تكتب الملف

    ملاحظة توضيحية لكل رمز:
        - النقطة (.) تُستخدم للوصول إلى attributes أو methods
        - القوس () يستدعي دالة أو method
        - الفاصلة (,) تفصل بين المعاملات
        - القوسان {} في f-string يُدرج قيمة المتغير
        - الشرطة السفلية (_) تُشير إلى دالة خاصة (private)
    """
    # بناء HTML لجميع صفوف الملفات
    # القوس () يستدعي الدالة والفاصلة تفصل المعاملات
    file_rows_html = _build_file_rows(analysis, max_files=50)

    # إنشاء المستند HTML الكامل
    # كل معامل له دور واضح ومحدد
    html_content = create_complete_html(
        timestamp=analysis.timestamp,  # وقت الإنشاء
        total_files=analysis.total_files,  # إجمالي الملفات
        total_code_lines=analysis.total_code_lines,  # إجمالي الأسطر
        total_functions=analysis.total_functions,  # إجمالي الدوال
        total_classes=analysis.total_classes,  # إجمالي الكلاسات
        avg_file_complexity=analysis.avg_file_complexity,  # متوسط التعقيد
        max_file_complexity=analysis.max_file_complexity,  # أقصى تعقيد
        file_rows_html=file_rows_html,  # HTML للملفات
    )

    # كتابة المحتوى إلى الملف
    # with: يضمن إغلاق الملف تلقائياً
    # "w": وضع الكتابة (write mode)
    # encoding="utf-8": لدعم النصوص العربية
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # طباعة رسالة تأكيد
    # f-string تُدرج قيمة output_path في النص
    logger.info("💾 Heatmap HTML saved: %s", output_path)
