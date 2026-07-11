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
    assert set(compose["volumes"]) == {"workspace-data", "report-data", "trace-data"}


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


def test_p38_is_not_implemented_early_and_ci_stays_secretless():
    compose = yaml.safe_load(_read("compose.yaml"))
    assert not ({"prometheus", "grafana"} & set(compose["services"]))
    ci = _read(".github/workflows/ci.yml").lower()
    assert "docker push" not in ci and "deploy" not in ci
    assert "deepseek_api_key" not in ci and "lark_cli" not in ci
    status = _read("DEVELOPMENT_STATUS.md")
    assert "P38 | `[ ]` Planned" in status


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
