from __future__ import annotations

import json
from json import JSONDecodeError
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol


MODEL_PRICING_PER_1K_TOKENS = {
    "mock-free": {"input": 0.0, "output": 0.0},
}


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    prompt_id: str
    prompt_version: str
    model: str = "mock-free"
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    model: str

    def generate(self, request: LLMRequest) -> dict[str, Any] | str:
        ...


class MockLLMProvider:
    def __init__(self, response: dict[str, Any] | str, model: str = "mock-free"):
        self.response = response
        self.model = model

    def generate(self, request: LLMRequest) -> dict[str, Any] | str:
        return self.response


def provider_metadata(response: dict[str, Any], *, default_prompt_id: str) -> dict[str, Any]:
    return {
        "model": response.get("model", ""),
        "prompt_id": response.get("prompt_id", default_prompt_id),
        "prompt_version": response.get("prompt_version", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }


def provider_error_fields(error: str, error_type: str = "") -> dict[str, str]:
    is_validation_error = error_type == "llm_schema_validation_error"
    return {
        "provider_error": "" if is_validation_error else error,
        "validation_error": error if is_validation_error else "",
    }


def provider_failure(error: str, *, provider_called: bool, error_type: str = "") -> dict[str, Any]:
    return {
        "success": False,
        "source": "provider",
        "provider_called": provider_called,
        "fallback_used": False,
        "provider_error": error,
        "validation_error": error if error_type == "llm_schema_validation_error" else "",
        "error": error,
        **({"error_type": error_type} if error_type else {}),
    }


def _token_count(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, len(text.split()))


def _estimated_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING_PER_1K_TOKENS.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens / 1000 * pricing["input"]) + (output_tokens / 1000 * pricing["output"])
    return round(cost, 8)


def _parse_content(raw: dict[str, Any] | str) -> dict[str, Any] | str:
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return json.loads(stripped)
        return raw
    return raw


def _trace_event(
    request: LLMRequest,
    status: str,
    latency_ms: int,
    usage: dict[str, Any],
    error: str = "",
    error_type: str = "llm_provider_error",
) -> dict[str, Any]:
    event = {
        "node": request.metadata.get("node", "llm_ops"),
        "tool_name": "llm_provider",
        "tool_input_summary": f"{request.prompt_id}@{request.prompt_version}",
        "tool_output_summary": "model-assisted step completed" if status == "success" else error,
        "status": status,
        "latency_ms": latency_ms,
        "model": request.model,
        "prompt_id": request.prompt_id,
        "prompt_version": request.prompt_version,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "estimated_cost_usd": usage["estimated_cost_usd"],
    }
    if error:
        event["error_type"] = error_type
        event["error"] = error
    return event


def run_llm_request(provider: LLMProvider, request: LLMRequest) -> dict[str, Any]:
    started_at = perf_counter()
    usage = {"input_tokens": _token_count(request.prompt), "output_tokens": 0, "estimated_cost_usd": 0.0}

    try:
        raw_content = provider.generate(request)
        content = _parse_content(raw_content)
        latency_ms = int((perf_counter() - started_at) * 1000)
        output_tokens = _token_count(content)
        usage = {
            "input_tokens": usage["input_tokens"],
            "output_tokens": output_tokens,
            "estimated_cost_usd": _estimated_cost(request.model, usage["input_tokens"], output_tokens),
        }
        return {
            "success": True,
            "content": content,
            "model": request.model,
            "prompt_id": request.prompt_id,
            "prompt_version": request.prompt_version,
            "usage": usage,
            "latency_ms": latency_ms,
            "error": "",
            "trace_event": _trace_event(request, "success", latency_ms, usage),
        }
    except JSONDecodeError as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = str(exc)
        error_type = "llm_malformed_json_error"
        return {
            "success": False,
            "content": None,
            "model": request.model,
            "prompt_id": request.prompt_id,
            "prompt_version": request.prompt_version,
            "usage": usage,
            "latency_ms": latency_ms,
            "error": error,
            "error_type": error_type,
            "trace_event": _trace_event(request, "error", latency_ms, usage, error, error_type),
        }
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = str(exc)
        error_type = "llm_provider_error"
        return {
            "success": False,
            "content": None,
            "model": request.model,
            "prompt_id": request.prompt_id,
            "prompt_version": request.prompt_version,
            "usage": usage,
            "latency_ms": latency_ms,
            "error": error,
            "error_type": error_type,
            "trace_event": _trace_event(request, "error", latency_ms, usage, error, error_type),
        }
