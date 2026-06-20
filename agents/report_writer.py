from __future__ import annotations

from typing import Any

from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY
from llm_ops.provider import LLMProvider, LLMRequest
from llm_ops.structured_output import run_validated_llm_request
from tools.trace_logger import append_trace


def _claim_texts(items: list[Any], key: str = "claim") -> list[str]:
    texts = []
    for item in items:
        if isinstance(item, dict):
            value = str(item.get(key, "")).strip()
        else:
            value = str(item).strip()
        if value:
            texts.append(value)
    return texts


def _collect_evidence_inputs(state: dict[str, Any]) -> dict[str, list[str] | str]:
    tasks = state.get("report_sub_tasks") or []
    if tasks:
        findings: list[str] = []
        hypotheses: list[str] = []
        blocked: list[str] = []
        sql_records: list[str] = []
        chart_paths: list[str] = []
        for task in tasks:
            evidence = task.get("evidence_result", {})
            findings.extend(_claim_texts(evidence.get("data_supported_findings", [])))
            hypotheses.extend(_claim_texts(evidence.get("hypotheses", [])))
            blocked.extend(_claim_texts(evidence.get("unsupported_claims_blocked", [])))
            if task.get("sql"):
                sql_records.append(str(task["sql"]))
            chart_paths.extend(str(path) for path in task.get("chart_paths", []) if str(path).strip())
        return {
            "verified_findings": list(dict.fromkeys(findings)),
            "verified_hypotheses": list(dict.fromkeys(hypotheses)),
            "blocked_unsupported_claims": list(dict.fromkeys(blocked)),
            "sql_records": sql_records,
            "chart_paths": list(dict.fromkeys(chart_paths)),
            "trace_path": str(state.get("trace_path", "")),
        }

    evidence = state.get("evidence_result", {})
    return {
        "verified_findings": _claim_texts(evidence.get("data_supported_findings", [])),
        "verified_hypotheses": _claim_texts(evidence.get("hypotheses", [])),
        "blocked_unsupported_claims": _claim_texts(evidence.get("unsupported_claims_blocked", [])),
        "sql_records": [str(state.get("generated_sql", "")).strip()] if state.get("generated_sql") else [],
        "chart_paths": [str(path) for path in state.get("chart_paths", []) if str(path).strip()],
        "trace_path": str(state.get("trace_path", "")),
    }


def _deterministic_result(
    evidence_inputs: dict[str, Any],
    provider_called: bool,
    provider_error: str = "",
    validation_error: str = "",
) -> dict[str, Any]:
    findings = list(evidence_inputs.get("verified_findings", []))
    hypotheses = list(evidence_inputs.get("verified_hypotheses", []))
    summary = findings[:3] or ["暂无可写入确定性摘要的数据支持结论。"]
    next_steps = hypotheses[:3] or ["复核已验证结论，并结合业务上下文确定后续行动。"]
    narrative_parts = []
    if findings:
        narrative_parts.append("；".join(findings[:3]))
    if hypotheses:
        narrative_parts.append("需进一步验证：" + "；".join(hypotheses[:2]))
    business_narrative = "。".join(narrative_parts) if narrative_parts else "当前报告保持确定性表达，未加入未验证结论。"
    return {
        "success": not provider_called,
        "source": "deterministic",
        "provider_called": provider_called,
        "fallback_used": True,
        "executive_summary": summary,
        "business_narrative": business_narrative,
        "next_steps": next_steps,
        "used_supported_claims": findings,
        "used_hypotheses": hypotheses,
        "unsupported_claims": [],
        "unsupported_claims_blocked": list(evidence_inputs.get("blocked_unsupported_claims", [])),
        "provider_error": provider_error,
        "validation_error": validation_error,
    }


def _provider_result(state: dict[str, Any], provider: LLMProvider, evidence_inputs: dict[str, Any]) -> dict[str, Any]:
    rendered = DEFAULT_PROMPT_REGISTRY.render(
        "report_writer",
        {
            "user_question": state.get("user_question", ""),
            **evidence_inputs,
        },
    )
    if not rendered.get("success"):
        return _deterministic_result(evidence_inputs, provider_called=True, provider_error=rendered.get("error", ""))

    request = LLMRequest(
        prompt=rendered["prompt"],
        prompt_id=rendered["prompt_id"],
        prompt_version=rendered["prompt_version"],
        model=getattr(provider, "model", "unknown"),
        metadata={"node": "report_writer_agent"},
    )
    response = run_validated_llm_request(
        provider,
        request,
        schema_context={
            "verified_findings": evidence_inputs.get("verified_findings", []),
            "verified_hypotheses": evidence_inputs.get("verified_hypotheses", []),
            "blocked_unsupported_claims": evidence_inputs.get("blocked_unsupported_claims", []),
        },
    )
    if not response.get("success"):
        if response.get("error_type") == "llm_schema_validation_error":
            return _deterministic_result(
                evidence_inputs,
                provider_called=True,
                validation_error=response.get("error", ""),
            )
        return _deterministic_result(
            evidence_inputs,
            provider_called=True,
            provider_error=response.get("error", ""),
        )

    content = response.get("content", {})
    return {
        "success": True,
        "source": "provider",
        "provider_called": True,
        "fallback_used": False,
        **content,
        "unsupported_claims_blocked": list(evidence_inputs.get("blocked_unsupported_claims", [])),
        "provider_error": "",
        "validation_error": "",
        "model": response.get("model", ""),
        "prompt_id": response.get("prompt_id", "report_writer"),
        "prompt_version": response.get("prompt_version", ""),
        "usage": response.get("usage", {}),
        "latency_ms": response.get("latency_ms", 0),
    }


def run_report_writer_agent(
    state: dict[str, Any],
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    evidence_inputs = _collect_evidence_inputs(state)
    provider_called = provider is not None
    result = _provider_result(state, provider, evidence_inputs) if provider else _deterministic_result(
        evidence_inputs,
        provider_called=False,
    )
    updated = {
        **state,
        "report_writer_result": result,
    }
    return append_trace(
        updated,
        {
            "node": "report_writer_agent",
            "tool_name": "provider_report_writer" if provider_called else "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": (
                "provider polished report prose"
                if result.get("source") == "provider"
                else "deterministic report prose fallback"
            ),
            "status": "success" if not result.get("validation_error") and not result.get("provider_error") else "error",
            "latency_ms": result.get("latency_ms", 0),
            "error_type": "report_writer_validation_error" if result.get("validation_error") else None,
            "error": result.get("validation_error") or result.get("provider_error") or None,
            "provider_called": provider_called,
            "fallback_used": bool(result.get("fallback_used")),
        },
    )
