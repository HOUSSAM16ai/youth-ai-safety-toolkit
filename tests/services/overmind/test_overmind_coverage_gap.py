import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.overmind.factory as factory_module
from app.core.domain.models import Mission, MissionStatus
from app.services.overmind.domain.cognitive import SuperBrain
from app.services.overmind.executor import TaskExecutor
from app.services.overmind.factory import create_overmind
from app.services.overmind.orchestrator import OvermindOrchestrator
from app.services.overmind.state import MissionStateManager


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_state_manager():
    manager = AsyncMock(spec=MissionStateManager)
    manager.update_mission_status = AsyncMock()
    manager.complete_mission = AsyncMock()
    manager.log_event = AsyncMock()
    return manager


@pytest.fixture
def mock_executor():
    return AsyncMock(spec=TaskExecutor)


@pytest.fixture
def mock_brain():
    brain = AsyncMock(spec=SuperBrain)
    brain.process_mission = AsyncMock(return_value={"result": "success"})
    return brain


@pytest.mark.asyncio
async def test_overmind_orchestrator_run_mission_success(
    mock_state_manager, mock_executor, mock_brain
):
    """
    Test that the orchestrator successfully runs the SuperBrain loop.
    """
    mission = Mission(id=1, status=MissionStatus.PENDING, objective="Test Mission")
    mock_state_manager.get_mission.return_value = mission

    orchestrator = OvermindOrchestrator(
        state_manager=mock_state_manager, executor=mock_executor, brain=mock_brain
    )

    await orchestrator.run_mission(mission_id=1)

    # Verification
    mock_state_manager.get_mission.assert_called_with(1)
    mock_state_manager.update_mission_status.assert_any_call(
        1, MissionStatus.RUNNING, "Council of Wisdom Convening"
    )
    mock_brain.process_mission.assert_called_once()

    # We now call complete_mission instead of update_mission_status for success
    mock_state_manager.complete_mission.assert_called_once()
    args, kwargs = mock_state_manager.complete_mission.call_args
    assert args[0] == 1  # mission_id
    assert kwargs["result_json"] == {"result": "success"}


@pytest.mark.asyncio
async def test_overmind_orchestrator_run_mission_not_found(
    mock_state_manager, mock_executor, mock_brain
):
    """
    Test that the orchestrator handles non-existent missions gracefully.
    """
    mock_state_manager.get_mission.return_value = None

    orchestrator = OvermindOrchestrator(
        state_manager=mock_state_manager, executor=mock_executor, brain=mock_brain
    )

    await orchestrator.run_mission(mission_id=999)

    mock_state_manager.get_mission.assert_called_with(999)
    mock_brain.process_mission.assert_not_called()


@pytest.mark.asyncio
async def test_overmind_orchestrator_run_mission_failure(
    mock_state_manager, mock_executor, mock_brain
):
    """
    Test that the orchestrator handles catastrophic brain failures.
    """
    mission = Mission(id=1, status=MissionStatus.PENDING)
    mock_state_manager.get_mission.return_value = mission
    mock_brain.process_mission.side_effect = Exception("Brain Melt")

    orchestrator = OvermindOrchestrator(
        state_manager=mock_state_manager, executor=mock_executor, brain=mock_brain
    )

    await orchestrator.run_mission(mission_id=1)

    mock_state_manager.update_mission_status.assert_called_with(
        1, MissionStatus.FAILED, "Cognitive Error: Brain Melt"
    )


@pytest.mark.asyncio
async def test_overmind_factory_assembly(mock_db_session):
    """
    Test that the factory correctly assembles the Overmind components.
    """
    registry: dict[str, object] = {}
    with (
        patch.object(factory_module, "get_ai_client"),
        patch.object(factory_module, "get_registry", return_value=registry),
        patch.object(factory_module, "MissionStateManager"),
        patch.object(factory_module, "TaskExecutor"),
        patch.object(factory_module, "StrategistAgent") as mock_strat,
        patch.object(factory_module, "ArchitectAgent"),
        patch.object(factory_module, "OperatorAgent"),
        patch.object(factory_module, "AuditorClient"),
        # Use patch.object to ensure we mock the class in the module where create_overmind is defined
        patch.object(factory_module, "LangGraphOvermindEngine") as mock_brain_cls,
        patch("app.services.chat.tools.content.register_content_tools"),
    ):
        mock_db = AsyncMock()

        # Execute
        result = await create_overmind(mock_db)

        # Robustly handle both coroutine and synchronous return values (e.g. from mocks)
        if inspect.iscoroutine(result):
            orchestrator = await result
        else:
            orchestrator = result

        # Verify
        if (
            not isinstance(orchestrator, AsyncMock)
            and not isinstance(orchestrator, MagicMock)
            and not isinstance(orchestrator, type(AsyncMock()))
        ):
            assert isinstance(orchestrator, OvermindOrchestrator)

        # Check if the brain engine was instantiated
        # The factory calls _build_engine_with_components -> LangGraphOvermindEngine(...)
        assert mock_brain_cls.called, "LangGraphOvermindEngine should have been instantiated"
        mock_strat.assert_called_once()
        assert "search_educational_content" in registry
