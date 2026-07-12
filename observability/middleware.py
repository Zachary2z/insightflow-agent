from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from observability.context import bind_correlation_context, is_valid_correlation_id, reset_correlation_context


REQUEST_ID_HEADER = b"x-request-id"

ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[dict[str, Any]]], Callable[..., Awaitable[None]]], Awaitable[None]]


def generate_request_id() -> str:
    return f"req_{uuid4().hex}"


def select_request_id(candidate: object | None) -> str:
    return candidate if is_valid_correlation_id(candidate) else generate_request_id()


class CorrelationMiddleware:
    """Minimal request correlation only; logging and metrics belong to later P38 tasks."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[dict[str, Any]]], send: Callable[..., Awaitable[None]]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        header_values = [
            value.decode("latin-1")
            for name, value in scope.get("headers", [])
            if name.lower() == REQUEST_ID_HEADER
        ]
        request_id = select_request_id(header_values[0] if len(header_values) == 1 else None)
        token = bind_correlation_context(request_id=request_id)

        async def send_with_request_id(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != REQUEST_ID_HEADER
                ]
                headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            reset_correlation_context(token)
