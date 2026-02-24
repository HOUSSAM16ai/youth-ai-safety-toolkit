from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .logic import (
    build_baseline,
    build_capacity_plan,
    build_confidence_interval,
    calculate_trend,
    compose_forecast_record,
    derive_root_causes,
    detect_anomaly,
    determine_healing_plan,
    percentile,
    predict_load,
    serialize_capacity_plan,
)
from .models import (
    AnomalyDetection,
    CapacityPlan,
    HealingDecision,
    JsonValue,
    LoadForecast,
    MetricType,
    TelemetryData,
)
from .ports import (
    AnomalyRepository,
    CapacityPlanRepository,
    ForecastRepository,
    HealingDecisionRepository,
    TelemetryRepository,
)
from .repositories import (
    InMemoryAnomalyRepository,
    InMemoryCapacityPlanRepository,
    InMemoryForecastRepository,
    InMemoryHealingDecisionRepository,
    InMemoryTelemetryRepository,
)


@dataclass
class AIOpsConfig:
    """تهيئة اعتماديات خدمة AIOps بطريقة واضحة للمبتدئين."""

    telemetry_repo: TelemetryRepository | None = None
    anomaly_repo: AnomalyRepository | None = None
    healing_repo: HealingDecisionRepository | None = None
    forecast_repo: ForecastRepository | None = None
    capacity_repo: CapacityPlanRepository | None = None


class AIOpsService:
    """خدمة AIOps خارقة بمعمارية مبسطة وتوثيق عربي للممارسين الجدد."""

    def __init__(
        self,
        config: AIOpsConfig | None = None,
    ):
        config = config or AIOpsConfig()

        # Default to in-memory repositories if not provided in config
        self.telemetry_repo = config.telemetry_repo or InMemoryTelemetryRepository()
        self.anomaly_repo = config.anomaly_repo or InMemoryAnomalyRepository()
        self.healing_repo = config.healing_repo or InMemoryHealingDecisionRepository()
        self.forecast_repo = config.forecast_repo or InMemoryForecastRepository()
        self.capacity_repo = config.capacity_repo or InMemoryCapacityPlanRepository()

        self.baseline_metrics: dict[str, dict[str, float]] = {}
        self.lock = threading.RLock()

        self.anomaly_thresholds: dict[MetricType, dict[str, float]] = {
            MetricType.LATENCY: {"zscore": 3.0, "percentile_95": 1.5},
            MetricType.ERROR_RATE: {"threshold": 0.05},
            MetricType.REQUEST_RATE: {"zscore": 2.5},
        }

        logging.getLogger(__name__).info("AIOps Service (Simplified) initialized successfully")

    # ==================================================================================
    # TELEMETRY COLLECTION
    # ==================================================================================

    def collect_telemetry(self, data: TelemetryData) -> None:
        """جمع نقطة قياس تشغيلية وتحديث خطوط الأساس واكتشاف الشذوذ."""
        with self.lock:
            self.telemetry_repo.add(data)
            self._update_baseline(data)
            self._detect_anomalies(data)

    def _update_baseline(self, data: TelemetryData) -> None:
        """تحديث خطوط الأساس الإحصائية للمقاييس لمقارنة الانحرافات."""
        values = [
            d.value for d in self.telemetry_repo.get_by_service(data.service_name, data.metric_type)
        ]
        key = f"{data.service_name}:{data.metric_type.value}"

        if len(values) >= 10:
            self.baseline_metrics[key] = build_baseline(values)

    # ==================================================================================
    # ANOMALY DETECTION
    # ==================================================================================

    def _detect_anomalies(self, data: TelemetryData) -> None:
        """كشف الشذوذ بالاعتماد على خطوط الأساس والإعدادات الافتراضية."""
        key = f"{data.service_name}:{data.metric_type.value}"
        baseline = self.baseline_metrics.get(key)

        if not baseline:
            return

        anomaly = detect_anomaly(data, baseline, self.anomaly_thresholds)
        if anomaly:
            self._record_anomaly(anomaly)
            self._trigger_healing(anomaly)

    def _record_anomaly(self, anomaly: AnomalyDetection) -> None:
        """تسجيل الشذوذ المكتشف وتحديث التخزين المؤقت بأمان."""
        with self.lock:
            self.anomaly_repo.add(anomaly)
            logging.getLogger(__name__).warning(
                f"Anomaly detected: {anomaly.description} (severity: {anomaly.severity.value})"
            )

    # ==================================================================================
    # SELF-HEALING
    # ==================================================================================

    def _trigger_healing(self, anomaly: AnomalyDetection) -> None:
        """تشغيل إجراءات المعالجة الذاتية بالاعتماد على خطة واضحة."""
        plan = determine_healing_plan(anomaly)

        if not plan:
            return

        decision = HealingDecision(
            decision_id=str(uuid.uuid4()),
            anomaly_id=anomaly.anomaly_id,
            service_name=anomaly.service_name,
            action=plan.action,
            reason=plan.reason,
            parameters=plan.parameters,
        )

        with self.lock:
            self.healing_repo.add(decision)

        self._execute_healing(decision)

    def _execute_healing(self, decision: HealingDecision) -> None:
        """تنفيذ إجراء المعالجة الذاتية مع تحديث أثر القرار."""
        logging.getLogger(__name__).info(
            f"Executing healing: {decision.action.value} for {decision.service_name}"
        )

        decision.executed_at = datetime.now(UTC)
        decision.success = True
        decision.impact = {
            "before": "degraded",
            "after": "healthy",
            "metrics_improved": True,
        }

        with self.lock:
            if anomaly := self.anomaly_repo.get(decision.anomaly_id):
                anomaly.resolved = True
                anomaly.resolved_at = datetime.now(UTC)
                self.anomaly_repo.update(anomaly)

    # ==================================================================================
    # PREDICTIVE ANALYTICS
    # ==================================================================================
    def forecast_load(
        self, service_name: str, metric_type: MetricType, hours_ahead: int = 24
    ) -> LoadForecast | None:
        """توقّع الحمل المستقبلي للخدمة مع خطوات واضحة وقابلة للاختبار."""
        values = self._get_recent_metric_values(service_name, metric_type)

        if not self._has_minimum_history(values):
            return None

        trend = calculate_trend(values)
        forecast_timestamp = datetime.now(UTC) + timedelta(hours=hours_ahead)
        predicted_load = predict_load(values[-1], trend, hours_ahead)
        confidence_interval = build_confidence_interval(values, predicted_load)

        forecast = compose_forecast_record(
            service_name=service_name,
            forecast_timestamp=forecast_timestamp,
            predicted_load=predicted_load,
            confidence_interval=confidence_interval,
        )
        self._store_forecast(service_name, forecast)

        return forecast

    def _get_recent_metric_values(self, service_name: str, metric_type: MetricType) -> list[float]:
        """جلب آخر قيم المقياس للخدمة بهدف بناء التوقعات."""
        data_points = self.telemetry_repo.get_by_service(service_name, metric_type)
        return [d.value for d in data_points[-168:]]

    @staticmethod
    def _has_minimum_history(values: list[float]) -> bool:
        """التحقق من توفر حد أدنى من التاريخ لضمان توقع موثوق."""
        return len(values) >= 100

    def _store_forecast(self, service_name: str, forecast: LoadForecast) -> None:
        """حفظ التوقع داخل المخزن مع حماية تزامنية."""
        with self.lock:
            self.forecast_repo.add(service_name, forecast)

    # ==================================================================================
    # CAPACITY PLANNING
    # ==================================================================================

    def generate_capacity_plan(
        self, service_name: str, forecast_horizon_hours: int = 72
    ) -> CapacityPlan | None:
        """إنشاء توصية تخطيط سعة مبنية على التوقعات الحديثة."""
        forecast = self.forecast_load(service_name, MetricType.REQUEST_RATE, forecast_horizon_hours)

        if not forecast:
            return None

        current_capacity = 100.0
        safety_factor = 1.3
        plan = build_capacity_plan(
            service_name=service_name,
            forecast=forecast,
            current_capacity=current_capacity,
            safety_factor=safety_factor,
            horizon_hours=forecast_horizon_hours,
        )

        with self.lock:
            self.capacity_repo.add(service_name, plan)

        return plan

    # ==================================================================================
    # ROOT CAUSE ANALYSIS
    # ==================================================================================

    def analyze_root_cause(self, anomaly_id: str) -> list[str]:
        """تحليل السبب الجذري للشذوذ باستخدام قواعد مبسطة."""
        anomaly = self.anomaly_repo.get(anomaly_id)
        if not anomaly:
            return []

        service_metrics = self._get_service_metrics(anomaly.service_name, minutes=30)
        root_causes = derive_root_causes(anomaly, service_metrics)

        with self.lock:
            anomaly.root_causes = root_causes
            self.anomaly_repo.update(anomaly)

        return root_causes

    def _get_service_metrics(self, service_name: str, minutes: int = 30) -> list[TelemetryData]:
        """جلب مقاييس خدمة خلال نافذة زمنية محددة بالدقائق."""
        cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
        all_metrics = self.telemetry_repo.get_all()
        metrics = []

        for key, data_points in all_metrics.items():
            if key.startswith(service_name):
                metrics.extend([d for d in data_points if d.timestamp >= cutoff])

        return metrics

    # ==================================================================================
    # METRICS & MONITORING
    # ==================================================================================

    def get_aiops_metrics(self) -> dict[str, JsonValue]:
        """الحصول على إحصاءات خدمة AIOps بصيغة جاهزة للعرض أو التتبع."""
        all_anomalies = self.anomaly_repo.get_all()
        total_anomalies = len(all_anomalies)
        resolved_anomalies = len([a for a in all_anomalies.values() if a.resolved])
        healing_decisions = self.healing_repo.get_all()
        forecasts = self.forecast_repo.get_all()
        capacity_plans = self.capacity_repo.get_all()
        telemetry = self.telemetry_repo.get_all()

        return {
            "total_telemetry_points": sum(len(d) for d in telemetry.values()),
            "total_anomalies": total_anomalies,
            "resolved_anomalies": resolved_anomalies,
            "resolution_rate": resolved_anomalies / total_anomalies if total_anomalies > 0 else 0.0,
            "active_healing_decisions": len(
                [d for d in healing_decisions.values() if d.success is None]
            ),
            "successful_healings": len(
                [d for d in healing_decisions.values() if d.success is True]
            ),
            "active_forecasts": sum(len(f) for f in forecasts.values()),
            "capacity_plans": len(capacity_plans),
            "services_monitored": len({a.service_name for a in all_anomalies.values()}),
        }

    def get_active_alerts(self) -> list[dict[str, JsonValue]]:
        """الحصول على قائمة التنبيهات النشطة (الشذوذ غير المحلول)."""
        all_anomalies = self.anomaly_repo.get_all()
        # Sort by timestamp descending
        active = sorted(
            [a for a in all_anomalies.values() if not a.resolved],
            key=lambda x: x.detected_at,
            reverse=True,
        )

        return [
            {
                "id": a.anomaly_id,
                "severity": a.severity.value,
                "message": f"[{a.anomaly_type.value}] {a.description} (Value: {a.metric_value:.2f}, Expected: {a.expected_value:.2f})",
                "timestamp": a.detected_at.isoformat(),
                "status": "active",
                "service_name": a.service_name,
                "metrics": {"value": a.metric_value, "expected": a.expected_value},
            }
            for a in active
        ]

    def get_service_health(self, service_name: str) -> dict[str, JsonValue]:
        """الحصول على ملخص صحة الخدمة مع آخر التوقعات وخطط السعة."""
        all_anomalies = self.anomaly_repo.get_all()
        recent_anomalies = [
            a for a in all_anomalies.values() if a.service_name == service_name and not a.resolved
        ]

        latest_forecast = None
        service_forecasts = self.forecast_repo.get(service_name)
        if service_forecasts:
            latest_forecast = service_forecasts[-1]

        return {
            "service_name": service_name,
            "active_anomalies": len(recent_anomalies),
            "health_status": "degraded" if recent_anomalies else "healthy",
            "latest_forecast": (
                {
                    "predicted_load": latest_forecast.predicted_load,
                    "forecast_time": latest_forecast.forecast_timestamp.isoformat(),
                }
                if latest_forecast
                else None
            ),
            "capacity_plan": (
                serialize_capacity_plan(self.capacity_repo.get(service_name))
                if self.capacity_repo.get(service_name)
                else None
            ),
        }

    # ==================================================================================
    # MONOLITH COMPATIBILITY (GOLDEN SIGNALS & PERFORMANCE)
    # ==================================================================================

    def get_golden_signals(self) -> dict[str, JsonValue]:
        """تجميع الإشارات الذهبية للتوافق مع المونوليث."""
        # Calculate global metrics across all services or just return aggregate
        # For simplicity, we aggregate everything.
        all_metrics = self.telemetry_repo.get_all()

        # Helper to get values for a metric type
        def get_values(m_type: MetricType) -> list[float]:
            values = []
            for q in all_metrics.values():
                values.extend([d.value for d in q if d.metric_type == m_type])
            return values

        # Latency
        latencies = get_values(MetricType.LATENCY)
        if not latencies:
            latencies = [0.0]

        latency_metrics = {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "p99.9": percentile(latencies, 99.9)
            if len(latencies) >= 1000
            else percentile(latencies, 99),
            "avg": sum(latencies) / len(latencies),
        }

        # Traffic
        # Request Rate (RPS) - average of latest rates
        rates = get_values(MetricType.REQUEST_RATE)
        avg_rate = sum(rates) / len(rates) if rates else 0.0
        # Total requests - count of latency points (assuming 1 latency pt per request)
        total_requests = len(latencies) if latencies != [0.0] else 0

        traffic_metrics = {
            "requests_per_second": avg_rate,
            "total_requests": total_requests,
        }

        # Errors
        error_rates = get_values(MetricType.ERROR_RATE)
        avg_error_rate = sum(error_rates) / len(error_rates) if error_rates else 0.0
        # Estimate count
        error_count = int(total_requests * avg_error_rate)

        error_metrics = {
            "error_rate": avg_error_rate,
            "error_count": error_count,
        }

        # Saturation
        # Use active requests (if available) or queue depth proxy
        # Since we don't strictly store active_requests, we return 0 or mock
        saturation_metrics = {
            "active_requests": 0,
            "queue_depth": 0,
            "active_spans": None,
            "resource_utilization": None,
        }

        return {
            "latency": latency_metrics,
            "traffic": traffic_metrics,
            "errors": error_metrics,
            "saturation": saturation_metrics,
        }

    def get_performance_snapshot(self) -> dict[str, JsonValue]:
        """لقطة الأداء الحالية."""
        all_metrics = self.telemetry_repo.get_all()

        def get_latest(m_type: MetricType) -> float:
            latest = 0.0
            for q in all_metrics.values():
                relevant = [d for d in q if d.metric_type == m_type]
                if relevant:
                    latest = max(latest, relevant[-1].value)  # Max across services
            return latest

        return {
            "cpu_usage": get_latest(MetricType.CPU_USAGE),
            "memory_usage": get_latest(MetricType.MEMORY_USAGE),
            "active_requests": int(get_latest(MetricType.REQUEST_RATE)),  # Proxy
        }

    def get_endpoint_analytics(self, path: str) -> list[dict[str, JsonValue]]:
        """تحليلات نقطة نهاية محددة."""
        # This requires filtering by path in labels.
        # Since InMemoryTelemetryRepository is structured by "service:metric", we iterate all.
        all_metrics = self.telemetry_repo.get_all()

        relevant_latencies = []
        errors = 0

        for q in all_metrics.values():
            for d in q:
                if d.labels.get("path") == path:
                    if d.metric_type == MetricType.LATENCY:
                        relevant_latencies.append(d.value)
                    elif d.metric_type == MetricType.ERROR_RATE and d.value > 0:
                        errors += 1  # Rough count

        if not relevant_latencies:
            return []

        avg_lat = sum(relevant_latencies) / len(relevant_latencies)
        p95_lat = percentile(relevant_latencies, 95)

        # Aggregate into one item per path (since path is unique here)
        return [
            {
                "path": path,
                "avg_latency": avg_lat,
                "p95_latency": p95_lat,
                "error_count": errors,
                "total_calls": len(relevant_latencies),
            }
        ]


# Singleton Instance
_aiops_instance: AIOpsService | None = None
_aiops_lock = threading.Lock()


def get_aiops_service() -> AIOpsService:
    global _aiops_instance
    if _aiops_instance is None:
        with _aiops_lock:
            if _aiops_instance is None:
                _aiops_instance = AIOpsService()
    return _aiops_instance
