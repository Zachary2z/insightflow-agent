from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_report_planner_uses_mock_llm_plan_without_accepting_sql():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run

    captured = {}

    def mock_llm_provider(prompt):
        captured["prompt"] = prompt
        return {
            "report_type": "weekly_business_report",
            "sections": [
                {
                    "section_id": "top_products",
                    "title": "LLM suggested title",
                    "rationale": "Need product ranking.",
                    "sql": "DELETE FROM orders",
                },
                {"section_id": "weekly_gmv", "rationale": "Need core metric."},
                {"section_id": "unknown_llm_section", "rationale": "Should be ignored."},
            ],
        }

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报，重点关注 Top 商品和 GMV。",
        run_id="run_planner_test",
        session_id="session_planner_test",
    )

    result = run_report_planner_agent(state, llm_provider=mock_llm_provider)

    assert result["report_plan"]["success"] is True
    assert result["report_plan"]["fallback_used"] is False
    assert result["report_plan"]["provider_called"] is True
    assert "allowed_section_ids" in captured["prompt"]
    assert "must_not_generate_sql" in captured["prompt"]
    assert [section["section_id"] for section in result["report_sections"]] == ["top_products", "weekly_gmv"]
    assert result["report_sections"][0]["title"] == "Top 商品"
    assert result["report_sections"][0]["sql"].strip().lower().startswith("select")
    assert "DELETE" not in result["report_sections"][0]["sql"].upper()
    assert result["trace"][-1]["node"] == "report_planner_agent"


def test_report_planner_falls_back_when_provider_missing_or_malformed():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报。",
        run_id="run_planner_fallback_test",
        session_id="session_planner_fallback_test",
    )

    no_provider_result = run_report_planner_agent(state)
    assert no_provider_result["report_plan"]["success"] is True
    assert no_provider_result["report_plan"]["fallback_used"] is True
    assert no_provider_result["report_plan"]["provider_called"] is False
    assert len(no_provider_result["report_sections"]) >= 7

    malformed_result = run_report_planner_agent(
        state,
        llm_provider=lambda prompt: {"sections": [{"section_id": "not_allowed"}]},
    )
    assert malformed_result["report_plan"]["success"] is False
    assert malformed_result["report_plan"]["fallback_used"] is True
    assert "no allowed sections" in malformed_result["report_plan"]["error"]
    assert len(malformed_result["report_sections"]) >= 7


def test_report_planner_supports_clarification_questions():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成经营复盘。",
        run_id="run_planner_clarify_test",
        session_id="session_planner_clarify_test",
    )

    result = run_report_planner_agent(
        state,
        llm_provider=lambda prompt: {
            "requires_clarification": True,
            "clarification_questions": ["请确认复盘周期是本周还是本月？"],
        },
    )

    assert result["status"] == "report_plan_needs_clarification"
    assert result["report_plan"]["success"] is True
    assert result["report_plan"]["requires_clarification"] is True
    assert result["report_plan"]["clarification_questions"] == ["请确认复盘周期是本周还是本月？"]
    assert result["report_sections"] == []


def test_report_supervisor_can_use_controlled_llm_planner(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报，优先看 GMV 和 Top 商品。",
        run_id="run_planner_supervisor_test",
        session_id="session_planner_supervisor_test",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        llm_provider=lambda prompt: {
            "report_type": "weekly_business_report",
            "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
        },
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["report_plan"]["provider_called"] is True
    assert result["report_plan"]["fallback_used"] is False
    assert [section["section_id"] for section in result["report_sections"]] == ["weekly_gmv", "top_products"]
    assert len(result["report_sub_tasks"]) == 2
    assert result["status"] == "business_review_report_completed"
    assert Path(result["weekly_report_path"]).exists()


def test_report_planner_uses_promptops_provider_and_rejects_provider_sql():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "帮我生成本月经营复盘，重点看 Top 商品。",
        run_id="run_promptops_report_planner",
        session_id="session_promptops_report_planner",
    )

    valid = run_report_planner_agent(
        state,
        llm_provider=MockLLMProvider(
            {
                "report_type": "monthly_business_report",
                "sections": [{"section_id": "top_products", "rationale": "Need product ranking."}],
                "requires_clarification": False,
                "clarification_questions": [],
            }
        ),
    )

    assert valid["report_plan"]["success"] is True
    assert valid["report_plan"]["source"] == "provider"
    assert valid["report_plan"]["provider_called"] is True
    assert valid["report_plan"]["fallback_used"] is False
    assert valid["report_plan"]["prompt_id"] == "report_planner"
    assert [section["section_id"] for section in valid["report_sections"]] == ["top_products"]
    assert valid["report_sections"][0]["sql"].lower().startswith("select")

    leaked_sql = run_report_planner_agent(
        state,
        llm_provider=MockLLMProvider(
            {
                "sections": [
                    {
                        "section_id": "top_products",
                        "rationale": "Need product ranking.",
                        "sql": "DELETE FROM orders",
                    }
                ],
                "requires_clarification": False,
                "clarification_questions": [],
            }
        ),
    )

    assert leaked_sql["report_plan"]["source"] == "deterministic"
    assert leaked_sql["report_plan"]["provider_called"] is True
    assert leaked_sql["report_plan"]["fallback_used"] is True
    assert leaked_sql["report_plan"]["validation_error"]
    assert all(task["sql"].lower().startswith("select") for task in leaked_sql["report_sections"])


def test_report_supervisor_runtime_provider_factory_and_no_key_baseline(tmp_path, monkeypatch):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "帮我生成本月经营复盘，重点看 GMV 和 Top 商品。",
        run_id="run_runtime_report_planner",
        session_id="session_runtime_report_planner",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        llm_provider=MockLLMProvider(
            {
                "report_type": "monthly_business_report",
                "sections": [{"section_id": "weekly_gmv"}, {"section_id": "top_products"}],
                "requires_clarification": False,
                "clarification_questions": [],
            }
        ),
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["report_plan"]["provider_called"] is True
    assert result["report_plan"]["source"] == "provider"
    assert result["report_type"] == "monthly_business_report"
    assert [section["section_id"] for section in result["report_sections"]] == ["weekly_gmv", "top_products"]
    assert result["status"] == "business_review_report_completed"

    monkeypatch.setenv("INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    fallback_state = initialize_run(
        "帮我生成本月经营复盘。",
        run_id="run_no_key_review_planner",
        session_id="session_no_key_review_planner",
    )
    fallback_state["db_path"] = DB_PATH
    fallback_state["trace_dir"] = tmp_path / "fallback_traces"

    fallback = run_report_supervisor_agent(
        fallback_state,
        report_dir=tmp_path / "fallback_markdown",
        chart_dir=tmp_path / "fallback_charts",
    )

    assert fallback["report_plan"]["source"] == "deterministic"
    assert fallback["report_plan"]["provider_called"] is False
    assert fallback["status"] == "business_review_report_completed"
