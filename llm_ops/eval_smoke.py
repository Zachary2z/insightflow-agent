from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY, PromptRegistry
from llm_ops.provider import LLMProvider, LLMRequest, run_llm_request
from llm_ops.structured_output import run_validated_llm_request


def _missing_expected_keys(content: Any, expected_keys: list[str]) -> list[str]:
    if not isinstance(content, dict):
        return list(expected_keys)
    return [key for key in expected_keys if key not in content]


def run_llm_smoke_eval(
    cases: list[dict[str, Any]],
    provider: LLMProvider,
    registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
    model: str = "mock-free",
) -> dict[str, Any]:
    results = []
    for case in cases:
        case_id = str(case.get("case_id", "case_unknown"))
        prompt_id = str(case.get("prompt_id", ""))
        rendered = registry.render(prompt_id, case.get("variables", {}))
        if not rendered.get("success"):
            results.append(
                {
                    "case_id": case_id,
                    "prompt_id": prompt_id,
                    "success": False,
                    "error": rendered.get("error", "prompt rendering failed"),
                    "provider_result": None,
                }
            )
            continue

        request = LLMRequest(
            prompt=rendered["prompt"],
            prompt_id=rendered["prompt_id"],
            prompt_version=rendered["prompt_version"],
            model=model,
            metadata={"node": "llm_smoke_eval"},
        )
        validation_enabled = bool(case.get("validate_output", False))
        if validation_enabled:
            provider_result = run_validated_llm_request(
                provider,
                request,
                schema_context=case.get("schema_context", {}),
            )
        else:
            provider_result = run_llm_request(provider, request)

        expected_success = bool(case.get("expected_success", True))
        missing = (
            _missing_expected_keys(provider_result.get("content"), list(case.get("expected_keys", [])))
            if provider_result.get("success")
            else list(case.get("expected_keys", []))
        )
        expected_error_type = str(case.get("expected_error_type", "")).strip()
        actual_error_type = str(provider_result.get("error_type", "")).strip()
        if expected_success:
            success = bool(provider_result.get("success")) and not missing
            error = "" if success else f"missing expected keys: {', '.join(missing)}"
        else:
            error_type_matches = not expected_error_type or actual_error_type == expected_error_type
            success = not provider_result.get("success") and error_type_matches
            error = "" if success else f"expected failure {expected_error_type or '<any>'}, got {actual_error_type or '<none>'}"
        results.append(
            {
                "case_id": case_id,
                "prompt_id": prompt_id,
                "success": success,
                "error": error,
                "validation_enabled": validation_enabled,
                "expected_success": expected_success,
                "provider_result": provider_result,
            }
        )

    passed = sum(1 for result in results if result["success"])
    failed = len(results) - passed
    return {
        "success": failed == 0,
        "total_cases": len(results),
        "passed": passed,
        "failed": failed,
        "cases": results,
    }
