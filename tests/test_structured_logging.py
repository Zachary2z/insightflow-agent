from __future__ import annotations

import io
import json
import logging

import pytest

from observability.logging import (
    JsonFormatter,
    configure_observability_logging,
    emit_observability_event,
)
from observability.redaction import OBSERVABILITY_FIELD_ALLOWLIST


def _lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


def test_json_logging_writes_one_allowlisted_event_per_line():
    stream = io.StringIO()
    logger = configure_observability_logging(log_format="json", level="INFO", stream=stream)

    emit_observability_event(
        "workflow_run_completed",
        logger=logger,
        status="success",
        operation="analysis",
        latency_ms=7,
        prompt="private prompt",
        rows=[{"secret": "raw rows"}],
    )

    events = _lines(stream)
    assert len(events) == 1
    assert events[0]["event"] == "workflow_run_completed"
    assert set(events[0]) <= OBSERVABILITY_FIELD_ALLOWLIST
    assert "private prompt" not in stream.getvalue()
    assert "raw rows" not in stream.getvalue()


def test_configuration_is_idempotent_and_updates_safe_format_and_level():
    stream = io.StringIO()
    logger = configure_observability_logging(log_format="json", level="INFO", stream=stream)
    same_logger = configure_observability_logging(log_format="text", level="ERROR", stream=stream)

    assert same_logger is logger
    assert len([handler for handler in logger.handlers if getattr(handler, "_insightflow_observability", False)]) == 1
    assert logger.level == logging.ERROR
    assert not isinstance(logger.handlers[0].formatter, JsonFormatter)


@pytest.mark.parametrize("log_format", ["unknown", "", "pkg.CustomFormatter"])
def test_unknown_format_falls_back_to_json(log_format):
    logger = configure_observability_logging(log_format=log_format, level="INFO", stream=io.StringIO())
    assert isinstance(logger.handlers[0].formatter, JsonFormatter)


@pytest.mark.parametrize("level", ["TRACE", "", "pkg.CustomLevel"])
def test_unknown_level_falls_back_to_info(level):
    logger = configure_observability_logging(log_format="json", level=level, stream=io.StringIO())
    assert logger.level == logging.INFO


def test_emit_failure_is_swallowed():
    class FailingLogger:
        def log(self, *_args, **_kwargs):
            raise OSError("Bearer synthetic-token-do-not-leak /Users/private/project")

    assert emit_observability_event("http_request_started", logger=FailingLogger(), status="started") is None
