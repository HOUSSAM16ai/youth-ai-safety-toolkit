
from unittest.mock import AsyncMock

import pytest

from app.core.domain.mission import MissionStatus
from app.services.overmind.orchestrator import OvermindOrchestrator


@pytest.mark.asyncio
async def test_arbitrate_mission_outcome_failures():
    orchestrator = OvermindOrchestrator(
        state_manager=AsyncMock(),
        executor=AsyncMock(),
        brain=AsyncMock()
    )

    # Test case: Failed task -> FAILED (previously PARTIAL_SUCCESS)
    result = {
        "execution": {
            "status": "partial_failure",
            "results": [{"name": "task1", "status": "failed"}]
        }
    }
    status = orchestrator._arbitrate_mission_outcome(result, mission_id=1)
    assert status == MissionStatus.FAILED

@pytest.mark.asyncio
async def test_arbitrate_mission_outcome_empty_search():
    orchestrator = OvermindOrchestrator(
        state_manager=AsyncMock(),
        executor=AsyncMock(),
        brain=AsyncMock()
    )

    # Test case: Empty search result -> FAILED
    result = {
        "execution": {
            "status": "success",
            "results": [
                {
                    "tool": "search_content",
                    "result": []
                }
            ]
        }
    }
    status = orchestrator._arbitrate_mission_outcome(result, mission_id=1)
    assert status == MissionStatus.FAILED

@pytest.mark.asyncio
async def test_arbitrate_mission_outcome_search_error_object():
    orchestrator = OvermindOrchestrator(
        state_manager=AsyncMock(),
        executor=AsyncMock(),
        brain=AsyncMock()
    )

    # Test case: Search result with error object -> FAILED
    result = {
        "execution": {
            "status": "success",
            "results": [
                {
                    "tool": "search_content",
                    "result": [{"type": "error", "content": "Error"}]
                }
            ]
        }
    }
    status = orchestrator._arbitrate_mission_outcome(result, mission_id=1)
    assert status == MissionStatus.FAILED
