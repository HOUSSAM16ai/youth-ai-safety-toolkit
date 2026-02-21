"""اختبارات نماذج الاستجابة لخدمة المراقبة عبر HTTP."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

# Explicitly override the secret key for testing to ensure consistency
TEST_SECRET_KEY = "test-secret-key-for-ci-pipeline"
os.environ["SECRET_KEY"] = TEST_SECRET_KEY

from microservices.observability_service import main as observability_main
from microservices.observability_service.models import CapacityPlan, MetricType
from microservices.observability_service.settings import get_settings


def get_auth_headers() -> dict[str, str]:
    """توليد ترويسة مصادقة صالحة للخدمات."""
    # Ensure we use the current environment variable if updated by conftest
    secret_key = os.environ.get("SECRET_KEY", TEST_SECRET_KEY)
    payload = {
        "sub": "api-gateway",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return {"X-Service-Token": token}


@dataclass(frozen=True)
class _ForecastStub:
    forecast_id: str
    predicted_load: float
    confidence_interval: tuple[float, float]


class _AIOpsServiceStub:
    def __init__(self) -> None:
        self.collected: list[str] = []

    def collect_telemetry(self, data: object) -> None:
        self.collected.append("collected")

    def get_aiops_metrics(self) -> dict[str, float | int]:
        return {"total_telemetry_points": 1, "resolution_rate": 0.5}

    def forecast_load(
        self, service_name: str, metric_type: MetricType, hours_ahead: int
    ) -> _ForecastStub:
        return _ForecastStub(
            forecast_id="forecast-1",
            predicted_load=1.5,
            confidence_interval=(1.2, 1.8),
        )

    def generate_capacity_plan(
        self, service_name: str, forecast_horizon_hours: int
    ) -> CapacityPlan:
        return CapacityPlan(
            plan_id="plan-1",
            service_name=service_name,
            current_capacity=1.0,
            recommended_capacity=2.0,
            forecast_horizon_hours=forecast_horizon_hours,
            expected_peak_load=1.5,
            confidence=0.9,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )


def _client_with_stubbed_service() -> TestClient:
    get_settings.cache_clear()
    stub = _AIOpsServiceStub()
    observability_main.get_aiops_service = lambda: stub
    return TestClient(observability_main.app)


def test_root_endpoint() -> None:
    client = _client_with_stubbed_service()

    # The root endpoint might be unprotected, or protected.
    # Assuming unprotected for health/root, but if protected, headers needed.
    # Usually root "/" is informational.
    # But if observability_service enforces security globally, we need headers.
    # Let's try with headers to be safe.
    response = client.get("/", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"message": "Observability Service is running"}


def test_telemetry_endpoint() -> None:
    client = _client_with_stubbed_service()

    payload = {
        "metric_id": "metric-1",
        "service_name": "service-a",
        "metric_type": MetricType.LATENCY.value,
        "value": 1.25,
    }

    response = client.post("/telemetry", json=payload, headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"status": "collected", "metric_id": "metric-1"}


def test_metrics_endpoint() -> None:
    client = _client_with_stubbed_service()

    response = client.get("/metrics", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {"metrics": {"total_telemetry_points": 1, "resolution_rate": 0.5}}


def test_forecast_endpoint() -> None:
    client = _client_with_stubbed_service()

    payload = {
        "service_name": "service-a",
        "metric_type": MetricType.LATENCY.value,
        "hours_ahead": 24,
    }

    response = client.post("/forecast", json=payload, headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "forecast_id": "forecast-1",
        "predicted_load": 1.5,
        "confidence_interval": [1.2, 1.8],
    }


def test_capacity_endpoint() -> None:
    client = _client_with_stubbed_service()
    created_at = datetime(2024, 1, 1, tzinfo=UTC).isoformat()

    payload = {"service_name": "service-a", "forecast_horizon_hours": 24}

    response = client.post("/capacity", json=payload, headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "plan": {
            "plan_id": "plan-1",
            "service_name": "service-a",
            "current_capacity": 1.0,
            "recommended_capacity": 2.0,
            "forecast_horizon_hours": 24,
            "expected_peak_load": 1.5,
            "confidence": 0.9,
            "created_at": created_at,
        }
    }
