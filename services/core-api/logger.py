# ====================================================================================================
# PROJECT "HOSPITAL" — ENTERPRISE STRUCTURED OBSERVABILITY & LOGGING
# ====================================================================================================
# Module: services/core-api/logger.py
# Purpose: High-throughput structured JSON logging with context-propagated correlation IDs,
#          standardized severity levels, and zero-dependency cloud-native formatting.
# ====================================================================================================

import os
import sys
import json
import logging
import traceback
import contextvars
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Context variable for request correlation / distributed tracing
_CORRELATION_ID: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
_TENANT_ID: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id", default="GLOBAL")


def set_correlation_id(correlation_id: str):
    """Sets the correlation ID for the current async or thread context."""
    _CORRELATION_ID.set(correlation_id)


def get_correlation_id() -> str:
    """Gets the active correlation ID or empty string."""
    return _CORRELATION_ID.get()


def set_context_tenant(tenant_id: str):
    """Sets the active tenant ID for the current context."""
    _TENANT_ID.set(tenant_id)


def get_context_tenant() -> str:
    """Gets the active tenant ID."""
    return _TENANT_ID.get()


class JSONFormatter(logging.Formatter):
    """
    Standardized JSON log formatter outputting machine-parseable log lines
    compatible with ELK, Datadog, CloudWatch, and GCP Cloud Logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id() or getattr(record, "correlation_id", None),
            "tenant_id": get_context_tenant() or getattr(record, "tenant_id", None),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Include custom kwargs passed via extra
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_entry.update(record.extra_fields)

        # Include traceback details if exception occurred
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stacktrace": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """
    Wrapper around python standard logging providing structured key-value context.
    """

    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(JSONFormatter())
            self._logger.addHandler(handler)
            self._logger.propagate = False

    def _log(self, level: int, msg: str, exc_info: bool = False, **kwargs):
        extra = {"extra_fields": kwargs}
        if "correlation_id" in kwargs:
            extra["correlation_id"] = kwargs.pop("correlation_id")
        if "tenant_id" in kwargs:
            extra["tenant_id"] = kwargs.pop("tenant_id")
        self._logger.log(level, msg, exc_info=exc_info, extra=extra)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, exc_info: bool = False, **kwargs):
        self._log(logging.ERROR, msg, exc_info=exc_info, **kwargs)

    def critical(self, msg: str, exc_info: bool = False, **kwargs):
        self._log(logging.CRITICAL, msg, exc_info=exc_info, **kwargs)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)


def get_logger(name: str = "hospital.core") -> StructuredLogger:
    """Factory function to obtain a singleton structured logger instance."""
    return StructuredLogger(name)
