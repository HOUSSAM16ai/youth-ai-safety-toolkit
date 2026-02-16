"""
سير عمل الرسم البياني لوكيل التخطيط (LangGraph Workflow).

يحدد آلة الحالة لتوليد الخطط، نقدها، وتحسينها.
"""

import ast
import json
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from microservices.planning_agent.cognitive import PlanCritic, PlanGenerator
from microservices.planning_agent.retrieval import rerank_context

logger = logging.getLogger("planning-agent")


class PlanningState(TypedDict):
    """تعريف الحالة للرسم البياني للتخطيط."""

    goal: str
    context: dict | list
    plan: list[dict]
    strategy_name: str
    reasoning: str
    score: float
    feedback: str
    iterations: int


def retrieve_node(state: PlanningState) -> dict:
    """يحسن السياق باستخدام LlamaIndex/Reranking."""
    logger.info("جاري استرجاع/إعادة ترتيب السياق...")
    # For now, pass context as is or enhance if needed.
    # Reranking usually expects list of strings. If context is dict, we might skip or flatten.
    ctx = state.get("context", [])
    if isinstance(ctx, list):
        refined_ctx = rerank_context(state["goal"], ctx)
        return {"context": refined_ctx}
    return {"context": ctx}


def generate_node(state: PlanningState) -> dict:
    """يولد خطة باستخدام DSPy."""
    logger.info(f"جاري توليد الخطة (التكرار {state.get('iterations', 0) + 1})...")

    generator = PlanGenerator()

    # إذا كان هناك ملاحظات من تكرار سابق، أضفها للسياق
    current_context = state.get("context", [])
    feedback = state.get("feedback")

    # Prepare context for generator
    gen_context = current_context
    if feedback:
        if isinstance(gen_context, list):
            gen_context = [*gen_context, f"Critique Feedback: {feedback}"]
        elif isinstance(gen_context, dict):
            gen_context = {**gen_context, "critique_feedback": feedback}

    try:
        pred = generator(goal=state["goal"], context=gen_context)

        raw_steps = pred.plan_steps
        strategy_name = getattr(pred, "strategy_name", "Generated Strategy")
        reasoning = getattr(pred, "reasoning", "No reasoning provided.")

        # Parsing logic for structured steps
        steps = []
        if isinstance(raw_steps, list):
            steps = raw_steps
        elif isinstance(raw_steps, str):
            try:
                clean = raw_steps.strip()
                if "```" in clean:
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                    clean = clean.strip()

                steps = json.loads(clean)
            except json.JSONDecodeError:
                try:
                    steps = ast.literal_eval(clean)
                except Exception:
                    # Fallback to simple string parsing if JSON fails
                    steps = [
                        {"name": "Step", "description": line, "tool_hint": None}
                        for line in clean.split("\n")
                        if line.strip()
                    ]

        if not isinstance(steps, list):
            steps = [{"name": "Plan Execution", "description": str(steps), "tool_hint": None}]

    except Exception as e:
        logger.error(f"فشل التوليد: {e}")
        steps = [{"name": "Error", "description": "Failed to generate plan.", "tool_hint": None}]
        strategy_name = "Error"
        reasoning = str(e)

    return {
        "plan": steps,
        "strategy_name": strategy_name,
        "reasoning": reasoning,
        "iterations": state.get("iterations", 0) + 1,
    }


def critique_node(state: PlanningState) -> dict:
    """ينقد الخطة باستخدام DSPy."""
    logger.info("جاري نقد الخطة...")

    critic = PlanCritic()
    try:
        # Convert plan dicts to string for critic
        plan_str = json.dumps(state["plan"], indent=2)
        pred = critic(goal=state["goal"], plan_steps=plan_str)

        # تحليل الدرجة
        try:
            raw_score = str(pred.score).split("/")[0].lower().replace("score:", "").strip()
            score = float(raw_score)
        except Exception:
            score = 5.0  # درجة افتراضية

        feedback = str(pred.feedback)
    except Exception as e:
        logger.error(f"فشل النقد: {e}")
        score = 0.0
        feedback = "خطأ أثناء النقد."

    logger.info(f"الدرجة: {score}, الملاحظات: {feedback}")
    return {"score": score, "feedback": feedback}


def should_continue(state: PlanningState):
    """يقرر ما إذا كان يجب التحسين أو الإنهاء."""
    # إذا كانت الدرجة جيدة (>= 7.0) أو وصلنا للحد الأقصى (3)، توقف.
    if state.get("score", 0) >= 7.0 or state.get("iterations", 0) >= 3:
        return END
    return "generate"


# بناء الرسم البياني
workflow = StateGraph(PlanningState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.add_node("critique", critique_node)

workflow.set_entry_point("retrieve")

workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "critique")

workflow.add_conditional_edges("critique", should_continue, {END: END, "generate": "generate"})

graph = workflow.compile()
