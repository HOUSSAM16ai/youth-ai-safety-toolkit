"""
Dec-POMDP canonical knowledge module.
Provides pure functions for building proof summaries and detecting related questions.
"""


def build_dec_pomdp_proof_summary() -> dict[str, object]:
    """
    Build a structured summary of the NEXP-complete proof for Dec-POMDP.
    """
    return {
        "title": "البرهان الكنسي لشمولية NEXP لمسألة Dec-POMDP ذات أفق محدود (وكيلان)",
        "membership": (
            "المشكلة في NEXP لأن السياسات المحلية قد تكون أسية، ويمكن "
            "تخمينها والتحقق من العائد المتوقع في وقت أسي."
        ),
        "reduction": {
            "source_problem": "Non-Deterministic Tiling Problem",
            "grid_encoding": "شبكة بحجم أسي 2^n × 2^n بترميز ثنائي للإحداثيات.",
            "observations": (
                "كل وكيل يرى فقط إحداثياته المحلية، ما يجبر السياسة على "
                "تعيين بلاطة لكل خانة بشكل مستقل."
            ),
            "actions": "كل وكيل يختار بلاطة من مجموعة T لموقعه الملاحظ.",
            "rewards": [
                "نفس الخانة: يجب تطابق البلاطين.",
                "جوار أفقي: (t1, t2) ∈ H.",
                "جوار رأسي: (t1, t2) ∈ V.",
                "حالات أخرى: مكافأة افتراضية لا تؤثر على الصحة.",
            ],
            "threshold": "اختيار R* = 1 يربط وجود سياسة مثلى بوجود تبليط صحيح.",
        },
        "centralized_failure": (
            "في التحكم المركزي يرى المتحكم الزوج كاملاً ويختار البلاط وفق العينة "
            "اللحظية، مما يلغي شرط الاتساق العالمي ويكسر الاختزال."
        ),
        "doc_path": "docs/architecture/dec_pomdp_nexp_proof.md",
    }


def build_dec_pomdp_consultation_payload(role: str) -> dict[str, object]:
    """
    Create a standard consultation payload for agents regarding Dec-POMDP proof.
    """
    recommendations = {
        "strategist": "اعتمد البرهان الكنسي بوصفه إطاراً للتفسير الرسمي.",
        "architect": "وثّق الاختزال كتصميم معرفي يدعم استقلالية الوكلاء.",
        "operator": "وفّر البرهان كمرجع تشغيلي للوكلاء مع تفاصيل المكافآت.",
        "auditor": "تثبيت البرهان كمعيار تحقق للاتساق اللامركزي.",
    }
    confidences = {
        "strategist": 96.0,
        "architect": 95.0,
        "operator": 94.0,
        "auditor": 95.0,
    }
    summary = build_dec_pomdp_proof_summary()
    return {
        "recommendation": recommendations.get(role, "اتباع البرهان الكنسي كمرجع موحد."),
        "confidence": confidences.get(role, 90.0),
        "details": summary,
    }


def format_dec_pomdp_proof_summary(summary: dict[str, object]) -> str:
    """
    Format Dec-POMDP proof summary as Arabic text.
    """
    reduction = summary["reduction"]
    rewards = "\n".join(f"- {item}" for item in reduction["rewards"])
    return (
        f"{summary['title']}\n"
        "1) الانتماء إلى NEXP:\n"
        f"- {summary['membership']}\n"
        "2) الاختزال من مشكلة التبليط غير الحتمية:\n"
        f"- المصدر: {reduction['source_problem']}\n"
        f"- الترميز: {reduction['grid_encoding']}\n"
        f"- الملاحظات: {reduction['observations']}\n"
        f"- الأفعال: {reduction['actions']}\n"
        "3) المكافآت المحلية:\n"
        f"{rewards}\n"
        f"4) العتبة: {reduction['threshold']}\n"
        "5) فشل التحكم المركزي:\n"
        f"- {summary['centralized_failure']}\n"
        f"مرجع التفصيل: {summary['doc_path']}"
    )


def is_dec_pomdp_proof_question(text: str) -> bool:
    """
    Check if the question is related to Dec-POMDP proof.
    """
    normalized = text.lower()
    keywords = [
        "dec-pomdp",
        "decpomdp",
        "nexp",
        "التبليط غير الحتمية",
        "التبليط غير الحتمي",
        "مشكلة التبليط",
        "برهان كنسي",
        "شمولية nexp",
    ]
    return any(keyword in normalized for keyword in keywords)
