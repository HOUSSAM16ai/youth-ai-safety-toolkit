from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from microservices.reasoning_agent.main import app
from microservices.reasoning_agent.src.domain.models import ReasoningNode
from microservices.reasoning_agent.src.services.strategies.mcts import RMCTSStrategy

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_mcts_strategy_expand():
    # Mock AI Service
    mock_ai = AsyncMock()
    mock_ai.generate_text.return_value = "1. First Idea\n2. Second Idea\n3. Third Idea"

    with patch("microservices.reasoning_agent.src.services.strategies.mcts.ai_service", mock_ai):
        strategy = RMCTSStrategy()
        parent = ReasoningNode(content="Root", step_type="root")

        candidates = await strategy.expand(parent, "context")

        assert len(candidates) == 3
        assert candidates[0].content == "First Idea"
        assert candidates[0].step_type == "hypothesis"


@pytest.mark.asyncio
async def test_mcts_strategy_evaluate():
    # Mock AI Service
    mock_ai = AsyncMock()
    mock_ai.generate_text.return_value = "Score: 0.8\nValid: True\nReason: Good logic."

    with patch("microservices.reasoning_agent.src.services.strategies.mcts.ai_service", mock_ai):
        strategy = RMCTSStrategy()
        node = ReasoningNode(content="Idea", step_type="hypothesis")

        result = await strategy.evaluate(node, "context")

        assert result.score == 0.8
        assert result.is_valid
        assert "Good logic" in result.reasoning


@patch("microservices.reasoning_agent.src.services.reasoning_service.reasoning_workflow.run")
def test_execute_endpoint(mock_workflow_run):
    # Mocking the async run method requires setting the return value to an awaitable/future
    # However, patch handles AsyncMock automatically if it detects async context,
    # but here we are patching a method on an instance.

    # Since reasoning_workflow.run is async, we should mock it as an AsyncMock
    mock_workflow_run.side_effect = AsyncMock(return_value="Final Answer")

    payload = {
        "caller_id": "test",
        "action": "reason",
        "payload": {"query": "Why is the sky blue?", "context": "Physics"},
    }

    # FastAPIs TestClient runs async endpoints synchronously in a thread loop
    response = client.post("/execute", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["answer"] == "Final Answer"

    mock_workflow_run.assert_called_once()
