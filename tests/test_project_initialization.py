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
