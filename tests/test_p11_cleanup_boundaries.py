from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_p11_product_entry_is_not_streamlit():
    assert not (ROOT / "app.py").exists()
    assert (ROOT / "frontend" / "package.json").exists()
    assert (ROOT / "api" / "app.py").exists()


def test_p11_old_eval_seed_and_mock_action_acceptance_are_removed():
    removed_paths = [
        ROOT / "eval" / "run_eval.py",
        ROOT / "eval" / "test_questions.json",
        ROOT / "tests" / "test_action_agent_tool_adapter_cleanup.py",
        ROOT / "tests" / "test_action_workflow.py",
        ROOT / "tests" / "test_deepseek_action_drafter_live.py",
        ROOT / "tests" / "test_eval_runner.py",
        ROOT / "tests" / "test_provider_backed_action_drafter.py",
        ROOT / "tests" / "test_realistic_seed_data.py",
        ROOT / "tests" / "test_seed_data.py",
        ROOT / "tests" / "test_streamlit_app.py",
    ]
    assert all(not path.exists() for path in removed_paths)
