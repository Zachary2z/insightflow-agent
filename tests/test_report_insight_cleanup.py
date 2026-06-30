from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "ecommerce.db"


def test_report_planner_provider_unavailable_does_not_select_fixed_sections():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报。",
        run_id="run_p83_report_no_provider",
        session_id="session_p83_report_no_provider",
    )

    result = run_report_planner_agent(state)

    assert result["report_plan"]["success"] is False
    assert result["report_plan"]["source"] == "provider_unavailable"
    assert result["report_plan"]["provider_called"] is False
    assert result["report_plan"]["fallback_used"] is True
    assert result["report_sections"] == []
    assert result["status"] == "report_plan_provider_unavailable"


def test_report_planner_rejects_provider_sql_without_deterministic_section_fallback():
    from agents.report_planner import run_report_planner_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "帮我生成本月经营复盘，重点看 Top 商品。",
        run_id="run_p83_report_sql_leak",
        session_id="session_p83_report_sql_leak",
    )

    result = run_report_planner_agent(
        state,
        llm_provider=MockLLMProvider(
            {
                "report_type": "monthly_business_report",
                "sections": [{"section_id": "top_products", "sql": "DELETE FROM orders"}],
                "requires_clarification": False,
                "clarification_questions": [],
            }
        ),
    )

    assert result["report_plan"]["success"] is False
    assert result["report_plan"]["source"] == "provider_unavailable"
    assert result["report_plan"]["provider_called"] is True
    assert result["report_plan"]["validation_error"]
    assert result["report_sections"] == []
    assert result["status"] == "report_plan_provider_unavailable"


def test_report_supervisor_stops_when_provider_plan_is_unavailable(tmp_path):
    from agents.report_supervisor import run_report_supervisor_agent
    from agents.supervisor import initialize_run

    state = initialize_run(
        "帮我生成一份本周电商经营分析周报。",
        run_id="run_p83_supervisor_no_provider",
        session_id="session_p83_supervisor_no_provider",
    )
    state["db_path"] = DB_PATH
    state["trace_dir"] = tmp_path / "traces"

    result = run_report_supervisor_agent(
        state,
        report_dir=tmp_path / "markdown",
        chart_dir=tmp_path / "charts",
    )

    assert result["status"] == "report_plan_provider_unavailable"
    assert result["report_sections"] == []
    assert result.get("report_sub_tasks", []) == []
    assert not result.get("weekly_report_path")


def test_insight_agent_uses_provider_business_answer_without_bypassing_evidence_boundary():
    from agents.insight_agent import run_insight_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "最近 30 天销售额最高的商品是什么？",
        run_id="run_p83_insight_provider",
        session_id="session_p83_insight_provider",
    )
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56]],
        "row_count": 1,
    }

    result = run_insight_agent(
        state,
        provider=MockLLMProvider(
            {
                "candidate_claims": [
                    "Laptop Pro 14 的 GMV 为 511248.56",
                    "库存不足是主要原因",
                ],
                "business_answer": {
                    "headline": "Laptop Pro 14 销售额排名第一",
                    "direct_answer": "Laptop Pro 14 排名第一，但原因需要证据校验。",
                    "why": "执行结果显示 Laptop Pro 14 的 GMV 为 511248.56。",
                    "evidence_bullets": ["Laptop Pro 14 的 GMV 为 511248.56。"],
                    "recommendations": [],
                    "caveats": ["库存不足仍需 Evidence Validator 校验，不能直接作为原因。"],
                    "confidence": "medium",
                },
            }
        ),
    )

    insight = result["insight"]
    assert insight["source"] == "provider"
    assert insight["provider_called"] is True
    assert insight["fallback_used"] is False
    assert insight["candidate_claims"] == ["Laptop Pro 14 的 GMV 为 511248.56", "库存不足是主要原因"]
    assert insight["final_answer"] == "Laptop Pro 14 排名第一，但原因需要证据校验。"
    assert result["business_answer"]["direct_answer"] == insight["final_answer"]
    assert result["claims_to_validate"] == insight["candidate_claims"]
    assert result["trace"][-1]["provider_called"] is True
    assert result["trace"][-1]["prompt_id"] == "insight_drafter"


def test_insight_agent_rejects_provider_final_claims_and_returns_structured_fallback():
    from agents.insight_agent import run_insight_agent
    from agents.supervisor import initialize_run
    from llm_ops.provider import MockLLMProvider

    state = initialize_run(
        "最近 30 天销售额最高的商品是什么？",
        run_id="run_p83_insight_reject",
        session_id="session_p83_insight_reject",
    )
    state["execution_result"] = {
        "success": True,
        "columns": ["product_name", "gmv"],
        "rows": [["Laptop Pro 14", 511248.56]],
        "row_count": 1,
    }

    result = run_insight_agent(
        state,
        provider=MockLLMProvider(
            {
                "candidate_claims": ["Laptop Pro 14 的 GMV 为 511248.56"],
                "business_answer": {
                    "headline": "Laptop Pro 14 GMV 最高",
                    "direct_answer": "Laptop Pro 14 GMV 最高。",
                    "why": "执行结果显示 Laptop Pro 14 的 GMV 为 511248.56。",
                    "evidence_bullets": ["Laptop Pro 14 的 GMV 为 511248.56。"],
                    "recommendations": [],
                    "caveats": [],
                    "confidence": "high",
                },
                "final_claims": ["Laptop Pro 14 一定会继续增长"],
            }
        ),
    )

    insight = result["insight"]
    assert insight["source"] == "provider_unavailable"
    assert insight["provider_called"] is True
    assert insight["fallback_used"] is True
    assert insight["validation_error"]
    assert insight["candidate_claims"] == ["product_name=Laptop Pro 14, gmv=511248.56"]
    assert result["claims_to_validate"] == insight["candidate_claims"]


def test_workflow_wires_provider_backed_insight_drafting(tmp_path):
    from graph.workflow import run_workflow
    from llm_ops.provider import MockLLMProvider

    result = run_workflow(
        "最近 30 天销售额最高的商品是什么？",
        db_path=DB_PATH,
        trace_dir=tmp_path,
        run_id="run_p83_workflow_insight",
        session_id="session_p83_workflow_insight",
        insight_drafting_provider=MockLLMProvider(
            {
                "candidate_claims": ["Laptop Pro 14 的 GMV 为 511248.56"],
                "business_answer": {
                    "headline": "Laptop Pro 14 销售额最高",
                    "direct_answer": "Laptop Pro 14 是最近 30 天销售额最高的商品，建议优先复盘其流量来源和转化路径。",
                    "why": "执行结果显示 Laptop Pro 14 的 GMV 为 511248.56。",
                    "evidence_bullets": ["Laptop Pro 14 的 GMV 为 511248.56。"],
                    "recommendations": ["复盘 Laptop Pro 14 的流量来源和转化路径。"],
                    "caveats": [],
                    "confidence": "high",
                },
            }
        ),
    )

    assert result["status"] == "completed"
    assert result["insight"]["source"] == "provider"
    assert result["insight"]["provider_called"] is True
    assert result["claims_to_validate"] == ["Laptop Pro 14 的 GMV 为 511248.56"]
    insight_events = [event for event in result["trace"] if event.get("node") == "insight_agent"]
    assert insight_events[-1]["provider_called"] is True
    assert insight_events[-1]["prompt_id"] == "insight_drafter"
