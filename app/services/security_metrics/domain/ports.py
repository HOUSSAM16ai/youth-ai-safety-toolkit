"""
Security Metrics Domain Ports
Interfaces for security metrics operations
"""

from abc import ABC, abstractmethod
from typing import Protocol

from .models import RiskPrediction, SecurityFinding, SecurityMetrics


class RiskCalculatorPort(ABC):
    """Port for risk calculation"""

    @abstractmethod
    def calculate_risk_score(
        self, findings: list[SecurityFinding], code_metrics: dict | None = None
    ) -> float:
        """Calculate overall risk score"""
        pass

    @abstractmethod
    def calculate_exposure_factor(self, file_path: str, public_endpoints: int) -> float:
        """Calculate file exposure factor"""
        pass


class PredictiveAnalyticsPort(ABC):
    """Port for predictive analytics"""

    @abstractmethod
    def predict_future_risk(
        self, historical_metrics: list[SecurityMetrics], days_ahead: int = 30
    ) -> RiskPrediction:
        """Predict future risk based on historical data"""
        pass


class MetricsCalculatorPort(ABC):
    """Port for metrics calculation"""

    @abstractmethod
    def calculate_metrics(
        self, findings: list[SecurityFinding], code_metrics: dict | None = None
    ) -> SecurityMetrics:
        """Calculate comprehensive security metrics"""
        pass


class AnomalyDetectorPort(ABC):
    """Port for anomaly detection"""

    @abstractmethod
    def detect_anomalies(
        self, current_metrics: SecurityMetrics, historical_metrics: list[SecurityMetrics]
    ) -> list[dict]:
        """Detect anomalies in security metrics"""
        pass


class FindingsRepositoryPort(Protocol):
    """Port for findings persistence"""

    def save_finding(self, finding: SecurityFinding) -> None:
        """Save a security finding"""
        ...

    def get_findings(self, filters: dict | None = None) -> list[SecurityFinding]:
        """Get findings with optional filters"""
        ...

    def update_finding(self, finding_id: str, updates: dict) -> None:
        """Update a finding"""
        ...


class MetricsRepositoryPort(Protocol):
    """Port for metrics persistence"""

    def save_metrics(self, metrics: SecurityMetrics) -> None:
        """Save security metrics"""
        ...

    def get_historical_metrics(self, days: int = 30) -> list[SecurityMetrics]:
        """Get historical metrics"""
        ...
