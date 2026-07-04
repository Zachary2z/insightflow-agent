from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _git_tracked_files() -> set[str]:
    return set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())


def test_generated_runtime_artifacts_are_not_tracked():
    tracked = _git_tracked_files()
    forbidden_exact = {
        "data/ecommerce.db",
        "data/action_ops.db",
        "eval/report.md",
    }
    forbidden_prefixes = (
        "reports/charts/run_",
        "reports/markdown/report_",
        "logs/traces/run_",
        ".superpowers/",
        "docs/superpowers/plans/",
    )

    assert tracked.isdisjoint(forbidden_exact)
    assert not any(path.startswith(forbidden_prefixes) for path in tracked)
    assert not any(
        path.startswith("workspaces/")
        and not path.endswith(".py")
        and "/" in path.removeprefix("workspaces/")
        for path in tracked
    )


def test_historical_development_records_are_retained_but_marked_as_history():
    historical_docs = [
        ROOT / "docs/product/plans/2026-06-30-p17-product-codebase-cleanup.md",
        ROOT / "docs/product/plans/2026-07-04-p25-real-usage-answer-report-polish.md",
        ROOT / "docs/superpowers/specs/2026-06-22-p11-general-data-analysis-product-design.md",
    ]

    missing = [path for path in historical_docs if not path.exists()]
    assert missing == []
    assert (ROOT / "docs/superpowers/specs/2026-06-22-p11-general-data-analysis-product-design.md").read_text(
        encoding="utf-8"
    ).startswith("# Historical / Superseded:")


def test_current_docs_name_fastapi_nextjs_as_current_product_path():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    current = readme.split("## Historical / Superseded Context", 1)[0]

    assert "FastAPI" in current
    assert "Next.js" in current
    assert "data/ecommerce.db remains tracked" not in readme
    assert "streamlit run app.py" not in current
    assert "eval/run_eval.py" not in current
