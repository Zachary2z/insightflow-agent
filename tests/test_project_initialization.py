from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_p11_scaffold_files_exist():
    expected_files = [
        "README.md",
        "requirements.txt",
        ".env.example",
        "api/app.py",
        "frontend/package.json",
    ]

    missing = [path for path in expected_files if not (ROOT / path).is_file()]

    assert missing == []


def test_p11_scaffold_directories_exist():
    expected_dirs = [
        "agents",
        "tools",
        "graph",
        "tests",
        "data",
        "frontend/app",
        "frontend/components",
        "logs/traces",
        "reports/charts",
        "reports/markdown",
    ]

    missing = [path for path in expected_dirs if not (ROOT / path).is_dir()]

    assert missing == []


def test_fastapi_product_entrypoint_is_importable():
    from api.app import create_app

    app = create_app()

    assert app.title == "InsightFlow Agent API"


def test_legacy_streamlit_ui_is_not_part_of_product_scaffold():
    assert not (ROOT / "app.py").exists()
    assert not (ROOT / "ui").exists()


def test_legacy_report_agents_are_not_part_of_current_report_center():
    removed_paths = [
        "agents/report_supervisor.py",
        "agents/report_agent.py",
        "agents/report_writer.py",
    ]

    assert [path for path in removed_paths if (ROOT / path).exists()] == []


def test_fastapi_product_entrypoint_excludes_legacy_runs_api():
    from api.app import create_app

    app = create_app()

    assert all(not route.path.startswith("/api/runs") for route in app.routes)
