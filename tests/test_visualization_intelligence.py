from __future__ import annotations

from pathlib import Path


def _execution_result(columns: list[str], rows: list[list[object]]) -> dict:
    return {
        "success": True,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def _evidence_result() -> dict:
    return {
        "success": True,
        "data_supported_findings": [
            {"claim": "Cameras GMV is 1200 and refund_rate is 0.08.", "evidence": "SQL result row"}
        ],
        "hypotheses": [],
        "unsupported_claims_blocked": [],
    }


def _analysis_steps() -> list[dict]:
    return [
        {
            "step_id": "gmv_trend",
            "question": "Compare GMV and risk over time.",
            "required_metrics": ["gmv", "refund_rate"],
            "required_dimensions": ["category", "time"],
            "candidate_tables": ["orders", "refund_requests"],
        }
    ]


def _assert_spec_contract(spec: dict, chart_type: str, expected_columns: set[str]) -> None:
    assert spec["success"] is True
    assert spec["chart_type"] == chart_type
    assert spec["title"]
    assert spec["x"]
    assert spec["y"]
    assert "y_secondary" in spec
    assert "series" in spec
    assert set(spec["required_columns"]).issubset(expected_columns)
    assert spec["explanation_basis"] == ["supported_findings"]
    assert spec["provider_called"] is False
    assert spec["fallback_used"] is False
    assert spec["prompt_id"] == ""
    assert spec["validation_error"] == ""
    assert spec["provider_error"] == ""
    assert "sql" not in spec
    assert "final_claims" not in spec
    assert "action_payload" not in spec


def test_deterministic_visualization_planner_supports_first_batch_chart_types():
    from agents.visualization_planner import plan_visualization

    examples = [
        (
            "请画 Top category ranked bar",
            "ranked_bar",
            _execution_result(["category_name", "gmv"], [["Cameras", 1200.0], ["Audio", 900.0]]),
        ),
        (
            "请画 GMV line trend",
            "line",
            _execution_result(["date", "gmv"], [["2026-06-01", 1200.0], ["2026-06-02", 1300.0]]),
        ),
        (
            "请画 channel grouped bar comparison",
            "grouped_bar",
            _execution_result(
                ["category_name", "channel", "gmv"],
                [["Cameras", "Paid Search", 1200.0], ["Cameras", "Organic", 800.0]],
            ),
        ),
        (
            "请画 GMV 和 refund rate dual axis line",
            "dual_axis_line",
            _execution_result(
                ["date", "gmv", "refund_rate"],
                [["2026-06-01", 1200.0, 0.08], ["2026-06-02", 1300.0, 0.09]],
            ),
        ),
        (
            "请画转化 funnel",
            "funnel",
            _execution_result(
                ["stage", "users"],
                [["sessions", 1000], ["add_to_cart", 320], ["checkout", 180], ["paid", 120]],
            ),
        ),
        (
            "请画 city category heatmap",
            "heatmap",
            _execution_result(
                ["city", "category_name", "gmv"],
                [["Shanghai", "Cameras", 1200.0], ["Beijing", "Audio", 900.0]],
            ),
        ),
        (
            "请画 GMV vs refund rate scatter",
            "scatter",
            _execution_result(
                ["product_name", "gmv", "refund_rate"],
                [["Camera A", 1200.0, 0.08], ["Camera B", 900.0, 0.12]],
            ),
        ),
        (
            "请画 high value high risk matrix",
            "risk_matrix",
            _execution_result(
                ["product_name", "gmv", "refund_rate"],
                [["Camera A", 1200.0, 0.08], ["Camera B", 900.0, 0.12]],
            ),
        ),
    ]

    for question, chart_type, execution_result in examples:
        spec = plan_visualization(
            question,
            analysis_steps=_analysis_steps(),
            execution_result=execution_result,
            evidence_result=_evidence_result(),
        )
        _assert_spec_contract(spec, chart_type, set(execution_result["columns"]))


def test_chart_validator_rejects_columns_missing_from_execution_result():
    from visualization.chart_validator import validate_chart_spec

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    result = validate_chart_spec(
        {
            "chart_type": "ranked_bar",
            "title": "Bad chart",
            "x": "category_name",
            "y": "net_gmv",
            "y_secondary": "",
            "series": "",
            "required_columns": ["category_name", "net_gmv"],
            "explanation_basis": ["supported_findings"],
        },
        execution_result,
    )

    assert result["success"] is False
    assert "net_gmv" in result["validation_error"]


def test_chart_renderer_uses_only_real_execution_rows(tmp_path):
    from visualization.chart_renderer import render_chart

    execution_result = _execution_result(
        ["category_name", "gmv"],
        [["Cameras", 1200.0], ["Audio", 900.0]],
    )
    spec = {
        "chart_type": "ranked_bar",
        "title": "Top Categories",
        "x": "category_name",
        "y": "gmv",
        "y_secondary": "",
        "series": "",
        "required_columns": ["category_name", "gmv"],
        "explanation_basis": ["supported_findings"],
        "run_id": "run_visualization_renderer_test",
    }

    result = render_chart(execution_result, spec, output_dir=tmp_path)

    assert result["success"] is True
    assert result["chart_type"] == "ranked_bar"
    assert Path(result["chart_path"]).exists()
    assert result["data_row_count"] == 2
    assert result["rendered_rows"] == execution_result["rows"]
    assert result["fabricated_data"] is False


def test_unsupported_chart_type_falls_back_to_safe_table_or_basic_bar(tmp_path):
    from visualization.chart_renderer import render_chart

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    result = render_chart(
        execution_result,
        {
            "chart_type": "radar",
            "title": "Unsupported",
            "x": "category_name",
            "y": "gmv",
            "required_columns": ["category_name", "gmv"],
        },
        output_dir=tmp_path,
    )

    assert result["success"] is True
    assert result["fallback_used"] is True
    assert result["fallback_reason"].startswith("Unsupported chart_type")
    assert result["chart_type"] in {"ranked_bar", "table"}
    if result["chart_type"] == "ranked_bar":
        assert Path(result["chart_path"]).exists()
    else:
        assert result["table"]["columns"] == ["category_name", "gmv"]
        assert result["table"]["rows"] == [["Cameras", 1200.0]]


def _valid_provider_spec() -> dict:
    return {
        "chart_type": "dual_axis_line",
        "title": "GMV and refund rate trend",
        "x": "date",
        "y": "gmv",
        "y_secondary": "refund_rate",
        "series": "",
        "required_columns": ["date", "gmv", "refund_rate"],
        "explanation_basis": ["supported_findings"],
    }


def test_provider_backed_visualization_planner_accepts_valid_structured_output():
    from agents.visualization_planner import plan_visualization
    from llm_ops.provider import MockLLMProvider

    execution_result = _execution_result(
        ["date", "gmv", "refund_rate"],
        [["2026-06-01", 1200.0, 0.08], ["2026-06-02", 1300.0, 0.09]],
    )

    result = plan_visualization(
        "请画 GMV 和退款率双轴趋势图",
        analysis_steps=_analysis_steps(),
        execution_result=execution_result,
        evidence_result=_evidence_result(),
        provider=MockLLMProvider(_valid_provider_spec()),
    )

    assert result["success"] is True
    assert result["source"] == "provider"
    assert result["chart_type"] == "dual_axis_line"
    assert result["provider_called"] is True
    assert result["fallback_used"] is False
    assert result["prompt_id"] == "visualization_planner"
    assert result["validation_error"] == ""
    assert result["provider_error"] == ""


def test_provider_backed_visualization_planner_rejects_sql_claims_and_action_payloads():
    from agents.visualization_planner import plan_visualization
    from llm_ops.provider import MockLLMProvider

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    invalid_payload = {
        **_valid_provider_spec(),
        "sql": "SELECT * FROM orders",
        "final_claims": ["Cameras declined because refunds increased."],
        "action_payload": {"action_type": "create_task"},
    }

    result = plan_visualization(
        "请画 GMV 图",
        analysis_steps=_analysis_steps(),
        execution_result=execution_result,
        evidence_result=_evidence_result(),
        provider=MockLLMProvider(invalid_payload),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["validation_error"]
    assert "sql" not in result
    assert "final_claims" not in result
    assert "action_payload" not in result


def test_provider_backed_visualization_planner_falls_back_on_malformed_output():
    from agents.visualization_planner import plan_visualization
    from llm_ops.provider import MockLLMProvider

    execution_result = _execution_result(["category_name", "gmv"], [["Cameras", 1200.0]])
    result = plan_visualization(
        "请画 Top category ranked bar",
        analysis_steps=_analysis_steps(),
        execution_result=execution_result,
        evidence_result=_evidence_result(),
        provider=MockLLMProvider('{"chart_type": "ranked_bar",'),
    )

    assert result["success"] is True
    assert result["source"] == "deterministic"
    assert result["chart_type"] == "ranked_bar"
    assert result["provider_called"] is True
    assert result["fallback_used"] is True
    assert result["provider_error"]


def test_chart_agent_uses_visualization_plan_and_preserves_existing_chart_state(tmp_path):
    from agents.chart_agent import run_chart_agent
    from agents.supervisor import initialize_run

    state = initialize_run("请画 GMV 和退款率双轴趋势图", run_id="run_visualization_agent_test")
    state["execution_result"] = _execution_result(
        ["date", "gmv", "refund_rate"],
        [["2026-06-01", 1200.0, 0.08], ["2026-06-02", 1300.0, 0.09]],
    )
    state["analysis_steps"] = _analysis_steps()
    state["evidence_result"] = _evidence_result()

    result = run_chart_agent(state, output_dir=tmp_path)

    assert result["visualization_plan"]["chart_type"] == "dual_axis_line"
    assert result["chart_result"]["success"] is True
    assert result["chart_result"]["chart_type"] == "dual_axis_line"
    assert Path(result["chart_path"]).exists()
    assert result["trace"][-1]["node"] == "chart_agent"
