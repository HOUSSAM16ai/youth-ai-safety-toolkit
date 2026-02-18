from collections import defaultdict
from pathlib import Path

from app.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    ProjectAnalysis,
)

logger = get_logger(__name__)


def generate_markdown_report(analysis: ProjectAnalysis, output_path: Path) -> None:
    """
    Generate comprehensive Markdown report for code analysis.

    توليد تقرير Markdown شامل لتحليل الكود.

    Args:
        analysis: Project analysis results
        output_path: Path to save the report
    """
    md = _build_report_header(analysis)
    md += _build_project_summary_section(analysis)
    md += _build_critical_hotspots_section(analysis)
    md += _build_high_hotspots_section(analysis)
    md += _build_priority_distribution_section(analysis)
    md += _build_structural_smells_section(analysis)
    md += _build_next_steps_section()
    md += _build_notes_section()

    _save_report(md, output_path)


def _build_report_header(analysis: ProjectAnalysis) -> str:
    """
    Build report header with title and timestamp.

    بناء رأس التقرير مع العنوان والتاريخ.
    """
    return f"""# 🔍 تقرير التحليل البنيوي للكود
**Phase 1: Structural Code Intelligence Analysis**

تم الإنشاء: {analysis.timestamp}

---

"""


def _build_project_summary_section(analysis: ProjectAnalysis) -> str:
    """
    Build project summary statistics section.

    بناء قسم إحصائيات ملخص المشروع.
    """
    return f"""## 📊 ملخص المشروع

| المقياس | القيمة |
|---------|--------|
| إجمالي الملفات المحللة | {analysis.total_files} |
| إجمالي الأسطر | {analysis.total_lines:,} |
| أسطر الكود (LOC) | {analysis.total_code_lines:,} |
| إجمالي الدوال | {analysis.total_functions} |
| إجمالي الكلاسات | {analysis.total_classes} |
| متوسط التعقيد للملف | {analysis.avg_file_complexity:.2f} |
| أقصى تعقيد للملف | {analysis.max_file_complexity} |

---

"""


def _build_critical_hotspots_section(analysis: ProjectAnalysis) -> str:
    """
    Build critical hotspots section with top 20 files.

    بناء قسم النقاط الساخنة الحرجة مع أعلى 20 ملف.
    """
    section = """## 🔥 Hotspots حرجة (Top 20)

الملفات التي تحتاج إلى معالجة فورية:

"""

    for i, path in enumerate(analysis.critical_hotspots, 1):
        file_m = next((f for f in analysis.files if f.relative_path == path), None)
        if file_m:
            section += f"{i}. **{path}**\n"
            section += f"   - درجة الخطورة: `{file_m.hotspot_score:.4f}` | "
            section += f"التعقيد: `{file_m.file_complexity}` | "
            section += f"التعديلات: `{file_m.commits_last_12months}` | "
            section += f"الأولوية: `{file_m.priority_tier}`\n\n"

    return section


def _build_high_hotspots_section(analysis: ProjectAnalysis) -> str:
    """
    Build high-priority hotspots section.

    بناء قسم النقاط الساخنة عالية الأولوية.
    """
    section = "\n---\n\n## ⚠️ Hotspots عالية (التالي 20)\n\n"

    for i, path in enumerate(analysis.high_hotspots, 1):
        file_m = next((f for f in analysis.files if f.relative_path == path), None)
        if file_m:
            section += f"{i}. **{path}** - درجة: `{file_m.hotspot_score:.4f}`\n"

    return section


def _build_priority_distribution_section(analysis: ProjectAnalysis) -> str:
    """
    Build priority distribution section.

    بناء قسم توزيع الأولويات.
    """
    priority_counts = defaultdict(int)
    for f in analysis.files:
        priority_counts[f.priority_tier] += 1

    return f"""\n---\n\n## 📈 توزيع الأولويات

- 🔴 حرجة (CRITICAL): {priority_counts["CRITICAL"]}
- 🟠 عالية (HIGH): {priority_counts["HIGH"]}
- 🟡 متوسطة (MEDIUM): {priority_counts["MEDIUM"]}
- 🟢 منخفضة (LOW): {priority_counts["LOW"]}

"""


def _build_structural_smells_section(analysis: ProjectAnalysis) -> str:
    """
    Build structural code smells detection section.

    بناء قسم اكتشاف الروائح البنيوية في الكود.
    """
    god_classes = [f for f in analysis.files if f.is_god_class]
    layer_mixing = [f for f in analysis.files if f.has_layer_mixing]
    cross_layer = [f for f in analysis.files if f.has_cross_layer_imports]

    return f"""---

## 🦨 الروائح البنيوية المكتشفة

- **God Classes**: {len(god_classes)} ملف
- **Layer Mixing**: {len(layer_mixing)} ملف
- **Cross-Layer Imports**: {len(cross_layer)} ملف

"""


def _build_next_steps_section() -> str:
    """
    Build recommended next steps section.

    بناء قسم الخطوات الموصى بها.
    """
    return """---

## 📋 الخطوات التالية

بناءً على هذا التحليل، يُوصى بالبدء في معالجة الملفات الحرجة أولاً:

1. تطبيق مبدأ المسؤولية الواحدة (SRP) على God Classes
2. إعادة التقسيم الطبقي للملفات ذات Layer Mixing
3. عكس التبعيات غير الصحيحة (Cross-Layer Imports)
4. تبسيط الدوال عالية التعقيد
5. تحسين الملفات الأكثر تعديلاً لتقليل الأخطاء المستقبلية

"""


def _build_notes_section() -> str:
    """
    Build notes and disclaimers section.

    بناء قسم الملاحظات والتنويهات.
    """
    return """---

## 📝 ملاحظات

- هذا التقرير يمثل baseline للمشروع الحالي
- يجب استخدامه كمرجع لقياس التحسينات بعد تطبيق SOLID
- جميع المقاييس قابلة لإعادة الإنتاج من خلال تشغيل الأداة مرة أخرى
- التركيز على الملفات الحرجة سيحقق أكبر تأثير إيجابي
"""


def _save_report(content: str, output_path: Path) -> None:
    """
    Save report content to file.

    حفظ محتوى التقرير إلى ملف.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("💾 Markdown report saved: %s", output_path)
