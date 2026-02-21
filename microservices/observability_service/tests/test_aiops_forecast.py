from __future__ import annotations

from datetime import UTC, datetime, timedelta

from microservices.observability_service.logic import (
    build_confidence_interval,
    calculate_trend,
    predict_load,
)
from microservices.observability_service.models import MetricType, TelemetryData
from microservices.observability_service.service import AIOpsService


def _add_history(service: AIOpsService, total_points: int) -> list[float]:
    base_time = datetime.now(UTC)
    values: list[float] = []

    for index in range(total_points):
        value = float(index + 1)
        values.append(value)
        service.collect_telemetry(
            TelemetryData(
                metric_id=f"m-{index}",
                service_name="svc",
                metric_type=MetricType.REQUEST_RATE,
                value=value,
                timestamp=base_time - timedelta(minutes=(total_points - index)),
            )
        )

    return values


def test_forecast_load_requires_minimum_history() -> None:
    service = AIOpsService()
    _add_history(service, total_points=10)

    assert service.forecast_load("svc", MetricType.REQUEST_RATE) is None


def test_forecast_load_builds_confidence_interval_and_persists() -> None:
    service = AIOpsService()
    values = _add_history(service, total_points=120)

    forecast = service.forecast_load("svc", MetricType.REQUEST_RATE, hours_ahead=2)

    assert forecast is not None

    trend = calculate_trend(values[-168:])
    expected_predicted = predict_load(values[-1], trend, 2)
    expected_lower, expected_upper = build_confidence_interval(values[-168:], expected_predicted)

    lower, upper = forecast.confidence_interval
    assert forecast.predicted_load == expected_predicted
    assert lower == expected_lower
    assert upper == expected_upper

    stored_forecasts = service.forecast_repo.get("svc")
    assert stored_forecasts and stored_forecasts[-1] is forecast
