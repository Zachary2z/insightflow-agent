import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_mcp_servers_expose_json_compatible_tool_contracts():
    from mcp_servers.database_server import get_tool_contract as get_database_contract
    from mcp_servers.report_server import get_tool_contract as get_report_contract

    contracts = [get_database_contract(), get_report_contract()]
    by_server = {contract["server_name"]: contract for contract in contracts}

    assert set(by_server) == {
        "database-mcp-server",
        "report-mcp-server",
    }
    assert {tool["name"] for tool in by_server["database-mcp-server"]["tools"]} == {
        "get_database_schema",
        "get_sample_rows",
        "run_sql",
    }
    assert {tool["name"] for tool in by_server["report-mcp-server"]["tools"]} == {
        "generate_chart",
        "save_report",
    }

    serialized = json.dumps(contracts, ensure_ascii=False)
    assert "validate_sql" not in serialized
    assert "approval_tool" not in serialized
    assert "audit_logger" not in serialized
    assert "trace_logger" not in serialized
    assert "permission_checker" not in serialized
    assert "log_trace" not in serialized
    assert "eval_runner" not in serialized
    assert "chart_tool" not in serialized
    assert "action-mcp-server" not in serialized

    for contract in contracts:
        assert contract["contract_scope"] == "external_safe_tool_contract"
        assert contract["internal_tools_exposed"] is False


def test_database_mcp_layer_wraps_schema_sample_and_validated_sql_execution():
    from mcp_servers.database_server import (
        mcp_get_database_schema,
        mcp_get_sample_rows,
        mcp_run_sql,
    )

    schema_result = mcp_get_database_schema(db_path=DB_PATH)
    sample_result = mcp_get_sample_rows(db_path=DB_PATH, table_name="orders", limit=2)
    execution_result = mcp_run_sql(
        db_path=DB_PATH,
        sql="SELECT COUNT(*) AS order_count FROM orders",
    )

    assert schema_result["success"] is True
    assert schema_result["mcp_server"] == "database-mcp-server"
    assert schema_result["tool_name"] == "get_database_schema"
    assert schema_result["result"]["table_count"] >= 4

    assert sample_result["success"] is True
    assert sample_result["tool_name"] == "get_sample_rows"
    assert sample_result["result"]["columns"]
    assert len(sample_result["result"]["rows"]) == 2

    assert execution_result["success"] is True
    assert execution_result["tool_name"] == "run_sql"
    assert execution_result["review_result"]["approved"] is True
    assert "LIMIT" in execution_result["review_result"]["normalized_sql"]
    assert execution_result["result"]["success"] is True
    assert execution_result["result"]["rows"][0][0] > 0


def test_database_mcp_run_sql_rejects_sql_that_fails_validator_before_execution():
    from mcp_servers.database_server import mcp_run_sql

    result = mcp_run_sql(
        db_path=DB_PATH,
        sql="SELECT email FROM users LIMIT 5",
    )

    assert result["success"] is False
    assert result["tool_name"] == "run_sql"
    assert result["review_result"]["approved"] is False
    assert "Sensitive field access is not allowed" in result["error"]
    assert result["result"] == {}


def test_report_mcp_layer_generates_chart_and_requires_evidence_for_report_save(tmp_path):
    from mcp_servers.report_server import mcp_generate_chart, mcp_save_report

    assert not (ROOT / "tools" / "chart_tool.py").exists()

    chart_result = mcp_generate_chart(
        data={"columns": ["product_name", "gmv"], "rows": [["Laptop", 1200.0], ["Camera", 800.0]]},
        chart_spec={
            "chart_type": "ranked_bar",
            "x": "product_name",
            "y": "gmv",
            "title": "Top products",
            "run_id": "run_mcp_report",
        },
        output_dir=tmp_path / "charts",
    )
    blocked_report = mcp_save_report(
        run_id="run_no_evidence",
        report_content="# Report\n\nUnsupported final claim.",
        evidence_result={"success": False},
        output_dir=tmp_path / "reports",
    )
    saved_report = mcp_save_report(
        run_id="run_with_evidence",
        report_content="# Report\n\nLaptop GMV is 1200.0.",
        evidence_result={
            "success": True,
            "data_supported_findings": [{"claim": "Laptop GMV is 1200.0."}],
            "unsupported_claims_blocked": [],
        },
        output_dir=tmp_path / "reports",
    )

    assert chart_result["success"] is True
    assert Path(chart_result["result"]["chart_path"]).exists()
    assert chart_result["result"]["delivery_tool_id"] == "local_renderer"
    assert chart_result["result"]["external_tool_called"] is True
    assert chart_result["result"]["trace_event"]["tool_name"] == "external_visualization_tool"
    assert chart_result["mcp_server"] == "report-mcp-server"

    assert blocked_report["success"] is False
    assert "Evidence validation is required" in blocked_report["error"]
    assert not (tmp_path / "reports" / "run_no_evidence_report.md").exists()

    assert saved_report["success"] is True
    assert Path(saved_report["result"]["report_path"]).exists()
