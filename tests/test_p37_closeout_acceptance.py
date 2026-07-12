from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _tracked_files() -> set[str]:
    return set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())


def test_final_p37_images_and_h1_h4_contracts_remain_present():
    compose = yaml.safe_load(_read("compose.yaml"))
    assert compose["services"]["backend"]["image"] == "insightflow-backend:p37"
    assert compose["services"]["frontend"]["image"] == "insightflow-frontend:p37"
    assert "AS builder" in _read("Dockerfile") and "USER insightflow:insightflow" in _read("Dockerfile")
    assert "AS builder" in _read("frontend/Dockerfile") and "USER nextjs:nodejs" in _read("frontend/Dockerfile")
    assert "/health/live" in _read("api/app.py") and "/health/ready" in _read("api/app.py")
    assert {"workspace-data", "report-data", "trace-data"}.issubset(compose["volumes"])


def test_make_smoke_and_ci_share_one_stable_acceptance_entry():
    makefile = _read("Makefile")
    smoke = _read("scripts/docker_smoke_test.sh")
    ci = _read(".github/workflows/ci.yml")
    assert "bash scripts/docker_smoke_test.sh" in makefile
    assert "scripts/docker_smoke_test.sh" in ci
    for required in (
        "/semantic-layer/draft",
        "/runs",
        "/reports",
        "/download",
        "/export",
        "docker compose",
        "compose down",
    ):
        assert required in smoke
    assert "--no-cache" not in smoke
    assert "down -v --remove-orphans" in smoke


def test_readme_and_deployment_document_no_key_live_and_volume_boundaries():
    readme = _read("README.md")
    deployment = _read("docs/deployment.md")
    assert "docs/deployment.md" in readme
    assert "insightflow-backend:p37" in readme
    assert "insightflow-frontend:p37" in readme
    for volume in ("workspace-data", "report-data", "trace-data"):
        assert volume in readme and volume in deployment
    assert "--env-file /dev/null" in readme and "无密钥" in deployment
    assert "INSIGHTFLOW_PRODUCT_LIVE_MODE=1" in deployment
    assert "INSIGHTFLOW_LIVE_DEEPSEEK_TESTS=1" in deployment
    assert "down -v" in deployment and "永久删除" in deployment
    assert "正式 Secret Manager" in deployment


def test_p38_h1_through_h6_are_complete_and_keep_external_boundaries():
    compose = yaml.safe_load(_read("compose.yaml"))
    assert {"prometheus", "grafana"}.issubset(compose["services"])
    ci = _read(".github/workflows/ci.yml").lower()
    assert "docker push" not in ci and "deploy" not in ci
    assert "deepseek_api_key" not in ci and "lark_cli" not in ci
    status = _read("DEVELOPMENT_STATUS.md")
    assert "P38 | `[x]` Complete" in status
    assert "P38-H1 | `[x]` Complete" in status
    assert "P38-H2 | `[x]` Complete" in status
    assert "P38-H3 | `[x]` Complete" in status
    assert "P38-H4 | `[x]` Complete" in status
    assert "P38-H5 | `[x]` Complete" in status
    assert "P38-H6 | `[x]` Complete" in status
    assert Path(ROOT / "observability" / "metrics.py").is_file()
    assert Path(ROOT / "observability" / "tests" / "rule-tests.yml").is_file()
    assert Path(ROOT / "docs" / "operations" / "observability-alerts.md").is_file()
    assert '@app.get("/metrics"' in _read("api/app.py")


def test_p38_h6_closeout_status_is_consistent_across_project_documents():
    plan = _read("DEVELOPMENT_PLAN.md")
    status = _read("DEVELOPMENT_STATUS.md")
    product_plan = _read("docs/product/plans/2026-07-11-p38-observability-and-operations.md")
    readme = _read("README.md")

    plan_tasks = plan.split("## P38 Task Status", 1)[1].split("## Latest P38-H6 Result", 1)[0]
    status_tasks = status.split("## P38 Task Status", 1)[1].split("### P38-H6 Verification", 1)[0]
    product_h4 = product_plan.split("### P38-H4: Prometheus Metrics", 1)[1].split("### P38-H5:", 1)[0]
    product_h5 = product_plan.split("### P38-H5: Prometheus, Grafana, Dashboards, And Alerts", 1)[1].split("### P38-H6:", 1)[0]
    product_h6 = product_plan.split("### P38-H6: Failure Injection, Runbooks, Acceptance, And Closeout", 1)[1]

    assert "Complete; H1-H6 complete" in plan
    assert "| P38-H4 | `[x]` Complete |" in plan_tasks
    assert "| P38-H5 | `[x]` Complete |" in plan_tasks
    assert "| P38-H6 | `[x]` Complete |" in plan_tasks
    assert "P38-H4 | `[ ]` Planned" not in plan_tasks
    assert "No next phase is designated" in plan

    assert "| P38 | `[x]` Complete |" in status
    assert "| P38-H4 | `[x]` Complete |" in status_tasks
    assert "| P38-H5 | `[x]` Complete |" in status_tasks
    assert "| P38-H6 | `[x]` Complete |" in status_tasks
    assert "P38-H4 | `[ ]` Planned" not in status_tasks
    assert "| Next planned task | Not designated; create a separate phase plan before expanding scope |" in status

    assert "Status: Complete; H1-H6 complete" in product_plan
    assert "Next planned task: not designated" in product_plan
    assert "Status: Complete" in product_h4
    assert "Status: Complete" in product_h5
    assert "Status: Complete" in product_h6

    assert "P38 observability and operations 已完成 H1-H6" in readme
    assert "下一阶段尚未指定" in readme
    assert "H6 尚未实施" not in readme

    compose = yaml.safe_load(_read("compose.yaml"))
    assert set(compose["services"]) == {"backend", "frontend", "prometheus", "grafana"}


def test_current_product_boundaries_were_not_rewritten_by_containerization():
    result_builder = _read("workspaces/product_result_builder.py")
    business_answer = _read("workspaces/business_answer_agent.py")
    report_runner = "\n".join(
        _read(path)
        for path in (
            "workspaces/report_runner.py",
            "workspaces/report_models.py",
            "workspaces/report_planner.py",
        )
    )
    assert "only assembles" in result_builder
    assert "question_evidence_ledger" in business_answer
    for contract in ("ReportPlan", "ReportEvidencePack", "EvidenceLedger", "ReportDocument"):
        assert contract in report_runner
    active = "\n".join(
        _read(path)
        for path in ("api/app.py", "workspaces/report_runner.py", "workspaces/product_result_builder.py")
    )
    assert "powerbi_publisher_mock" not in active
    assert "jira_ticket_mock" not in active


def test_generated_artifacts_secrets_and_local_paths_are_not_tracked_or_documented():
    tracked = _tracked_files()
    forbidden_exact = {".env", "data/ecommerce.db", "data/action_ops.db", "eval/report.md"}
    assert tracked.isdisjoint(forbidden_exact)
    forbidden = re.compile(
        r"(?:^|/)(?:node_modules|\.next|__pycache__|\.pytest_cache)(?:/|$)|"
        r"\.(?:db|sqlite|sqlite3|docx|pyc)$|"
        r"^logs/traces/.+\.json$|^reports/(?:charts|markdown)/[^.].+|"
        r"^workspaces/[^/]+/(?:runs|reports)/"
    )
    assert not [path for path in tracked if forbidden.search(path)]
    checked = "\n".join(
        _read(path)
        for path in (
            "Dockerfile",
            "frontend/Dockerfile",
            "compose.yaml",
            ".github/workflows/ci.yml",
            "README.md",
            "DEVELOPMENT_PLAN.md",
            "DEVELOPMENT_STATUS.md",
            "docs/deployment.md",
        )
    )
    assert not re.search(r"/Users/[^\s`]+", checked)
    assert not re.search(r"(?i)(?:sk|key|token)-[a-z0-9_-]{20,}", checked)
