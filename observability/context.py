from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Mapping, TypedDict

from observability.redaction import safe_identifier


MAX_CORRELATION_ID_LENGTH = 64
CORRELATION_FIELDS = (
    "request_id",
    "run_id",
    "session_id",
    "workspace_id",
    "report_id",
)
class CorrelationContext(TypedDict, total=False):
    request_id: str
    run_id: str
    session_id: str
    workspace_id: str
    report_id: str


_correlation_context: ContextVar[CorrelationContext] = ContextVar(
    "insightflow_correlation_context",
    default={},
)
CorrelationToken = Token[CorrelationContext]


def is_valid_correlation_id(value: object) -> bool:
    """Return whether a value is a bounded opaque identifier safe for signals."""
    return safe_identifier(value) is not None


def _validated_bindings(values: Mapping[str, object | None]) -> CorrelationContext:
    bindings: CorrelationContext = {}
    for field, value in values.items():
        if field not in CORRELATION_FIELDS:
            raise TypeError(f"Unsupported correlation field: {field}")
        if value is None or value == "":
            continue
        if not is_valid_correlation_id(value):
            raise ValueError(f"Invalid {field}")
        bindings[field] = value
    return bindings


def get_correlation_context() -> CorrelationContext:
    """Return a copy so callers cannot mutate the current task's context."""
    return dict(_correlation_context.get())


def bind_correlation_context(
    *,
    request_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    workspace_id: str | None = None,
    report_id: str | None = None,
) -> CorrelationToken:
    """Temporarily merge validated identifiers into the current context."""
    bindings = _validated_bindings(
        {
            "request_id": request_id,
            "run_id": run_id,
            "session_id": session_id,
            "workspace_id": workspace_id,
            "report_id": report_id,
        }
    )
    merged: CorrelationContext = {**_correlation_context.get(), **bindings}
    return _correlation_context.set(merged)


def reset_correlation_context(token: CorrelationToken) -> None:
    """Restore the exact context snapshot that preceded a bind."""
    _correlation_context.reset(token)


@contextmanager
def correlation_scope(
    *,
    request_id: str | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    workspace_id: str | None = None,
    report_id: str | None = None,
) -> Iterator[CorrelationContext]:
    """Bind a partial context and always restore the parent, including on errors."""
    token = bind_correlation_context(
        request_id=request_id,
        run_id=run_id,
        session_id=session_id,
        workspace_id=workspace_id,
        report_id=report_id,
    )
    try:
        yield get_correlation_context()
    finally:
        reset_correlation_context(token)
