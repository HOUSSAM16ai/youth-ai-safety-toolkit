from unittest.mock import AsyncMock, Mock, patch
import pytest
from app.services.boundaries.observability_client import ObservabilityServiceClient

@pytest.mark.asyncio
async def test_get_aiops_metrics_transformation():
    # Mock httpx response (synchronous methods like json())
    mock_response = Mock()
    mock_response.json.return_value = {
        "metrics": {
            "total_anomalies": 5.0,
            "successful_healings": 3,
            "active_forecasts": 2,
            "capacity_plans": 1
        }
    }
    mock_response.raise_for_status = Mock()

    # Patch AsyncClient.get to be an async mock returning the synchronous response mock
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        client = ObservabilityServiceClient()
        result = await client.get_aiops_metrics()

        assert result["anomaly_score"] == 5.0
        assert result["self_healing_events"] == 3
        assert result["predictions"]["active_forecasts"] == 2
        assert result["predictions"]["capacity_plans"] == 1
