from unittest.mock import patch

import pytest
from pydantic import SecretStr

from microservices.planning_agent.main import _generate_plan
from microservices.planning_agent.settings import PlanningAgentSettings


@pytest.mark.asyncio
async def test_generate_plan_success():
    """Test successful plan generation via Graph."""
    mock_settings = PlanningAgentSettings(
        OPENROUTER_API_KEY=SecretStr("sk-test"),
        AI_MODEL="test-model",
        AI_BASE_URL="http://test/api",
    )

    # Mock result matching the new structure in graph.py
    mock_result = {
        "plan": ["Step 1", "Step 2"],
        "strategy_name": "Test Strategy",
        "reasoning": "Test Reasoning",
        "iterations": 1,
    }

    # Patch the graph object imported in main.py
    with patch("microservices.planning_agent.main.graph") as mock_graph:
        mock_graph.invoke.return_value = mock_result

        result = await _generate_plan("Learn Python", [], mock_settings)

        # Expected result is now a dict
        assert result["steps"] == ["Step 1", "Step 2"]
        assert result["strategy_name"] == "Test Strategy"
        assert result["reasoning"] == "Test Reasoning"
        mock_graph.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_generate_plan_fallback_on_error():
    """Test fallback when Graph fails."""
    mock_settings = PlanningAgentSettings(OPENROUTER_API_KEY=SecretStr("sk-test"))

    with patch("microservices.planning_agent.main.graph") as mock_graph:
        mock_graph.invoke.side_effect = Exception("Graph Error")

        result = await _generate_plan("Learn Python", [], mock_settings)

        # Verify fallback structure
        assert isinstance(result, dict)
        assert result["strategy_name"] == "Fallback Strategy"
        steps = result["steps"]
        assert isinstance(steps, list)
        assert len(steps) >= 3
        # Check description in first step
        assert "Analyze Goal" in steps[0]["name"]


@pytest.mark.asyncio
async def test_generate_plan_fallback_no_key():
    """Test fallback when no API key is present."""
    mock_settings = PlanningAgentSettings(OPENROUTER_API_KEY=None)

    result = await _generate_plan("Learn Python", [], mock_settings)

    # Verify fallback structure
    assert isinstance(result, dict)
    assert result["strategy_name"] == "Fallback Strategy"
    steps = result["steps"]
    assert isinstance(steps, list)
    assert len(steps) >= 3
    assert "Analyze Goal" in steps[0]["name"]
