from __future__ import annotations

from datetime import UTC, datetime

from microservices.observability_service.logic import HealingPlan, determine_healing_plan
from microservices.observability_service.models import (
    AnomalyDetection,
    AnomalySeverity,
    AnomalyType,
    CapacityPlan,
    HealingAction,
)
from microservices.observability_service.service import AIOpsService


def _build_anomaly(metric_value: float, expected_value: float = 0.1) -> AnomalyDetection:
    return AnomalyDetection(
        anomaly_id="anomaly-1",
        service_name="svc",
        anomaly_type=AnomalyType.LATENCY_SPIKE,
        severity=AnomalySeverity.HIGH,
        detected_at=datetime.now(UTC),
        metric_value=metric_value,
        expected_value=expected_value,
        confidence=0.9,
        description="latency spike",
    )


def test_healing_plan_structure_is_type_safe() -> None:
    plan = determine_healing_plan(_build_anomaly(metric_value=2.5))

    assert isinstance(plan, HealingPlan)
    assert plan.action is HealingAction.SCALE_UP
    assert all(isinstance(value, (int, float)) for value in plan.parameters.values())


def test_service_health_serializes_capacity_plan_without_datetimes() -> None:
    service = AIOpsService()
    plan = CapacityPlan(
        plan_id="plan-1",
        service_name="svc",
        current_capacity=50.0,
        recommended_capacity=75.0,
        forecast_horizon_hours=24,
        expected_peak_load=70.0,
        confidence=0.8,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    service.capacity_repo.add("svc", plan)

    payload = service.get_service_health("svc")

    assert payload["capacity_plan"]["service_name"] == "svc"
    assert payload["capacity_plan"]["created_at"].endswith("+00:00")
    assert payload["capacity_plan"]["recommended_capacity"] == 75.0


def test_aiops_metrics_payload_is_numeric_and_complete() -> None:
    service = AIOpsService()

    metrics = service.get_aiops_metrics()

    assert set(metrics.keys()) == {
        "total_telemetry_points",
        "total_anomalies",
        "resolved_anomalies",
        "resolution_rate",
        "active_healing_decisions",
        "successful_healings",
        "active_forecasts",
        "capacity_plans",
        "services_monitored",
    }
    assert all(isinstance(value, (int, float)) for value in metrics.values())
