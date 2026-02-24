from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.boundaries.observability_boundary_service import ObservabilityBoundaryService
from app.services.boundaries.schemas import TelemetryData
from app.telemetry.unified_observability import get_unified_observability


@pytest.mark.asyncio
async def test_observability_migration_flush_metrics():
    # Setup
    service = get_unified_observability()
    # Mock the client
    mock_client = AsyncMock()
    service.client = mock_client

    # Clear buffer first to be safe
    service.metrics.metrics_buffer.clear()

    # Record a metric
    service.record_metric("test_metric", 123.0, labels={"env": "test"})

    # Verify buffer has item
    assert len(service.metrics.metrics_buffer) > 0

    # Manually flush
    await service._flush_metrics_to_microservice()

    # Verify buffer is empty
    assert len(service.metrics.metrics_buffer) == 0

    # Verify client called
    assert mock_client.collect_telemetry.called
    call_args = mock_client.collect_telemetry.call_args[0][0]
    assert isinstance(call_args, TelemetryData)
    assert call_args.metric_id == "test_metric"
    assert call_args.value == 123.0
    assert call_args.labels["env"] == "test"


@pytest.mark.asyncio
async def test_observability_migration_boundary_alerts():
    # Setup
    boundary = ObservabilityBoundaryService()
    mock_client = AsyncMock()
    boundary.client = mock_client

    # Mock client response
    mock_client.get_active_alerts.return_value = [{"id": "alert1", "status": "active"}]

    # Call method
    alerts = await boundary.get_active_alerts()

    # Verify
    assert alerts == [{"id": "alert1", "status": "active"}]
    assert mock_client.get_active_alerts.called


@pytest.mark.asyncio
async def test_observability_migration_boundary_fallback():
    # Setup
    boundary = ObservabilityBoundaryService()
    mock_client = AsyncMock()
    # Simulate error
    mock_client.get_active_alerts.side_effect = Exception("Connection failed")
    boundary.client = mock_client

    # Ensure local alerts exist (mock them)
    # boundary.telemetry is set in __init__.

    mock_telemetry = MagicMock()
    # Mock anomaly_alerts as a list or deque of objects
    mock_alert_obj = MagicMock()
    mock_alert_obj.alert_id = "local_alert"
    mock_alert_obj.severity = "high"
    mock_alert_obj.description = "Local alert"
    mock_alert_obj.timestamp = 1234567890.0
    mock_alert_obj.resolved = False

    mock_telemetry.anomaly_alerts = [mock_alert_obj]
    boundary.telemetry = mock_telemetry

    # Call method
    alerts = await boundary.get_active_alerts()

    # Verify fallback
    assert len(alerts) == 1
    assert alerts[0]["id"] == "local_alert"
    assert alerts[0]["status"] == "active"
