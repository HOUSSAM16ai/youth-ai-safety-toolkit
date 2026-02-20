import uuid
import re
from microservices.reasoning_agent.src.domain.models import ReasoningNode, EvaluationResult
from microservices.reasoning_agent.src.services.ai_service import ai_service
from microservices.reasoning_agent.src.core.logging import get_logger

logger = get_logger("mcts-strategy")

class RMCTSStrategy:
    """
    Recursive Monte Carlo Tree Search Strategy for Reasoning.
    """

    async def expand(self, parent: ReasoningNode, context: str) -> list[ReasoningNode]:
        """
        Generates N possible next steps/thoughts based on the parent.
        """
        prompt = (
            f"Context: {context}\n"
            f"Previous Thought: {parent.content}\n\n"
            "Task: Generate 3 distinct, high-quality reasoning steps or hypotheses to progress towards the answer.\n"
            "Format: Return ONLY a numbered list.\n"
            "1. [First Thought]\n"
            "2. [Second Thought]\n"
            "3. [Third Thought]"
        )

        try:
            content = await ai_service.generate_text(
                prompt=prompt,
                system_prompt="You are a Strategic Reasoning Engine. Think diversely and logically."
            )

            # Robust Parsing
            candidates = []
            # Regex to match numbered lines like "1. Text" or "1) Text" or "- Text"
            matches = re.findall(r"^(?:(?:\d+[.)])|[-*])\s*(.+)$", content, re.MULTILINE)

            if not matches:
                # Fallback: Split by newline if no numbering found
                matches = [line.strip() for line in content.split('\n') if line.strip()]

            for match in matches[:3]: # Limit to 3
                candidates.append(
                    ReasoningNode(
                        parent_id=parent.id,
                        content=match.strip(),
                        step_type="hypothesis"
                    )
                )

            return candidates

        except Exception as e:
            logger.error(f"Expansion failed: {e}")
            return []

    async def evaluate(self, node: ReasoningNode, context: str) -> EvaluationResult:
        """
        Reflective step: Score the thought against the context.
        """
        prompt = (
            f"Context: {context}\n"
            f"Proposed Thought: {node.content}\n\n"
            "Task: Evaluate this thought for accuracy, relevance, and logical soundness.\n"
            "Output format:\n"
            "Score: [0.0-1.0]\n"
            "Valid: [True/False]\n"
            "Reason: [Explanation]"
        )

        try:
            content = await ai_service.generate_text(
                prompt=prompt,
                system_prompt="You are a Critical Reviewer. Be strict."
            )

            # Simple parsing logic (can be upgraded to Instructor later)
            score = 0.5
            is_valid = True
            reasoning = content

            lower_content = content.lower()

            # Extract Score
            score_match = re.search(r"score:\s*([0-9.]+)", lower_content)
            if score_match:
                try:
                    score = float(score_match.group(1))
                except ValueError:
                    pass

            # Extract Validity
            if "valid: false" in lower_content or "valid: no" in lower_content:
                is_valid = False

            return EvaluationResult(score=score, is_valid=is_valid, reasoning=reasoning)

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return EvaluationResult(score=0.0, is_valid=False, reasoning=f"Error: {str(e)}")

    async def execute(self, root_content: str, context: str, depth: int = 2) -> ReasoningNode:
        """
        Executes the search strategy.
        """
        logger.info(f"Starting MCTS with depth {depth}")
        root = ReasoningNode(content=root_content, step_type="root", value=1.0)

        current_layer = [root]

        for i in range(depth):
            logger.info(f"Depth {i+1}: Expanding {len(current_layer)} nodes")
            next_layer = []

            for node in current_layer:
                children = await self.expand(node, context)
                node.children = children

                for child in children:
                    eval_result = await self.evaluate(child, context)
                    child.evaluation = eval_result
                    child.value = eval_result.score

                    if child.evaluation.is_valid and child.evaluation.score > 0.4:
                        next_layer.append(child)

            # Selection: Sort by value and keep top 2
            next_layer.sort(key=lambda x: x.value, reverse=True)
            current_layer = next_layer[:2]

            if not current_layer:
                logger.warning("No valid paths found in this layer.")
                break

        # Return best leaf
        if not current_layer:
            return root
        return current_layer[0]

mcts_strategy = RMCTSStrategy()
