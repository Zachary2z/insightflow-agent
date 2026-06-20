from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.action_drafter import run_action_drafter_agent
from llm_ops.provider import LLMProvider
from llm_ops.runtime_provider import build_action_drafter_provider
from tools.action_tool import DEFAULT_ACTION_DB_PATH
from tools.trace_logger import append_trace


def _primary_finding(state: dict[str, Any]) -> str:
    findings = state.get("evidence_result", {}).get("data_supported_findings", [])
    if findings:
        return str(findings[0].get("claim", "需要运营跟进的异常指标"))
    return "需要运营跟进的异常指标"


def _needs_more_data(state: dict[str, Any]) -> list[str]:
    needed = []
    for hypothesis in state.get("evidence_result", {}).get("hypotheses", []):
        for item in hypothesis.get("needs_more_data", []):
            if item not in needed:
                needed.append(str(item))
    return needed


def build_action_plan(state: dict[str, Any]) -> dict[str, Any]:
    finding = _primary_finding(state)
    needed = _needs_more_data(state)
    actions = [
        {
            "action_id": "action_follow_up_task",
            "action_type": "create_task",
            "title": "跟进经营异常指标",
            "description": f"请运营团队复查：{finding}",
            "owner": "运营团队",
            "priority": "high",
            "source": "evidence_result",
        },
        {
            "action_id": "action_metric_alert",
            "action_type": "create_metric_alert",
            "metric_name": "category_gmv_change",
            "condition": "below",
            "threshold": "-10%",
            "description": f"监控与复查：{finding}",
            "source": "evidence_result",
        },
    ]
    if needed:
        actions.append(
            {
                "action_id": "action_data_check_task",
                "action_type": "create_task",
                "title": "补充验证数据",
                "description": "补充或核查数据：" + ", ".join(needed),
                "owner": "数据团队",
                "priority": "medium",
                "source": "hypothesis",
            }
        )
    return {
        "success": True,
        "plan_type": "business_action_plan",
        "actions": actions,
        "source_finding": finding,
    }


def run_action_planner_agent(
    state: dict[str, Any],
    action_db_path: str | Path | None = None,
    action_draft_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    action_plan = build_action_plan(state)
    updated = {
        **state,
        "action_plan": action_plan,
        "action_db_path": action_db_path or state.get("action_db_path") or DEFAULT_ACTION_DB_PATH,
        "status": "action_plan_created",
    }
    planned = append_trace(
        updated,
        {
            "node": "action_planner_agent",
            "tool_name": "",
            "tool_input_summary": state.get("user_question", ""),
            "tool_output_summary": f"{len(action_plan['actions'])} actions planned",
            "status": "success",
            "latency_ms": 0,
        },
    )
    provider = action_draft_provider or build_action_drafter_provider()
    return run_action_drafter_agent(planned, provider=provider)
