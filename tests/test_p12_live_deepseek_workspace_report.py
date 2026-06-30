import json
import os
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    provider_question_understanding_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
    provider_visualization_agent_enabled,
)
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore
from workspaces.synthetic_data import generate_general_business_dataset


pytestmark = pytest.mark.skipif(
    os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1",
    reason="Live DeepSeek tests are opt-in.",
)


def _require_live_deepseek_report_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "0")
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run the live P12 workspace report acceptance test.")
    if not provider_question_understanding_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1.")
    if not provider_sql_planning_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1.")
    if not provider_sql_candidate_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1.")
    if not provider_visualization_agent_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1.")


def _completed_sections(report: dict) -> list[dict]:
    return [
        section
        for section in report.get("sections", [])
        if section.get("status") == "completed"
    ]


def _section_provider_metadata(section: dict, key: str) -> dict:
    value = section.get("provider_metadata", {}).get(key)
    assert isinstance(value, dict), f"Missing section provider metadata: {key}"
    return value


def _load_report_trace(report: dict) -> dict:
    trace_path = Path(report["trace_path"])
    assert trace_path.is_file()
    return json.loads(trace_path.read_text(encoding="utf-8"))


def _section_trace_payloads(report: dict) -> list[dict]:
    trace = _load_report_trace(report)
    payloads = []
    for event in trace.get("events", []):
        section_trace_path = event.get("section_trace_path")
        if not section_trace_path:
            continue
        path = Path(section_trace_path)
        assert path.is_file()
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    return payloads


def _trace_nodes(payload: dict) -> set[str]:
    return {str(event.get("node")) for event in payload.get("trace", [])}


def test_live_deepseek_generates_workspace_report_with_real_provider_chain(
    tmp_path,
    monkeypatch,
):
    _require_live_deepseek_report_flags(monkeypatch)

    dataset_dir = tmp_path / "dataset"
    generate_general_business_dataset(dataset_dir, months=12)
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Live DeepSeek Report Workspace")
    workspace_db = Path(workspace["analysis_db_path"])
    import_csv(store, workspace["workspace_id"], dataset_dir / "orders.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "customers.csv")
    import_csv(store, workspace["workspace_id"], dataset_dir / "marketing_spend.csv")
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(
        store,
        workspace["workspace_id"],
        profile,
    )

    result = run_workspace_report(
        store=store,
        workspace_id=workspace["workspace_id"],
        report_type="business_review",
        report_goal=(
            "基于最近 90 天的订单、客户和营销数据，生成一份面向管理层的收入复盘报告，"
            "包含渠道表现、趋势变化、证据和可执行建议。"
        ),
    )

    report = result["report"]
    report_dir = Path(report["json_path"]).parent
    artifact_dir = Path(report["artifact_dir"])
    completed_sections = _completed_sections(report)

    assert profile["tables"]
    assert semantic_layer["metrics"]
    assert semantic_layer["dimensions"]
    assert result["success"] is True
    assert result["report_id"]
    assert report["status"] == "completed"
    assert report_dir.is_dir()
    assert artifact_dir.is_dir()
    assert Path(report["json_path"]).is_file()
    assert Path(report["markdown_path"]).is_file()
    assert Path(report["trace_path"]).is_file()
    assert len(report["sections"]) >= 3
    assert len(completed_sections) == len(report["sections"])

    for section in completed_sections:
        assert section["question"].strip()
        business_answer = section["business_answer"]
        assert business_answer["headline"].strip()
        assert business_answer["direct_answer"].strip()
        assert business_answer["why"].strip()
        assert isinstance(business_answer["evidence_bullets"], list)
        assert isinstance(business_answer["recommendations"], list)
        assert isinstance(business_answer["caveats"], list)
        assert business_answer["confidence"] in {"low", "medium", "high"}
        assert section["sql"].strip()
        assert section["rows_preview"]
        business_answer_text = json.dumps(business_answer, ensure_ascii=False)
        assert "SELECT " not in business_answer_text.upper()
        assert "provider_called" not in business_answer_text
        assert "这是自动报告内部 section" not in business_answer_text
        assert section["technical_details"]["internal_question"].startswith(
            "这是自动报告内部 section"
        )
        assert section["technical_details"]["sql"] == section["sql"]
        assert section["technical_details"]["provider_metadata"]
        assert "data/ecommerce.db" not in section["sql"]
        assert "sql_reviewer_agent" in section["trace_nodes"]
        assert "sql_executor_node" in section["trace_nodes"]
        assert _section_provider_metadata(section, "question_understanding")[
            "provider_called"
        ] is True
        assert _section_provider_metadata(section, "sql_planning")[
            "provider_called"
        ] is True
        assert _section_provider_metadata(section, "llm_sql_enhancement")[
            "provider_called"
        ] is True
        assert _section_provider_metadata(section, "visualization_trace")[
            "provider_called"
        ] is True

    section_trace_payloads = _section_trace_payloads(report)
    assert section_trace_payloads
    for payload in section_trace_payloads:
        nodes = _trace_nodes(payload)
        assert "sql_reviewer_agent" in nodes
        assert "sql_executor_node" in nodes
        schema_events = [
            event
            for event in payload.get("trace", [])
            if event.get("node") == "schema_agent"
        ]
        assert schema_events
        assert any(
            str(workspace_db) in event.get("tool_input_summary", "")
            for event in schema_events
        )
        assert all(
            "data/ecommerce.db" not in event.get("tool_input_summary", "")
            for event in schema_events
        )

    artifact_sections = [
        section for section in completed_sections if section.get("artifact_paths")
    ]
    assert artifact_sections
    first_artifact_path = artifact_sections[0]["artifact_paths"][0]
    first_artifact_file = report_dir / first_artifact_path
    assert first_artifact_file.is_file()
    assert first_artifact_file.is_relative_to(artifact_dir)
    assert any(
        _section_provider_metadata(section, "visualization_trace").get(
            "external_tool_called"
        )
        is True
        for section in completed_sections
    )

    markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
    assert "# Business Review" in markdown
    assert "## Executive Summary" in markdown
    assert "## Business Sections" in markdown
    assert "## Technical Appendix" in markdown
    assert markdown.index("## Executive Summary") < markdown.index("## Technical Appendix")
    business_body = markdown.split("## Technical Appendix", 1)[0]
    appendix = markdown.split("## Technical Appendix", 1)[1]
    assert "```sql" not in business_body
    assert "provider_called" not in business_body
    assert "这是自动报告内部 section" not in business_body
    assert "#### 结论" in business_body
    assert "#### 直接回答" in business_body
    assert "#### 为什么" in business_body
    assert "#### 关键证据" in business_body
    assert "#### 建议动作" in business_body
    assert "#### 限制说明" in business_body
    assert "#### 置信度" in business_body
    assert "```sql" in appendix
    assert "provider_called" in appendix
    assert first_artifact_path in markdown

    trace = _load_report_trace(report)
    assert any(event.get("event") == "section_completed" for event in trace["events"])
