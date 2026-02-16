"""
الوحدات المعرفية باستخدام DSPy.

تحدد هذه الوحدة التواقيع (Signatures) والوحدات (Modules) للتخطيط والنقد.
"""

import importlib
import importlib.util
import json
from types import SimpleNamespace


def _dspy_dependencies_available() -> bool:
    """يتحقق من توفر اعتمادات DSPy اللازمة قبل الاستخدام."""

    required_specs = (
        "dspy",
        "litellm",
        "openai",
        "openai.types.beta.threads.message_content",
    )
    for spec in required_specs:
        try:
            if importlib.util.find_spec(spec) is None:
                return False
        except ModuleNotFoundError:
            return False
    return True


def _load_dspy() -> object | None:
    """يحاول تحميل DSPy مع توفير بدائل آمنة عند عدم توفر التبعيات."""

    if not _dspy_dependencies_available():
        return None

    return importlib.import_module("dspy")


_dspy_module = _load_dspy()

if _dspy_module is None:

    class _StubSignature:
        """بديل مبسط لتوقيعات DSPy عند عدم توفر المكتبة."""

    class _StubModule:
        """بديل مبسط لوحدات DSPy عند عدم توفر المكتبة."""

    def _stub_field(*args: object, **kwargs: object) -> None:
        return None

    class _StubChainOfThought:
        """يرفض الاستخدام الفعلي في حال غياب DSPy."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("DSPy غير متاح في بيئة التشغيل الحالية")

    dspy = SimpleNamespace(
        Signature=_StubSignature,
        Module=_StubModule,
        InputField=_stub_field,
        OutputField=_stub_field,
        ChainOfThought=_StubChainOfThought,
    )
else:
    dspy = _dspy_module


class GeneratePlan(dspy.Signature):
    """Generates a structured strategic plan based on an objective and context.
    The output must include a strategy name, reasoning, and a list of actionable steps.
    Each step must have a 'name', 'description', and an optional 'tool_hint' (e.g., search_content, reason_deeply, read_file)."""

    goal = dspy.InputField(desc="The main objective or mission goal.")
    context = dspy.InputField(desc="Relevant context, constraints, and available resources.")

    strategy_name = dspy.OutputField(desc="A creative and descriptive name for the strategy.")
    reasoning = dspy.OutputField(desc="Explanation of why this strategy was chosen.")
    plan_steps = dspy.OutputField(
        desc="A list of steps, where each step is a dictionary with keys: 'name', 'description', 'tool_hint'."
    )


class CritiquePlan(dspy.Signature):
    """Evaluates a strategic plan for feasibility, completeness, and clarity.
    Returns a score out of 10 and constructive feedback."""

    goal = dspy.InputField()
    plan_steps = dspy.InputField()
    score = dspy.OutputField(desc="Float score between 0.0 and 10.0")
    feedback = dspy.OutputField(desc="Specific advice on how to improve the plan.")


class PlanGenerator(dspy.Module):
    """Builds a strategic planning model."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GeneratePlan)

    def forward(self, goal: str, context: dict | list):
        """Executes the planning process."""
        context_str = json.dumps(context, default=str) if context else "No additional context."
        return self.generate(goal=goal, context=context_str)


class PlanCritic(dspy.Module):
    """Builds a plan critique model."""

    def __init__(self):
        super().__init__()
        self.critique = dspy.ChainOfThought(CritiquePlan)

    def forward(self, goal: str, plan_steps: list):
        """Executes the critique process."""
        plan_str = json.dumps(plan_steps, default=str)
        return self.critique(goal=goal, plan_steps=plan_str)
