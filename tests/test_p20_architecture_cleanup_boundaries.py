from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


MAIN_PATH_FILES = (
    "api/app.py",
    "workspaces/analysis_runner.py",
    "workspaces/report_runner.py",
    "workspaces/product_result_builder.py",
    "agents/final_answer_composer.py",
    "agents/answer_reviewer.py",
    "tools/evidence_tool.py",
    "agents/schema_repair.py",
    "graph/workflow.py",
    "graph/nodes.py",
)

LEGACY_IMPORT_PREFIXES = (
    "sql_planning.feedback",
    "agents.chart_agent",
    "agents.visualization_planner",
    "tools.chart_tool",
    "action_delivery",
    "tools.approval_tool",
    "tools.audit_logger",
)


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _python_imports(path: str) -> set[str]:
    tree = ast.parse(_source(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_p20_main_product_chain_keeps_current_agent_tool_boundaries():
    graph_source = _source("graph/workflow.py") + "\n" + _source("graph/nodes.py")

    ordered_nodes = [
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
    ]
    for node in ordered_nodes:
        assert node in graph_source

    main_source = "\n".join(_source(path) for path in MAIN_PATH_FILES)
    required_boundaries = (
        "run_question_understanding_agent",
        "run_sql_planning_router_agent",
        "run_sql_reviewer",
        "run_schema_repair_agent",
        "run_sql",
        "validate_evidence",
        "review_answer",
        "compose_final_answer",
        "run_workspace_report",
        "save_trace",
    )
    for boundary in required_boundaries:
        assert boundary in main_source


def test_p20_active_main_path_does_not_import_legacy_or_template_mining_paths():
    imports: set[str] = set()
    for path in MAIN_PATH_FILES:
        imports.update(_python_imports(path))

    for legacy_prefix in LEGACY_IMPORT_PREFIXES:
        assert all(
            imported != legacy_prefix and not imported.startswith(f"{legacy_prefix}.")
            for imported in imports
        )


def test_p20_guarded_sql_candidate_trace_has_no_template_mining_eval_payload():
    from agents.guarded_llm_enhancer import run_guarded_sql_candidate_agent
    from llm_ops.provider import MockLLMProvider

    state = {
        "run_id": "run_p20_trace_boundary",
        "session_id": "session_p20_trace_boundary",
        "user_question": "按渠道汇总收入",
        "sql_routing_strategy": "llm_candidate",
        "sql_planning": {
            "intent": {"metric": "revenue", "dimension": "channel", "operation": "summary"},
        },
        "database_schema": {
            "tables": [
                {
                    "table_name": "orders",
                    "columns": [
                        {"name": "channel", "type": "TEXT"},
                        {"name": "revenue", "type": "REAL"},
                    ],
                    "foreign_keys": [],
                }
            ]
        },
        "metric_context": {},
        "trace": [],
    }

    result = run_guarded_sql_candidate_agent(
        state,
        llm_provider=MockLLMProvider(
            {
                "sql_candidates": [
                    {
                        "sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
                        "rationale": "Use current workspace table.",
                    }
                ]
            }
        ),
    )

    serialized_trace = json.dumps(result["trace"], ensure_ascii=False)
    assert "template_mining_event" not in serialized_trace
    assert result["llm_sql_enhancement"]["accepted"] is True
