from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ACTION_AGENT_MODULES = {
    "agents.action_planner",
    "agents.action_drafter",
    "agents.risk_assessor",
    "agents.action_executor",
    "agents.action_verifier",
}

ACTION_TOOL_MODULES = {
    "action_delivery",
    "tools.action_tool",
    "tools.approval_tool",
    "tools.audit_logger",
    "mcp_servers.action_server",
}

LEGACY_PRODUCT_TERMS = {
    "chart_agent",
    "visualization_planner",
    "chart_tool",
}


def _python_imports(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _git_tracked_files() -> set[str]:
    return set(
        subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    )


def test_action_workflow_files_are_removed_from_product_codebase():
    removed_paths = [
        "agents/action_planner.py",
        "agents/action_drafter.py",
        "agents/risk_assessor.py",
        "agents/action_executor.py",
        "agents/action_verifier.py",
        "action_delivery",
        "tools/action_tool.py",
        "tools/approval_tool.py",
        "tools/audit_logger.py",
        "mcp_servers/action_server.py",
    ]

    existing = [path for path in removed_paths if (ROOT / path).exists()]

    assert existing == []


def test_runtime_provider_no_longer_exposes_action_drafter_provider():
    import llm_ops.runtime_provider as runtime_provider

    assert not hasattr(runtime_provider, "provider_action_drafter_enabled")
    assert not hasattr(runtime_provider, "build_action_drafter_provider")


def test_prompt_registry_no_longer_contains_action_drafter():
    from llm_ops.prompt_registry import DEFAULT_PROMPT_REGISTRY

    assert DEFAULT_PROMPT_REGISTRY.get("action_drafter") is None
    assert "action_drafter" not in DEFAULT_PROMPT_REGISTRY.list_prompts()


def test_current_graph_does_not_import_or_route_to_action_agents():
    graph_imports = _python_imports("graph/workflow.py") | _python_imports("graph/nodes.py")

    assert graph_imports.isdisjoint(ACTION_AGENT_MODULES)

    graph_source = _source("graph/workflow.py") + "\n" + _source("graph/nodes.py")
    for legacy_name in (
        "action_planner",
        "action_drafter",
        "risk_assessor",
        "action_executor",
        "action_verifier",
    ):
        assert legacy_name not in graph_source
    for required_node in (
        "question_understanding",
        "clarification",
        "sql_planning",
        "analysis_planner",
        "schema",
        "metric",
        "guarded_candidate",
        "review",
        "schema_repair",
        "execute",
        "insight",
        "claim_typing",
        "visualization_agent",
        "save_trace",
    ):
        assert required_node in graph_source


def test_workspace_api_analysis_and_report_entrypoints_exclude_action_workflow_tools():
    product_entry_imports = set()
    for path in (
        "api/app.py",
        "workspaces/analysis_runner.py",
        "workspaces/report_runner.py",
        "workspaces/product_result_builder.py",
    ):
        product_entry_imports.update(_python_imports(path))

    assert product_entry_imports.isdisjoint(ACTION_AGENT_MODULES | ACTION_TOOL_MODULES)

    entry_source = "\n".join(
        _source(path)
        for path in (
            "api/app.py",
            "workspaces/analysis_runner.py",
            "workspaces/report_runner.py",
            "workspaces/product_result_builder.py",
        )
    )
    for forbidden in (
        "action_delivery",
        "action_tool",
        "approval_tool",
        "audit_logger",
        "action_server",
        "run_action_planner",
    ):
        assert forbidden not in entry_source


def test_frontend_product_api_and_renderers_exclude_action_and_eval_paths():
    frontend_source = "\n".join(
        _source(path)
            for path in (
                "frontend/lib/api.ts",
                "frontend/components/RunResult.tsx",
                "frontend/components/ReportViewer.tsx",
                "frontend/components/ReportTechnicalAppendix.tsx",
            )
        )

    for forbidden in (
        "action workflow",
        "action_planner",
        "action_drafter",
        "risk_assessor",
        "action_executor",
        "action_verifier",
        "action_delivery",
        "approval_tool",
        "audit_logger",
        "jira_ticket_mock",
        "eval/run_eval.py",
    ):
        assert forbidden not in frontend_source

    assert "/api/workspaces/${workspaceId}/runs" in frontend_source
    assert "/api/workspaces/${workspaceId}/reports" in frontend_source
    assert "business_answer" in frontend_source


def test_legacy_chart_agent_planner_and_chart_tool_are_not_product_paths():
    assert not (ROOT / "agents" / "chart_agent.py").exists()
    assert not (ROOT / "agents" / "visualization_planner.py").exists()
    assert not (ROOT / "tools" / "chart_tool.py").exists()

    product_source = "\n".join(
        _source(path)
        for path in (
            "api/app.py",
            "graph/workflow.py",
            "graph/nodes.py",
            "workspaces/analysis_runner.py",
            "workspaces/report_runner.py",
            "frontend/lib/api.ts",
        )
    )
    assert LEGACY_PRODUCT_TERMS.isdisjoint(set(product_source.split()))
    for legacy_term in LEGACY_PRODUCT_TERMS:
        assert legacy_term not in product_source


def test_mcp_database_and_report_wrappers_do_not_expose_internal_or_action_tools():
    from mcp_servers.database_server import get_tool_contract as get_database_contract
    from mcp_servers.report_server import get_tool_contract as get_report_contract

    contracts = [get_database_contract(), get_report_contract()]
    serialized = json.dumps(contracts, ensure_ascii=False)

    assert {contract["server_name"] for contract in contracts} == {
        "database-mcp-server",
        "report-mcp-server",
    }
    assert "validate_sql" not in serialized
    assert "approval_tool" not in serialized
    assert "audit_logger" not in serialized
    assert "action_tool" not in serialized
    assert "action-mcp-server" not in serialized
    assert "chart_tool" not in serialized
    for contract in contracts:
        assert contract["internal_tools_exposed"] is False


def test_mock_saas_visualization_delivery_is_not_a_runtime_tool_option():
    from tools.external_visualization_tool import call_external_visualization_tool
    from visualization_delivery.adapters import execute_delivery_tool
    from visualization_delivery.tool_catalog import DELIVERY_TOOL_CATALOG

    assert set(DELIVERY_TOOL_CATALOG) == {"local_renderer", "excel_exporter"}
    assert "powerbi_publisher_mock" not in DELIVERY_TOOL_CATALOG
    assert all(not tool.is_mock for tool in DELIVERY_TOOL_CATALOG.values())

    execution_result = {
        "success": True,
        "columns": ["category_name", "gmv"],
        "rows": [["Cameras", 1200.0]],
    }
    rejected = call_external_visualization_tool(
        delivery_tool_id="powerbi_publisher_mock",
        chart_spec={},
        execution_result=execution_result,
        run_id="run_mock_saas_rejected",
    )
    assert rejected["success"] is False
    assert rejected["external_tool_called"] is False

    adapter_rejected = execute_delivery_tool(
        delivery_tool_id="powerbi_publisher_mock",
        chart_spec={},
        execution_result=execution_result,
        run_id="run_mock_saas_adapter_rejected",
    )
    assert adapter_rejected["success"] is False
    assert adapter_rejected["external_tool_called"] is False

    p17_plan = _source("docs/product/plans/2026-06-30-p17-product-codebase-cleanup.md")
    assert "P17-H1 Inventory Result" in p17_plan
    assert "powerbi_publisher_mock" in p17_plan
    assert "P17-H3" in p17_plan
    assert "mock SaaS" in p17_plan


def test_obsolete_eval_demo_and_streamlit_files_are_deleted_and_untracked():
    removed_paths = {
        "app.py",
        "ui",
        "api/run_manager.py",
        "eval/run_eval.py",
        "eval/test_questions.json",
        "tests/test_eval_runner.py",
        "tests/test_streamlit_app.py",
    }
    tracked_files = _git_tracked_files()

    assert tracked_files.isdisjoint(removed_paths)
    assert not any(path.startswith("ui/") for path in tracked_files)
    for path in removed_paths:
        assert not (ROOT / path).exists()


def test_current_readme_entrypoints_do_not_reference_old_eval_or_streamlit_paths():
    readme = _source("README.md")
    current_sections = readme[
        readme.index("## Quickstart") : readme.index("## Historical / Superseded Context")
    ]

    for forbidden in (
        "streamlit run app.py",
        "eval/run_eval.py",
        "tests/test_eval_runner.py",
        "tests/test_streamlit_app.py",
    ):
        assert forbidden not in current_sections

    assert "uvicorn api.app:app --reload" in current_sections
    assert "npm run dev" in current_sections
    assert "/api/workspaces/{workspace_id}/runs" in current_sections
    assert "/api/workspaces/{workspace_id}/reports" in current_sections


def test_current_product_docs_do_not_present_superseded_paths_as_current_guidance():
    current_docs = {
        "README.md": _source("README.md").split("## Historical / Superseded Context")[0],
        "DEVELOPMENT_PLAN.md": _source("DEVELOPMENT_PLAN.md").split(
            "## Historical / Superseded Context"
        )[0],
        "DEVELOPMENT_STATUS.md": _source("DEVELOPMENT_STATUS.md").split(
            "## Historical / Superseded Notes"
        )[0],
    }

    forbidden_current_guidance = (
        "streamlit run app.py",
        "eval/run_eval.py",
        "tests/test_eval_runner.py",
        "tests/test_streamlit_app.py",
        "mock SaaS",
        "action workflow",
        "fixed template",
        "deterministic action template",
        "keyword inference",
    )

    for path, current_text in current_docs.items():
        for forbidden in forbidden_current_guidance:
            assert forbidden not in current_text, f"{forbidden!r} is current guidance in {path}"


def test_superseded_superpowers_specs_are_marked_historical_not_current_guidance():
    spec_paths = (
        "docs/superpowers/specs/2026-06-22-p11-general-data-analysis-product-design.md",
        "docs/superpowers/specs/2026-06-23-p12-workspace-report-productization-design.md",
        "docs/superpowers/specs/2026-06-24-p13-business-answer-product-ux-design.md",
    )

    for path in spec_paths:
        spec = _source(path)
        assert spec.startswith("# Historical / Superseded:"), path
        assert "Current implementation guidance lives in docs/product/plans/" in spec
        assert "P16 business_answer contract" in spec
        assert "P17 cleanup" in spec
