"""
خدمة المراقبة (Observability Service).

توفر واجهات API مستقلة لتحليل القياسات والتنبؤ بالأحمال.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from microservices.observability_service.errors import (
    BadRequestError,
    NotFoundError,
    setup_exception_handlers,
)
from microservices.observability_service.health import HealthResponse, build_health_payload
from microservices.observability_service.logging import get_logger, setup_logging
from microservices.observability_service.logic import serialize_capacity_plan
from microservices.observability_service.models import MetricType, TelemetryData
from microservices.observability_service.security import verify_service_token
from microservices.observability_service.security_routes import security_router
from microservices.observability_service.service import get_aiops_service
from microservices.observability_service.settings import ObservabilitySettings, get_settings

logger = get_logger("observability-service")


class TelemetryRequest(BaseModel):
    """حمولة قياس قادمة من خدمة مراقبة."""

    metric_id: str
    service_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: dict[str, str] = Field(default_factory=dict)
    unit: str = ""


class ForecastRequest(BaseModel):
    """طلب توقع الحمل المستقبلي."""

    service_name: str
    metric_type: MetricType
    hours_ahead: int = 24


class CapacityPlanRequest(BaseModel):
    """طلب إنشاء خطة سعة مستقبلية."""

    service_name: str
    forecast_horizon_hours: int = 72


class TelemetryResponse(BaseModel):
    """استجابة استقبال القياس."""

    status: str
    metric_id: str


class RootResponse(BaseModel):
    """رسالة الجذر لخدمة المراقبة."""

    message: str


class AlertItem(BaseModel):
    """عنصر تنبيه واحد."""

    id: str
    severity: str
    message: str
    timestamp: str
    status: str
    service_name: str
    metrics: dict[str, float]


class AlertsResponse(BaseModel):
    """استجابة قائمة التنبيهات."""

    alerts: list[AlertItem]


class MetricsResponse(BaseModel):
    """استجابة المقاييس الإجمالية."""

    metrics: dict[str, float | int]


class ForecastResponse(BaseModel):
    """استجابة توقع الحمل مع فاصل الثقة."""

    forecast_id: str
    predicted_load: float
    confidence_interval: tuple[float, float]


class CapacityPlanPayload(BaseModel):
    """تفاصيل خطة السعة الناتجة عن التحليل."""

    plan_id: str
    service_name: str
    current_capacity: float
    recommended_capacity: float
    forecast_horizon_hours: int
    expected_peak_load: float
    confidence: float
    created_at: str


class CapacityPlanResponse(BaseModel):
    """استجابة خطة السعة بعد التوليد."""

    plan: CapacityPlanPayload


class LatencyMetrics(BaseModel):
    """مقاييس زمن الاستجابة للمسارات الساخنة."""

    model_config = ConfigDict(populate_by_name=True)

    p50: float = Field(..., description="الوسيط")
    p95: float = Field(..., description="النسبة المئوية 95")
    p99: float = Field(..., description="النسبة المئوية 99")
    p99_9: float = Field(..., alias="p99.9", description="النسبة المئوية 99.9")
    avg: float = Field(..., description="المتوسط العام")


class TrafficMetrics(BaseModel):
    """إحصاءات حركة المرور على مستوى الخدمة."""

    requests_per_second: float = Field(..., description="عدد الطلبات في الثانية")
    total_requests: int = Field(..., description="إجمالي الطلبات في النافذة الزمنية")


class ErrorMetrics(BaseModel):
    """مقاييس الأخطاء ونسبة فشل الطلبات."""

    error_rate: float = Field(..., description="معدل الأخطاء بالنسبة المئوية")
    error_count: int = Field(..., description="عدد الأخطاء الملاحظة")


class SaturationMetrics(BaseModel):
    """مؤشرات التشبع واستهلاك الموارد."""

    active_requests: int = Field(..., description="عدد الطلبات النشطة")
    queue_depth: int = Field(..., description="عمق طابور التنفيذ")
    active_spans: int | None = Field(None, description="عدد المقاطع التتبعية الفعّالة")
    resource_utilization: float | None = Field(None, description="نسبة استهلاك الموارد")


class GoldenSignalsResponse(BaseModel):
    """
    نموذج الإشارات الذهبية (SRE Golden Signals).
    """

    latency: LatencyMetrics = Field(..., description="مقاييس زمن الاستجابة")
    traffic: TrafficMetrics = Field(..., description="حركة المرور")
    errors: ErrorMetrics = Field(..., description="نسبة الأخطاء")
    saturation: SaturationMetrics = Field(..., description="مؤشرات التشبع")


class PerformanceSnapshotResponse(BaseModel):
    """
    نموذج لقطة الأداء.
    """

    cpu_usage: float = Field(..., description="استهلاك المعالج (%)")
    memory_usage: float = Field(..., description="استهلاك الذاكرة (%)")
    active_requests: int = Field(..., description="عدد الطلبات النشطة")


class EndpointAnalyticsResponse(BaseModel):
    """
    نموذج تحليلات نقطة النهاية.
    """

    path: str = Field(..., description="مسار نقطة النهاية")
    avg_latency: float = Field(..., description="متوسط زمن الاستجابة")
    p95_latency: float = Field(..., description="P95 Latency")
    error_count: int = Field(0, description="عدد الأخطاء")
    total_calls: int = Field(0, description="إجمالي الاستدعاءات")


def _register_routes(app: FastAPI, settings: ObservabilitySettings) -> None:
    """تسجيل موجهات خدمة المراقبة بالاعتماد على الإعدادات."""

    app.include_router(security_router, dependencies=[Depends(verify_service_token)])

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check() -> HealthResponse:
        """يفحص جاهزية خدمة المراقبة."""

        return build_health_payload(service_name=settings.SERVICE_NAME)

    @app.get("/", response_model=RootResponse, tags=["System"])
    async def root() -> RootResponse:
        """رسالة الجذر لخدمة المراقبة."""

        return RootResponse(message="Observability Service is running")

    @app.post(
        "/telemetry",
        response_model=TelemetryResponse,
        tags=["Telemetry"],
        summary="استقبال قياس جديد",
        dependencies=[Depends(verify_service_token)],
    )
    async def collect_telemetry(request: TelemetryRequest) -> TelemetryResponse:
        """تجميع قياسات واردة من الخدمات الأخرى."""

        logger.info(
            "استقبال قياس",
            extra={"metric_id": request.metric_id, "service_name": request.service_name},
        )
        service = get_aiops_service()
        data = TelemetryData(
            metric_id=request.metric_id,
            service_name=request.service_name,
            metric_type=request.metric_type,
            value=request.value,
            timestamp=request.timestamp,
            labels=request.labels,
            unit=request.unit,
        )
        service.collect_telemetry(data)
        return TelemetryResponse(status="collected", metric_id=request.metric_id)

    @app.get(
        "/metrics",
        response_model=MetricsResponse,
        tags=["Telemetry"],
        summary="عرض مؤشرات الخدمة",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_metrics() -> MetricsResponse:
        """إرجاع مؤشرات المراقبة الإجمالية."""

        service = get_aiops_service()
        return MetricsResponse(metrics=service.get_aiops_metrics())

    @app.get(
        "/alerts",
        response_model=AlertsResponse,
        tags=["Telemetry"],
        summary="عرض التنبيهات النشطة",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_alerts() -> AlertsResponse:
        """إرجاع قائمة التنبيهات النشطة (الشذوذ)."""

        service = get_aiops_service()
        alerts = service.get_active_alerts()
        # alerts are already dicts matching the structure
        return AlertsResponse(alerts=alerts)

    @app.get(
        "/health/{service_name}",
        response_model=dict[str, object],
        tags=["Telemetry"],
        summary="فحص صحة خدمة محددة",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_service_health(service_name: str) -> dict[str, object]:
        """قياس صحة خدمة محددة."""

        service = get_aiops_service()
        return service.get_service_health(service_name)

    @app.post(
        "/forecast",
        response_model=ForecastResponse,
        tags=["Forecast"],
        summary="توليد توقعات الحمل",
        dependencies=[Depends(verify_service_token)],
    )
    async def forecast_load(request: ForecastRequest) -> ForecastResponse:
        """توليد توقع للحمل المستقبلي."""

        service = get_aiops_service()
        forecast = service.forecast_load(
            request.service_name, request.metric_type, request.hours_ahead
        )
        if not forecast:
            raise NotFoundError("لا توجد بيانات كافية للتنبؤ")

        return ForecastResponse(
            forecast_id=forecast.forecast_id,
            predicted_load=forecast.predicted_load,
            confidence_interval=forecast.confidence_interval,
        )

    @app.post(
        "/capacity",
        response_model=CapacityPlanResponse,
        tags=["Forecast"],
        summary="توليد خطة السعة",
        dependencies=[Depends(verify_service_token)],
    )
    async def generate_capacity_plan(request: CapacityPlanRequest) -> CapacityPlanResponse:
        """إنشاء خطة سعة بناءً على التوقعات."""

        service = get_aiops_service()
        plan = service.generate_capacity_plan(request.service_name, request.forecast_horizon_hours)
        if not plan:
            raise BadRequestError("تعذر توليد خطة السعة")
        serialized = serialize_capacity_plan(plan)
        if serialized is None:
            raise BadRequestError("تعذر تحويل خطة السعة")
        return CapacityPlanResponse(plan=CapacityPlanPayload(**serialized))

    @app.get(
        "/anomalies/{anomaly_id}/root_cause",
        response_model=dict[str, object],
        tags=["Anomalies"],
        summary="تحليل السبب الجذري للشذوذ",
        dependencies=[Depends(verify_service_token)],
    )
    async def analyze_root_cause(anomaly_id: str) -> dict[str, object]:
        """تحليل السبب الجذري لشذوذ محدد."""

        service = get_aiops_service()
        causes = service.analyze_root_cause(anomaly_id)
        return {"anomaly_id": anomaly_id, "root_causes": causes}

    @app.get(
        "/golden-signals",
        response_model=GoldenSignalsResponse,
        tags=["Telemetry"],
        summary="إشارات ذهبية (SRE)",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_golden_signals() -> GoldenSignalsResponse:
        """استرجاع الإشارات الذهبية للتوافق مع المونوليث."""
        service = get_aiops_service()
        return GoldenSignalsResponse(**service.get_golden_signals())

    @app.get(
        "/performance",
        response_model=PerformanceSnapshotResponse,
        tags=["Telemetry"],
        summary="لقطة الأداء",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_performance_snapshot() -> PerformanceSnapshotResponse:
        """استرجاع لقطة الأداء الحالية."""
        service = get_aiops_service()
        return PerformanceSnapshotResponse(**service.get_performance_snapshot())

    @app.get(
        "/analytics/{path:path}",
        response_model=list[EndpointAnalyticsResponse],
        tags=["Telemetry"],
        summary="تحليلات نقطة النهاية",
        dependencies=[Depends(verify_service_token)],
    )
    async def get_endpoint_analytics(path: str) -> list[EndpointAnalyticsResponse]:
        """استرجاع تحليلات لنقطة نهاية محددة."""
        service = get_aiops_service()
        results = service.get_endpoint_analytics(path)
        return [EndpointAnalyticsResponse(**r) for r in results]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة خدمة المراقبة."""

    setup_logging(get_settings().SERVICE_NAME)
    logger.info("بدء تشغيل خدمة المراقبة")
    yield
    logger.info("إيقاف خدمة المراقبة")


def create_app(settings: ObservabilitySettings | None = None) -> FastAPI:
    """إنشاء تطبيق FastAPI لخدمة المراقبة مع إعدادات صريحة."""

    effective_settings = settings or get_settings()
    app = FastAPI(
        title="Observability Service",
        version=effective_settings.SERVICE_VERSION,
        description="خدمة مستقلة لتحليل القياسات",
        lifespan=lifespan,
    )
    _register_routes(app, effective_settings)
    setup_exception_handlers(app)
    return app


app = create_app()
