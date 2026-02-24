from __future__ import annotations

import logging

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.boundaries.schemas import (
    TelemetryData,
)

logger = logging.getLogger(__name__)


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
                "capacity_plans": metrics.get("capacity_plans", 0),
            },
        }

    async def get_metrics(self) -> dict:
        """Get raw metrics from the microservice."""
        response = await self.client.get("/metrics")
        response.raise_for_status()
        return response.json().get("metrics", {})

    async def get_active_alerts(self) -> list[dict]:
        """Get active alerts from the microservice."""
        response = await self.client.get("/alerts")
        response.raise_for_status()
        return response.json().get("alerts", [])

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
        try:
            response = await self.client.post("/telemetry", json=payload)
            response.raise_for_status()
        except Exception as e:
            # Log and suppress error to avoid breaking the caller (background task)
            logger.warning(f"Failed to send telemetry: {e}")

    async def calculate_security_metrics(
        self, findings: list[dict], code_metrics: dict | None = None
    ) -> dict:
        payload = {"findings": findings, "code_metrics": code_metrics}
        response = await self.client.post("/security/metrics/calculate", json=payload)
        response.raise_for_status()
        return response.json()

    async def predict_security_risk(
        self, historical_metrics: list[dict], days_ahead: int = 30
    ) -> dict:
        payload = {"historical_metrics": historical_metrics, "days_ahead": days_ahead}
        response = await self.client.post("/security/risk/predict", json=payload)
        response.raise_for_status()
        return response.json()

    async def calculate_risk_score(
        self, findings: list[dict], code_metrics: dict | None = None
    ) -> float:
        payload = {"findings": findings, "code_metrics": code_metrics}
        response = await self.client.post("/security/risk/score", json=payload)
        response.raise_for_status()
        return response.json()["risk_score"]

    async def get_golden_signals(self) -> dict:
        """Get golden signals from the microservice."""
        response = await self.client.get("/golden-signals")
        response.raise_for_status()
        return response.json()

    async def get_performance_snapshot(self) -> dict:
        """Get performance snapshot from the microservice."""
        response = await self.client.get("/performance")
        response.raise_for_status()
        return response.json()

    async def get_endpoint_analytics(self, path: str) -> list[dict]:
        """Get endpoint analytics from the microservice."""
        response = await self.client.get(f"/analytics/{path}")
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()
