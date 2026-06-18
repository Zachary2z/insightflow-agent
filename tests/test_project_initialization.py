from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_p0_scaffold_files_exist():
    expected_files = [
        "README.md",
        "requirements.txt",
        ".env.example",
        "app.py",
    ]

    missing = [path for path in expected_files if not (ROOT / path).is_file()]

    assert missing == []


def test_p0_scaffold_directories_exist():
    expected_dirs = [
        "agents",
        "tools",
        "graph",
        "eval",
        "tests",
        "data",
        "logs/traces",
        "reports/charts",
        "reports/markdown",
    ]

    missing = [path for path in expected_dirs if not (ROOT / path).is_dir()]

    assert missing == []


def test_streamlit_app_entrypoint_is_importable():
    import app

    assert app.APP_TITLE == "InsightFlow Agent"
    assert callable(app.main)
