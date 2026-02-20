import uuid
from typing import Literal

from pydantic import BaseModel, Field

# --- Unified Agent Protocol ---


class AgentRequest(BaseModel):
    """
    Request payload for executing an agent action.
    """

    caller_id: str = Field(..., description="Entity requesting the action")
    target_service: str = Field("reasoning-agent", description="Target service name")
    action: str = Field(..., description="Action to perform (e.g., 'reason')")
    payload: dict[str, object] = Field(default_factory=dict, description="Action arguments")
    security_token: str | None = Field(None, description="Auth token")


class AgentResponse(BaseModel):
    """
    Standardized response from an agent.
    """

    status: Literal["success", "error"] = Field(..., description="Execution status")
    data: object | None = Field(None, description="Result data")
    error: str | None = Field(None, description="Error message")
    metrics: dict[str, object] = Field(default_factory=dict, description="Performance metrics")


# --- Reasoning Models ---


class EvaluationResult(BaseModel):
    """Result of evaluating a reasoning step."""

    score: float = Field(..., ge=0.0, le=1.0, description="Quality score of the thought")
    is_valid: bool = Field(..., description="Whether the thought is logically valid")
    reasoning: str = Field(..., description="Explanation for the score")


class ReasoningNode(BaseModel):
    """A node in the reasoning tree (Tree of Thoughts)."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    content: str = Field(..., description="The thought content or hypothesis")
    step_type: str = Field("thought", description="Type of step: root, hypothesis, critique")
    value: float = Field(0.0, description="Accumulated value or score")
    children: list["ReasoningNode"] = Field(default_factory=list)
    evaluation: EvaluationResult | None = None

    # Enable recursive type definition
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123",
                "content": "Let's assume X is true...",
                "step_type": "hypothesis",
            }
        }
    }
