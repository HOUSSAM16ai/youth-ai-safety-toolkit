from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | dict[str, "JsonValue"] | list["JsonValue"]

# ======================================================================================
# ENUMERATIONS
# ======================================================================================


class AnomalyType(Enum):
    """أنواع الشذوذ المحتملة في بيانات المراقبة."""

    LATENCY_SPIKE = "latency_spike"
    ERROR_RATE_INCREASE = "error_rate_increase"
    TRAFFIC_ANOMALY = "traffic_anomaly"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CAPACITY_LIMIT = "capacity_limit"
    PATTERN_DEVIATION = "pattern_deviation"


class AnomalySeverity(Enum):
    """درجات خطورة الشذوذ التي تساعد على ترتيب الأولويات."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class HealingAction(Enum):
    """إجراءات المعالجة الذاتية المتاحة لتحسين استقرار الخدمات."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART_SERVICE = "restart_service"
    INCREASE_TIMEOUT = "increase_timeout"
    ENABLE_CIRCUIT_BREAKER = "enable_circuit_breaker"
    ROUTE_TRAFFIC = "route_traffic"
    CLEAR_CACHE = "clear_cache"
    ADJUST_RATE_LIMIT = "adjust_rate_limit"


class MetricType(Enum):
    """أنواع المقاييس المستخدمة في نقاط القياس التشغيلية."""

    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    REQUEST_RATE = "request_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"


# ======================================================================================
# DATA STRUCTURES
# ======================================================================================


@dataclass
class TelemetryData:
    """تمثيل نقطة قياس تشغيلية بوصف عربي واضح للمبتدئين."""

    metric_id: str
    service_name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class AnomalyDetection:
    """سجل كشف شذوذ مع تفاصيل السياق والوقت والثقة."""

    anomaly_id: str
    service_name: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    detected_at: datetime
    metric_value: float
    expected_value: float
    confidence: float  # 0-1
    description: str
    root_causes: list[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: datetime | None = None


@dataclass
class LoadForecast:
    """توقع الحمل المستقبلي للخدمة مع معلومات الدقة."""

    forecast_id: str
    service_name: str
    forecast_timestamp: datetime
    predicted_load: float
    confidence_interval: tuple[float, float]
    model_accuracy: float
    generated_at: datetime


@dataclass
class HealingDecision:
    """قرار المعالجة الذاتية الناتج عن كشف الشذوذ."""

    decision_id: str
    anomaly_id: str
    service_name: str
    action: HealingAction
    reason: str
    parameters: dict[str, JsonValue]
    executed_at: datetime | None = None
    success: bool | None = None
    impact: dict[str, JsonValue] = field(default_factory=dict)


@dataclass
class CapacityPlan:
    """توصية تخطيط السعة للخدمة مع ثقة متوقعة."""

    plan_id: str
    service_name: str
    current_capacity: float
    recommended_capacity: float
    forecast_horizon_hours: int
    expected_peak_load: float
    confidence: float
    created_at: datetime
