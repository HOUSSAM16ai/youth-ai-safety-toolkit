from __future__ import annotations

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.boundaries.schemas import (
    TelemetryData,
)


class ObservabilityClientSettings(BaseSettings):
    OBSERVABILITY_SERVICE_URL: str = "http://observability-service:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ObservabilityServiceClient:
    """
    عميل للتعامل مع خدمة المراقبة الدقيقة.
    """

    def __init__(self, base_url: str | None = None):
        settings = ObservabilityClientSettings()
        self.base_url = base_url or settings.OBSERVABILITY_SERVICE_URL
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def get_aiops_metrics(self) -> dict:
        response = await self.client.get("/metrics")
        response.raise_for_status()
        data = response.json()

        # Microservice returns MetricsResponse(metrics={...})
        metrics = data.get("metrics", {})

        # Transform to match AIOpsMetricsResponse
        return {
            "anomaly_score": float(metrics.get("total_anomalies", 0.0)),
            "self_healing_events": int(metrics.get("successful_healings", 0)),
            "predictions": {
                "active_forecasts": metrics.get("active_forecasts", 0),
                "capacity_plans": metrics.get("capacity_plans", 0)
            }
        }

    async def get_service_health(self, service_name: str) -> dict:
        response = await self.client.get(f"/health/{service_name}")
        response.raise_for_status()
        return response.json()

    async def collect_telemetry(self, data: TelemetryData) -> None:
        payload = {
            "metric_id": data.metric_id,
            "service_name": data.service_name,
            "metric_type": data.metric_type.value,
            "value": data.value,
            "timestamp": data.timestamp.isoformat(),
            "labels": data.labels,
            "unit": data.unit,
        }
        response = await self.client.post("/telemetry", json=payload)
        response.raise_for_status()

    async def close(self):
        await self.client.aclose()
