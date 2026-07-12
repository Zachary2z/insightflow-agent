from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Protocol, TextIO

from observability.events import build_observability_event
from observability.redaction import sanitize_observability_fields


LOGGER_NAME = "insightflow.observability"
SAFE_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class EventEmitter(Protocol):
    def __call__(self, event: str, **fields: object) -> Any: ...


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = sanitize_observability_fields(getattr(record, "observability_event", {}))
        return json.dumps(event, ensure_ascii=False, separators=(",", ":"))


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = sanitize_observability_fields(getattr(record, "observability_event", {}))
        ordered = ("timestamp", "level", "event", "request_id", "run_id", "workspace_id", "report_id", "http_method", "route", "status", "status_code", "latency_ms", "event_count", "error_type")
        return " ".join(f"{field}={event[field]}" for field in ordered if field in event)


def _safe_format(value: object) -> str:
    return value.lower() if type(value) is str and value.lower() in {"json", "text"} else "json"


def _safe_level(value: object) -> int:
    return SAFE_LEVELS.get(value.upper(), logging.INFO) if type(value) is str else logging.INFO


def configure_observability_logging(
    *,
    log_format: str | None = None,
    level: str | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure the isolated InsightFlow event logger without touching root/third-party loggers."""
    selected_format = _safe_format(log_format if log_format is not None else os.getenv("INSIGHTFLOW_LOG_FORMAT", "json"))
    selected_level = _safe_level(level if level is not None else os.getenv("INSIGHTFLOW_LOG_LEVEL", "INFO"))
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(selected_level)
    logger.propagate = False

    handlers = [handler for handler in logger.handlers if getattr(handler, "_insightflow_observability", False)]
    if handlers:
        handler = handlers[0]
        for duplicate in handlers[1:]:
            logger.removeHandler(duplicate)
    else:
        handler = logging.StreamHandler(stream or sys.stdout)
        handler._insightflow_observability = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    if stream is not None and getattr(handler, "stream", None) is not stream:
        handler.setStream(stream)
    handler.setLevel(selected_level)
    handler.setFormatter(JsonFormatter() if selected_format == "json" else TextFormatter())
    return logger


def emit_observability_event(
    event: str,
    *,
    logger: logging.Logger | Any | None = None,
    **fields: object,
) -> None:
    """Build and emit one safe event; observability failures never affect business work."""
    try:
        payload = build_observability_event(event, **fields)
        selected_logger = logger or configure_observability_logging()
        selected_logger.log(
            SAFE_LEVELS[payload["level"].upper()],
            payload["event"],
            extra={"observability_event": payload},
        )
    except Exception:
        return None


def safely_emit(emitter: EventEmitter, event: str, **fields: object) -> None:
    try:
        emitter(event, **fields)
    except Exception:
        return None
