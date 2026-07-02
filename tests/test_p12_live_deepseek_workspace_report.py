import json
import os
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
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


def _load_report_trace(report: dict) -> dict:
    trace_path = Path(report["trace_path"])
    assert trace_path.is_file()
    return json.loads(trace_path.read_text(encoding="utf-8"))


def test_live_deepseek_workspace_report_uses_p22_document_contract(
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
    assert report["sections"] == []
    assert report["plan"]["title"] == "最近90天经营复盘报告"
    assert report["evidence_pack"]["facts"]
    assert report["document"]["sections"]
    assert report["validation"]["status"] == "passed"
    document_text = json.dumps(report["document"], ensure_ascii=False)
    assert "SELECT " not in document_text.upper()
    assert "provider_called" not in document_text
    assert str(workspace_db) not in document_text
    assert "data/ecommerce.db" not in document_text

    markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
    assert "# 最近90天经营复盘报告" in markdown
    assert "## 开篇摘要" in markdown
    assert "## 报告正文" in markdown
    assert "## 技术附录" in markdown
    assert markdown.index("## 开篇摘要") < markdown.index("## 技术附录")
    business_body = markdown.split("## 技术附录", 1)[0]
    appendix = markdown.split("## 技术附录", 1)[1]
    assert "```sql" not in business_body
    assert "provider_called" not in business_body
    assert "章节业务答案" not in business_body
    assert "#### 直接回答" not in business_body
    assert "#### 为什么" not in business_body
    assert "置信度" not in business_body
    assert "evidence_pack" in appendix

    trace = _load_report_trace(report)
    assert any(event.get("event") == "report_document_composed" for event in trace["events"])
