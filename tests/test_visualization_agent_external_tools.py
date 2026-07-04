from __future__ import annotations

import json
import zipfile
from pathlib import Path

from llm_ops.provider import MockLLMProvider


def _execution_result(rows: list[list[object]] | None = None) -> dict:
    data_rows = rows or [["Cameras", 1200.0], ["Audio", 900.0]]
    return {
        "success": True,
        "columns": ["category_name", "gmv"],
        "rows": data_rows,
        "row_count": len(data_rows),
    }


def _state(run_id: str = "run_visualization_agent_test") -> dict:
    return {
        "run_id": run_id,
        "session_id": f"session_{run_id}",
        "user_question": "把最近 30 天各品类 GMV 导出给财务复核。",
        "analysis_steps": [
            {
                "step_id": "category_gmv",
                "question": "Rank categories by GMV.",
                "required_metrics": ["gmv"],
                "required_dimensions": ["category"],
                "candidate_tables": ["orders", "order_items", "products", "categories"],
            }
        ],
        "execution_result": _execution_result(),
        "evidence_result": {
            "success": True,
            "data_supported_findings": [{"claim": "Cameras GMV is 1200.0."}],
            "hypotheses": [],
            "unsupported_claims_blocked": [],
        },
        "trace": [],
        "status": "completed",
    }


def _provider_output(delivery_tool_id: str = "local_renderer", **overrides) -> dict:
    payload = {
        "chart_spec": {
            "chart_type": "ranked_bar",
            "title": "Category GMV",
            "x": "category_name",
            "y": "gmv",
            "y_secondary": "",
            "series": "",
            "required_columns": ["category_name", "gmv"],
            "explanation_basis": ["supported_findings"],
            "unit": "元",
            "value_label": True,
            "business_annotation": "Cameras leads category GMV.",
        },
        "delivery_tool_id": delivery_tool_id,
        "tool_reason": "Use the selected delivery tool for the stakeholder workflow.",
    }
    payload.update(overrides)
    return payload


def _xlsx_values(path: Path) -> str:
    with zipfile.ZipFile(path) as workbook:
        return "\n".join(
            workbook.read(name).decode("utf-8")
            for name in workbook.namelist()
            if name.endswith(".xml")
        )


def test_provider_valid_output_selects_excel_exporter_and_writes_real_xlsx(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_excel_exporter"),
        provider=MockLLMProvider(_provider_output("excel_exporter")),
        output_dir=tmp_path,
    )

    delivery = result["visualization_delivery_result"]
    workbook_path = Path(delivery["artifact_path"])
    workbook_xml = _xlsx_values(workbook_path)

    assert result["visualization_decision"]["delivery_tool_id"] == "excel_exporter"
    assert delivery["success"] is True
    assert workbook_path.exists()
    assert delivery["external_tool_called"] is True
    assert delivery["data_row_count"] == 2
    assert delivery["fabricated_data"] is False
    assert "Cameras" in workbook_xml
    assert "Audio" in workbook_xml
    assert "1200" in workbook_xml
    assert "not-real" not in workbook_xml


def test_provider_powerbi_mock_selection_is_rejected_and_falls_back_to_local_renderer(tmp_path, monkeypatch):
    from agents.visualization_agent import run_visualization_agent

    monkeypatch.delenv("POWERBI_API_KEY", raising=False)
    result = run_visualization_agent(
        _state("run_powerbi_mock"),
        provider=MockLLMProvider(_provider_output("powerbi_publisher_mock")),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    delivery = result["visualization_delivery_result"]
    assert decision["provider_called"] is True
    assert decision["fallback_used"] is True
    assert decision["delivery_tool_id"] == "local_renderer"
    assert "powerbi_publisher_mock" in decision["validation_error"]
    assert delivery["success"] is True
    assert Path(delivery["artifact_path"]).exists()
    assert delivery["artifact_url"] == ""
    assert delivery["external_tool_called"] is True
    assert delivery["tool_type"] == "local_artifact"
    assert delivery["fabricated_data"] is False


def test_provider_valid_output_selects_local_renderer_and_calls_real_renderer(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_local_renderer"),
        provider=MockLLMProvider(_provider_output("local_renderer")),
        output_dir=tmp_path,
    )

    delivery = result["visualization_delivery_result"]
    assert delivery["success"] is True
    assert delivery["chart_type"] == "ranked_bar"
    assert Path(delivery["artifact_path"]).exists()
    assert result["visualization_decision"]["chart_spec"]["unit"] == "元"
    assert result["visualization_decision"]["chart_spec"]["value_label"] is True
    assert result["visualization_trace"]["business_annotation"] == "Cameras leads category GMV."
    assert delivery["external_tool_called"] is True
    assert delivery["rendered_rows"] == _execution_result()["rows"]
    assert delivery["fabricated_data"] is False


def test_provider_output_with_sql_is_rejected_and_falls_back(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_sql_leak"),
        provider=MockLLMProvider(_provider_output("excel_exporter", sql="SELECT * FROM orders")),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    assert decision["provider_called"] is True
    assert decision["fallback_used"] is True
    assert decision["validation_error"]
    assert "SELECT * FROM orders" not in json.dumps(decision)


def test_provider_output_with_final_claims_is_rejected_and_falls_back(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_claim_leak"),
        provider=MockLLMProvider(_provider_output("local_renderer", final_claims=["GMV will double next week."])),
        output_dir=tmp_path,
    )

    assert result["visualization_decision"]["fallback_used"] is True
    assert result["visualization_decision"]["validation_error"]


def test_provider_output_with_action_payload_is_rejected_and_falls_back(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_action_leak"),
        provider=MockLLMProvider(_provider_output("local_renderer", action_payload={"send_email": True})),
        output_dir=tmp_path,
    )

    assert result["visualization_decision"]["fallback_used"] is True
    assert result["visualization_decision"]["validation_error"]


def test_provider_output_with_credentials_or_secrets_is_rejected_and_falls_back(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_secret_leak"),
        provider=MockLLMProvider(_provider_output("powerbi_publisher_mock", credentials={"api_key": "sk-test"})),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    assert decision["fallback_used"] is True
    assert decision["validation_error"]
    assert "sk-test" not in json.dumps(result)


def test_provider_malformed_json_falls_back_without_crashing(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_malformed_json"),
        provider=MockLLMProvider('{"chart_spec": {"chart_type": "ranked_bar"},'),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    assert decision["success"] is True
    assert decision["source"] == "fallback"
    assert decision["provider_called"] is True
    assert decision["fallback_used"] is True
    assert decision["provider_error"]


def test_provider_missing_columns_are_rejected_by_chart_validator(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    invalid = _provider_output("local_renderer")
    invalid["chart_spec"] = {**invalid["chart_spec"], "y": "net_gmv", "required_columns": ["category_name", "net_gmv"]}

    result = run_visualization_agent(
        _state("run_missing_column"),
        provider=MockLLMProvider(invalid),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    assert decision["fallback_used"] is True
    assert "net_gmv" in decision["validation_error"]


def test_provider_unknown_delivery_tool_is_rejected_by_policy(tmp_path):
    from agents.visualization_agent import run_visualization_agent

    result = run_visualization_agent(
        _state("run_unknown_tool"),
        provider=MockLLMProvider(_provider_output("tableau_publisher")),
        output_dir=tmp_path,
    )

    decision = result["visualization_decision"]
    assert decision["fallback_used"] is True
    assert "tableau_publisher" in decision["validation_error"]
    assert result["visualization_delivery_result"]["tool_id"] == "local_renderer"


def test_excel_exporter_only_writes_execution_result_rows(tmp_path):
    from tools.external_visualization_tool import call_external_visualization_tool

    execution_result = _execution_result(rows=[["OnlyRealRow", 777.0]])
    result = call_external_visualization_tool(
        delivery_tool_id="excel_exporter",
        chart_spec=_provider_output()["chart_spec"],
        execution_result=execution_result,
        run_id="run_excel_real_rows",
        output_dir=tmp_path,
    )
    workbook_xml = _xlsx_values(Path(result["artifact_path"]))

    assert result["success"] is True
    assert "OnlyRealRow" in workbook_xml
    assert "Cameras" not in workbook_xml
    assert result["exported_rows"] == execution_result["rows"]
    assert result["fabricated_data"] is False


def test_local_renderer_only_uses_execution_result_rows(tmp_path):
    from tools.external_visualization_tool import call_external_visualization_tool

    execution_result = _execution_result(rows=[["OnlyRealRow", 777.0]])
    result = call_external_visualization_tool(
        delivery_tool_id="local_renderer",
        chart_spec=_provider_output()["chart_spec"],
        execution_result=execution_result,
        run_id="run_renderer_real_rows",
        output_dir=tmp_path,
    )

    assert result["success"] is True
    assert result["rendered_rows"] == [["OnlyRealRow", 777.0]]
    assert result["fabricated_data"] is False


def test_powerbi_mock_delivery_tool_is_not_a_runtime_option(tmp_path, monkeypatch):
    from tools.external_visualization_tool import call_external_visualization_tool

    monkeypatch.delenv("POWERBI_API_KEY", raising=False)
    result = call_external_visualization_tool(
        delivery_tool_id="powerbi_publisher_mock",
        chart_spec=_provider_output()["chart_spec"],
        execution_result=_execution_result(),
        run_id="run_powerbi_no_auth",
        output_dir=tmp_path,
    )

    assert result["success"] is False
    assert result["artifact_url"] == ""
    assert result["external_tool_called"] is False
    assert "Unknown delivery tool: powerbi_publisher_mock" in result["error"]


def test_workflow_visualization_trace_records_provider_fallback_when_mock_saas_is_requested(tmp_path):
    from graph.workflow import run_workflow

    result = run_workflow(
        "最近 30 天各品类销售额表现有什么差异，哪个品类最值得关注？",
        db_path=Path(__file__).resolve().parents[1] / "data" / "ecommerce.db",
        trace_dir=tmp_path,
        run_id="run_workflow_visualization_trace",
        session_id="session_workflow_visualization_trace",
        initial_sql=(
            "SELECT c.category_name AS category_name, SUM(oi.quantity * oi.unit_price) AS gmv "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.id "
            "JOIN categories c ON p.category_id = c.id "
            "JOIN orders o ON oi.order_id = o.id "
            "WHERE o.status = 'paid' "
            "GROUP BY c.category_name ORDER BY gmv DESC LIMIT 5"
        ),
        visualization_agent_provider=MockLLMProvider(_provider_output("powerbi_publisher_mock")),
    )

    trace_event = next(event for event in result["trace"] if event.get("node") == "visualization_agent")
    assert result["visualization_trace"]["provider_called"] is True
    assert result["visualization_trace"]["fallback_used"] is True
    assert result["visualization_trace"]["delivery_tool_id"] == "local_renderer"
    assert result["visualization_trace"]["external_tool_called"] is True
    assert result["visualization_trace"]["prompt_id"] == "visualization_agent"
    assert "powerbi_publisher_mock" in result["visualization_trace"]["validation_error"]
    assert result["visualization_trace"]["provider_error"] == ""
    assert trace_event["provider_called"] is True
    assert trace_event["fallback_used"] is True
    assert trace_event["delivery_tool_id"] == "local_renderer"
    assert trace_event["external_tool_called"] is True
    assert trace_event["prompt_id"] == "visualization_agent"
