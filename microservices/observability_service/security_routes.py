"""
Security Metrics API Router
Exposes endpoints for security metrics calculation and risk analysis
"""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from microservices.observability_service.security_metrics.application.metrics_calculator import (
    ComprehensiveMetricsCalculator,
)
from microservices.observability_service.security_metrics.application.predictive_analytics import (
    LinearRegressionPredictor,
)
from microservices.observability_service.security_metrics.application.risk_calculator import (
    AdvancedRiskCalculator,
)
from microservices.observability_service.security_metrics.domain.models import (
    SecurityFinding,
    SecurityMetrics,
    Severity,
    TrendDirection,
)

security_router = APIRouter(prefix="/security", tags=["Security Metrics"])

# ==============================================================================
# Schemas
# ==============================================================================


class SecurityFindingSchema(BaseModel):
    """Schema for a security finding"""

    id: str
    severity: Severity
    rule_id: str
    file_path: str
    line_number: int
    message: str
    cwe_id: str | None = None
    owasp_category: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    false_positive: bool = False
    fixed: bool = False
    fix_time_hours: float | None = None
    developer_id: str | None = None


class CalculateMetricsRequest(BaseModel):
    """Request to calculate security metrics"""

    findings: list[SecurityFindingSchema]
    code_metrics: dict | None = None


class SecurityMetricsResponse(BaseModel):
    """Response containing calculated security metrics"""

    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    findings_per_1000_loc: float
    new_findings_last_24h: int
    fixed_findings_last_24h: int
    false_positive_rate: float
    mean_time_to_detect: float
    mean_time_to_fix: float
    overall_risk_score: float
    security_debt_score: float
    trend_direction: str
    findings_per_developer: dict[str, int]
    fix_rate_per_developer: dict[str, float]
    timestamp: datetime


class RiskPredictionRequest(BaseModel):
    """Request to predict future risk"""

    historical_metrics: list[SecurityMetricsResponse]
    days_ahead: int = 30


class RiskPredictionResponse(BaseModel):
    """Response containing risk prediction"""

    predicted_risk: float
    confidence: float
    trend: str
    slope: float
    current_risk: float


class CalculateRiskRequest(BaseModel):
    """Request to calculate risk score"""

    findings: list[SecurityFindingSchema]
    code_metrics: dict | None = None


class CalculateRiskResponse(BaseModel):
    """Response containing risk score"""

    risk_score: float


# ==============================================================================
# Mappers
# ==============================================================================


def _map_finding_schema_to_domain(schema: SecurityFindingSchema) -> SecurityFinding:
    """Map Pydantic schema to Domain entity"""
    return SecurityFinding(
        id=schema.id,
        severity=schema.severity,
        rule_id=schema.rule_id,
        file_path=schema.file_path,
        line_number=schema.line_number,
        message=schema.message,
        cwe_id=schema.cwe_id,
        owasp_category=schema.owasp_category,
        first_seen=schema.first_seen,
        last_seen=schema.last_seen,
        false_positive=schema.false_positive,
        fixed=schema.fixed,
        fix_time_hours=schema.fix_time_hours,
        developer_id=schema.developer_id,
    )


def _map_metrics_domain_to_response(metrics: SecurityMetrics) -> SecurityMetricsResponse:
    """Map Domain entity to Pydantic response"""
    return SecurityMetricsResponse(
        total_findings=metrics.total_findings,
        critical_count=metrics.critical_count,
        high_count=metrics.high_count,
        medium_count=metrics.medium_count,
        low_count=metrics.low_count,
        findings_per_1000_loc=metrics.findings_per_1000_loc,
        new_findings_last_24h=metrics.new_findings_last_24h,
        fixed_findings_last_24h=metrics.fixed_findings_last_24h,
        false_positive_rate=metrics.false_positive_rate,
        mean_time_to_detect=metrics.mean_time_to_detect,
        mean_time_to_fix=metrics.mean_time_to_fix,
        overall_risk_score=metrics.overall_risk_score,
        security_debt_score=metrics.security_debt_score,
        trend_direction=metrics.trend_direction.value,
        findings_per_developer=metrics.findings_per_developer,
        fix_rate_per_developer=metrics.fix_rate_per_developer,
        timestamp=metrics.timestamp,
    )


def _map_metrics_response_to_domain(response: SecurityMetricsResponse) -> SecurityMetrics:
    """Map Pydantic response (historical) to Domain entity"""
    return SecurityMetrics(
        total_findings=response.total_findings,
        critical_count=response.critical_count,
        high_count=response.high_count,
        medium_count=response.medium_count,
        low_count=response.low_count,
        findings_per_1000_loc=response.findings_per_1000_loc,
        new_findings_last_24h=response.new_findings_last_24h,
        fixed_findings_last_24h=response.fixed_findings_last_24h,
        false_positive_rate=response.false_positive_rate,
        mean_time_to_detect=response.mean_time_to_detect,
        mean_time_to_fix=response.mean_time_to_fix,
        overall_risk_score=response.overall_risk_score,
        security_debt_score=response.security_debt_score,
        trend_direction=TrendDirection(response.trend_direction),
        findings_per_developer=response.findings_per_developer,
        fix_rate_per_developer=response.fix_rate_per_developer,
        timestamp=response.timestamp,
    )


# ==============================================================================
# Endpoints
# ==============================================================================


@security_router.post("/metrics/calculate", response_model=SecurityMetricsResponse)
async def calculate_metrics(request: CalculateMetricsRequest) -> SecurityMetricsResponse:
    """Calculate comprehensive security metrics from findings"""
    findings = [_map_finding_schema_to_domain(f) for f in request.findings]
    calculator = ComprehensiveMetricsCalculator()
    metrics = calculator.calculate_metrics(findings, request.code_metrics)
    return _map_metrics_domain_to_response(metrics)


@security_router.post("/risk/predict", response_model=RiskPredictionResponse)
async def predict_risk(request: RiskPredictionRequest) -> RiskPredictionResponse:
    """Predict future risk based on historical metrics"""
    historical_metrics = [_map_metrics_response_to_domain(m) for m in request.historical_metrics]
    predictor = LinearRegressionPredictor()
    prediction = predictor.predict_future_risk(historical_metrics, request.days_ahead)
    return RiskPredictionResponse(
        predicted_risk=prediction.predicted_risk,
        confidence=prediction.confidence,
        trend=prediction.trend.value,
        slope=prediction.slope,
        current_risk=prediction.current_risk,
    )


@security_router.post("/risk/score", response_model=CalculateRiskResponse)
async def calculate_risk(request: CalculateRiskRequest) -> CalculateRiskResponse:
    """Calculate advanced risk score from findings"""
    findings = [_map_finding_schema_to_domain(f) for f in request.findings]
    calculator = AdvancedRiskCalculator()
    risk_score = calculator.calculate_risk_score(findings, request.code_metrics)
    return CalculateRiskResponse(risk_score=risk_score)
