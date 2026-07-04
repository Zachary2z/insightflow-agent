from __future__ import annotations

from typing import Any

from agents.insight_agent import run_insight_agent
from llm_ops.provider import LLMProvider
from workspaces.evidence_auditor import run_evidence_auditor_agent


def run_business_answer_agent(
    state: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
    answer_reviewer_provider: LLMProvider | None = None,
    final_answer_composer_provider: LLMProvider | None = None,
    evidence_auditor_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    answered = run_insight_agent(
        dict(state),
        provider=provider,
        answer_reviewer_provider=answer_reviewer_provider,
        final_answer_composer_provider=final_answer_composer_provider,
    )
    audited = run_evidence_auditor_agent(answered, provider=evidence_auditor_provider)
    audited["status"] = "completed" if audited.get("insight", {}).get("success") else "failed"
    audited["data_used"] = audited.get("insight", {}).get("data_used", False)
    return audited


__all__ = ["run_business_answer_agent"]
