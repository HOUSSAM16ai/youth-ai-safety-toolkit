"""
Standardized Logging Module for CogniForge.

Provides structured logging configuration using python-json-logger in production
and readable console logging in development. Supports request correlation IDs.

Standards:
- JSON in Production.
- Correlation IDs for tracing.
- Redaction of sensitive keys (Secrets).
"""

import logging
import sys
from contextvars import ContextVar
from typing import Final

from pythonjsonlogger import jsonlogger

from .config import get_settings

# Correlation ID Context (for tracking requests across services)
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Keys to redact from logs
SENSITIVE_KEYS: Final[set[str]] = {
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "access_token",
}


class RedactingJsonFormatter(jsonlogger.JsonFormatter):
    """JSON Formatter that automatically redacts sensitive keys."""

    def process_log_record(self, log_record: dict[str, object]) -> dict[str, object]:
        """Redacts sensitive keys from the log record."""
        for key in list(log_record.keys()):
            if key.lower() in SENSITIVE_KEYS:
                log_record[key] = "***REDACTED***"

        # Also check inside 'message' if it's a dict (structured log)
        if isinstance(log_record.get("message"), dict):
            for key in list(log_record["message"].keys()):  # type: ignore
                if key.lower() in SENSITIVE_KEYS:
                    log_record["message"][key] = "***REDACTED***"  # type: ignore

        return super().process_log_record(log_record)


class CorrelationIdFilter(logging.Filter):
    """Injects the correlation ID into the log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = correlation_id.get()
        # Add to record so it appears in formatter
        record.correlation_id = cid  # type: ignore
        return True


def setup_logging(service_name: str | None = None) -> None:
    """
    Configures the root logger with structured JSON logging or colored console output.
    """
    settings = get_settings()
    log_level = settings.LOG_LEVEL.upper()

    # Determine service name
    svc_name = service_name or settings.SERVICE_NAME

    # Check environment
    is_production = settings.ENVIRONMENT in ("production", "staging")

    handler: logging.Handler
    formatter: logging.Formatter

    if is_production:
        # JSON format for Production (Observability)
        handler = logging.StreamHandler(sys.stdout)
        # We include service_name in the format string
        formatter = RedactingJsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(correlation_id)s %(service_name)s"
        )
    else:
        # Simple readable format for Dev
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers = []

    root_logger.addHandler(handler)

    # Add correlation ID filter to handler so it works even if we add multiple handlers
    handler.addFilter(CorrelationIdFilter())

    # Inject Service Name Record Factory
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        record.service_name = svc_name  # type: ignore
        return record

    logging.setLogRecordFactory(record_factory)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").disabled = True  # We use our own middleware
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Returns a logger instance with the given name."""
    return logging.getLogger(name)


# Export a default logger to satisfy imports expecting 'logger' from this module
logger = logging.getLogger("orchestrator")
