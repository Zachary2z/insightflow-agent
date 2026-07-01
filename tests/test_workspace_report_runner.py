import json
import sqlite3
from pathlib import Path

import pytest
import yaml

from workspaces.report_runner import REPORT_TYPE_PRESETS, _section_question, run_workspace_report
from workspaces.store import WorkspaceStore


BUSINESS_ANSWER_KEYS = {
    "headline",
    "direct_answer",
    "why",
    "evidence_bullets",
    "recommendations",
    "caveats",
    "confidence",
}


def _business_answer(call_index: int) -> dict:
    return {
        "headline": f"第 {call_index} 个章节的业务结论",
        "direct_answer": f"第 {call_index} 个章节显示付费搜索收入领先，建议优先复盘渠道结构。",
        "why": "证据表显示 paid_search 的收入高于 organic。",
        "evidence_bullets": ["paid_search 收入为 200.0。"],
        "recommendations": ["优先复盘付费搜索的投放效率。"],
        "caveats": ["当前只基于报告章节查询返回的数据。"],
        "confidence": "high",
    }


def _create_workspace_with_orders(tmp_path):
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("Report Runner Workspace")
    with sqlite3.connect(workspace["analysis_db_path"]) as conn:
        conn.execute(
            "CREATE TABLE orders (order_date TEXT, channel TEXT, revenue REAL)"
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?)",
            [
                ("2026-01-01", "email", 100.0),
                ("2026-01-02", "paid_search", 200.0),
                ("2026-01-03", "organic", 150.0),
            ],
        )
    return store, workspace


def _fake_section_runner(calls):
    def runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        workspace = store.get_workspace(workspace_id)
        call_index = len(calls) + 1
        run_dir = Path(workspace["root_path"]) / "runs" / f"fake_run_{call_index}"
        run_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = run_dir / f"chart_{call_index}.png"
        artifact_path.write_bytes(b"fake-png")
        calls.append(
            {
                "workspace_id": workspace_id,
                "user_question": user_question,
                "initial_sql": initial_sql,
                "providers": providers,
                "artifact_path": str(artifact_path),
            }
        )
        return {
            "status": "completed",
            "final_answer": f"Section answer {call_index} with business recommendation.",
            "product_result": {
                "version": "p16.v1",
                "business_answer": _business_answer(call_index),
            },
            "generated_sql": (
                "SELECT channel, SUM(revenue) AS revenue "
                "FROM orders GROUP BY channel LIMIT 20"
            ),
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0], ["organic", 150.0]],
                "row_count": 2,
            },
            "evidence_result": {
                "data_supported_findings": [
                    {"claim": "paid_search has the highest revenue."}
                ],
                "hypotheses": [{"claim": "organic may be worth deeper review."}],
            },
            "visualization_trace": {
                "artifact_path": str(artifact_path),
                "chart_spec": {
                    "title": f"第 {call_index} 节渠道收入图",
                    "unit": "元",
                    "business_annotation": "paid_search 收入领先，支持优先复盘渠道结构。",
                },
                "provider_called": False,
            },
            "provider_metadata": {"fake": {"call_index": call_index}},
            "trace": [
                {"node": "question_understanding_agent"},
                {"node": "sql_reviewer_agent"},
                {"node": "sql_executor_node"},
                {"node": "visualization_agent"},
            ],
            "trace_path": str(run_dir / "trace.json"),
            "workspace_run_dir": str(run_dir),
        }

    return runner


def _narrative_business_answer(
    *,
    headline: str,
    direct_answer: str,
    why: str,
    evidence_bullets: list[str],
    recommendations: list[str] | None = None,
    caveats: list[str] | None = None,
    confidence: str = "high",
) -> dict:
    return {
        "headline": headline,
        "direct_answer": direct_answer,
        "why": why,
        "evidence_bullets": evidence_bullets,
        "recommendations": recommendations or [],
        "caveats": caveats or ["当前只基于报告章节查询结果。"],
        "confidence": confidence,
    }


def test_report_synthesizes_management_narrative_instead_of_section_concatenation(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    answers = [
        _narrative_business_answer(
            headline="微信私域收入规模领先",
            direct_answer="最近 90 天微信私域总收入最高，是收入规模主线。",
            why="证据显示微信私域收入为 890262.07 元，高于抖音信息流。",
            evidence_bullets=["微信私域收入为 890262.07 元。", "抖音信息流收入为 740113.50 元。"],
            recommendations=["优先复盘微信私域的可复制获客动作。"],
        ),
        _narrative_business_answer(
            headline="百度搜索订单数领先",
            direct_answer="从订单数看，百度搜索最高，说明规模和订单效率存在不同口径。",
            why="证据显示百度搜索订单数为 165，微信私域订单数为 144。",
            evidence_bullets=["百度搜索订单数为 165。", "微信私域订单数为 144。"],
            recommendations=["把百度搜索作为订单获取效率的下一步验证对象。"],
        ),
        _narrative_business_answer(
            headline="ROI 数据缺失，不能直接给投放加码结论",
            direct_answer="当前报告没有 ROI 或利润数据，预算建议应先写成下一步验证。",
            why="返回字段只有渠道、收入和订单数，没有 ROI、利润或转化率。",
            evidence_bullets=["当前证据表缺少 ROI、利润、转化率字段。"],
            recommendations=["下一步补充 ROI、利润和转化率后，再判断预算加码。"],
            caveats=["缺少 ROI、利润、转化率，不能直接推导投放收益。"],
            confidence="medium",
        ),
    ]

    def narrative_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        index = min(len(calls), len(answers) - 1)
        calls.append(user_question)
        return {
            "status": "completed",
            "product_result": {
                "version": "p16.v1",
                "business_answer": answers[index],
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue", "order_count"],
                "rows": [["微信私域", 890262.07, 144], ["百度搜索", 650220.0, 165]],
            },
            "evidence_result": {"validation_status": "validated"},
            "trace": [{"node": "final_answer_composer"}],
        }

    calls = []
    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成面向管理层的中文渠道经营复盘报告，关注收入规模、订单效率和预算决策边界。",
        section_runner=narrative_runner,
    )

    report = result["report"]
    summary_text = "\n".join(report["executive_summary"])
    findings_text = "\n".join(report["key_findings"])
    actions_text = "\n".join(report["action_priorities"])
    limits_text = "\n".join(report["risks_and_limits"])

    assert report["executive_summary"]
    assert report["executive_summary"][0] != "Overall Revenue: 微信私域收入规模领先"
    assert "管理层" in summary_text
    assert "微信私域" in summary_text
    assert "百度搜索" in findings_text
    assert any(marker in findings_text for marker in ("口径", "取舍", "不同"))
    assert "下一步补充 ROI、利润和转化率" in actions_text
    assert "ROI" in limits_text
    assert "利润" in limits_text
    assert "SELECT" not in summary_text + findings_text + actions_text + limits_text
    assert "final_answer_composer" not in summary_text + findings_text + actions_text + limits_text


def test_report_synthesis_respects_english_goal_language(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def english_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "product_result": {
                "version": "p16.v1",
                "business_answer": {
                    "headline": "Paid search leads revenue",
                    "direct_answer": "Paid search has the highest revenue in the returned data.",
                    "why": "The evidence table shows paid_search revenue is 200.0.",
                    "evidence_bullets": ["paid_search revenue is 200.0."],
                    "recommendations": ["Review paid search efficiency before increasing spend."],
                    "caveats": ["ROI and profit are not available in this report section."],
                    "confidence": "high",
                },
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0], ["organic", 150.0]],
            },
            "evidence_result": {"validation_status": "validated"},
            "trace": [{"node": "final_answer_composer"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "Create an English leadership report about revenue and channel performance.",
        section_runner=english_runner,
    )

    report_text = "\n".join(
        [
            *result["report"]["executive_summary"],
            *result["report"]["key_findings"],
            *result["report"]["action_priorities"],
            *result["report"]["risks_and_limits"],
        ]
    )
    assert "Executive summary" in report_text
    assert "Key findings" in report_text
    assert "管理层" not in report_text
    assert "关键发现" not in report_text
    assert "建议动作" not in report_text


def test_business_review_generates_multiple_sections_and_persists_report_artifacts(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "business_review",
        "生成一份经营复盘报告，关注收入、渠道、趋势和建议。",
        providers={"question_understanding": object()},
        section_runner=_fake_section_runner(calls),
    )

    report = result["report"]
    report_dir = Path(workspace["root_path"]) / "reports" / report["report_id"]
    artifact_dir = report_dir / "artifacts"

    assert result["success"] is True
    assert report["status"] == "completed"
    assert len(report["sections"]) >= 3
    assert len(calls) == len(report["sections"])
    assert all(call["providers"] for call in calls)
    assert all("SELECT" not in call["user_question"].upper() for call in calls)
    assert (report_dir / "report.json").is_file()
    assert (report_dir / "report.md").is_file()
    assert (report_dir / "trace.json").is_file()
    assert artifact_dir.is_dir()

    saved = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "report.md").read_text(encoding="utf-8")
    business_answer = saved["sections"][0]["business_answer"]
    assert set(business_answer) == BUSINESS_ANSWER_KEYS
    assert business_answer["headline"] == "第 1 个章节的业务结论"
    assert business_answer["direct_answer"] == "第 1 个章节显示付费搜索收入领先，建议优先复盘渠道结构。"
    assert business_answer["evidence_bullets"] == ["paid_search 收入为 200.0。"]
    business_answer_text = json.dumps(business_answer, ensure_ascii=False)
    assert "SELECT channel" not in business_answer_text
    assert "provider_called" not in business_answer_text
    assert "question_understanding_agent" not in business_answer_text
    assert saved["executive_summary"][0].startswith("管理层摘要：")
    assert saved["key_findings"]
    assert saved["action_priorities"]
    assert saved["risks_and_limits"]
    assert saved["chart_and_evidence"]
    assert saved["sections"][0]["columns"] == ["channel", "revenue"]
    assert saved["sections"][0]["rows_preview"][0] == {
        "channel": "paid_search",
        "revenue": 200.0,
    }
    assert saved["sections"][0]["trace_nodes"] == [
        "question_understanding_agent",
        "sql_reviewer_agent",
        "sql_executor_node",
        "visualization_agent",
    ]
    technical_details = saved["sections"][0]["technical_details"]
    assert technical_details["internal_question"].startswith("这是自动报告内部 section")
    assert technical_details["purpose"] == "Summarize recent revenue scale and channel mix using the current workspace data."
    assert technical_details["sql"].startswith("SELECT channel")
    assert technical_details["rows_preview"][0] == {
        "channel": "paid_search",
        "revenue": 200.0,
    }
    assert technical_details["provider_metadata"]["fake"]["call_index"] == 1
    assert technical_details["trace_nodes"] == [
        "question_understanding_agent",
        "sql_reviewer_agent",
        "sql_executor_node",
        "visualization_agent",
    ]
    for section in saved["sections"]:
        assert section["artifact_paths"]
        assert section["business_artifacts"][0]["title"].endswith("渠道收入图")
        assert section["business_artifacts"][0]["unit"] == "元"
        assert "paid_search 收入领先" in section["business_artifacts"][0]["business_annotation"]
        for artifact_path in section["artifact_paths"]:
            assert artifact_path.startswith("artifacts/")
            assert (report_dir / artifact_path).is_file()
            assert Path(artifact_path).is_relative_to("artifacts")
            assert "runs/fake_run" not in artifact_path
            assert f"![" in markdown
            assert artifact_path in markdown
            assert "单位：元" in markdown

    trace = json.loads((report_dir / "trace.json").read_text(encoding="utf-8"))
    assert trace["report_id"] == report["report_id"]
    assert any(event["event"] == "section_completed" for event in trace["events"])


def test_report_with_no_charts_stays_readable_without_internal_errors(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def no_chart_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "product_result": {
                "version": "p16.v1",
                "business_answer": _business_answer(1),
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0], ["organic", 150.0]],
            },
            "evidence_result": {"validation_status": "validated"},
            "visualization_trace": {
                "rendering_status": "failed",
                "error": "matplotlib backend error",
                "trace_path": "/tmp/internal-trace.json",
            },
            "trace": [{"node": "visualization_agent"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "生成中文收入趋势报告。",
        section_runner=no_chart_runner,
    )
    markdown = Path(result["report"]["markdown_path"]).read_text(encoding="utf-8")
    business_body = markdown.split("## 技术附录", 1)[0]

    assert result["report"]["chart_and_evidence"] == ["暂无可展示图表；本报告先基于各章节证据表和业务结论阅读。"]
    assert "暂无可展示图表" in business_body
    assert "matplotlib backend error" not in business_body
    assert "internal-trace" not in business_body


def test_report_section_without_current_business_answer_gets_low_confidence_failure(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def legacy_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "final_answer": "Legacy final answer should not become the report body.",
            "generated_sql": "SELECT channel, SUM(revenue) AS revenue FROM orders GROUP BY channel",
            "execution_result": {
                "success": True,
                "columns": ["channel", "revenue"],
                "rows": [["paid_search", 200.0]],
            },
            "trace": [{"node": "sql_executor_node"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "生成收入趋势报告。",
        section_runner=legacy_runner,
    )

    first_section = result["report"]["sections"][0]
    assert first_section["status"] == "failed"
    assert first_section["business_answer"] == {
        "headline": "本节缺少可展示的业务结论",
        "direct_answer": "本节分析没有返回当前 P16 business_answer 合同，因此不能把旧文本作为报告正文展示。",
        "why": "报告章节只接受 headline、direct_answer、why、evidence_bullets、recommendations、caveats 和 confidence 组成的业务答案。",
        "evidence_bullets": [],
        "recommendations": ["请重新生成本报告章节，或重新运行分析以获得当前业务答案结构。"],
        "caveats": ["旧 final_answer、SQL、trace 或 provider metadata 不会作为报告正文降级展示。"],
        "confidence": "low",
    }
    assert "summary" not in first_section
    assert "Legacy final answer should not become the report body." not in first_section["business_answer"]["direct_answer"]


def test_report_does_not_inherit_conflicting_section_answer_or_repeat_long_direct_answer(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def conflicting_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "product_result": {
                "version": "p16.v1",
                "business_answer": {
                    "headline": "高价值企业最值得重点运营",
                    "direct_answer": (
                        "高价值企业最值得重点运营，因为它的客单价最高。"
                        "但本报告章节问题只是内部 section 提示生成的自动分析，"
                        "这里的长正文不应被 executive summary 原样重复。"
                    ),
                    "why": "证据表第一行显示：segment 为 成长型团队，total_revenue 为 2798216.93，order_count 为 628。",
                    "evidence_bullets": [
                        "成长型团队收入为 2798216.93，订单量为 628。",
                        "高价值企业客单价为 6348.56。",
                    ],
                    "recommendations": ["优先把运营资源投入高价值企业。"],
                    "caveats": [],
                    "confidence": "high",
                },
            },
            "execution_result": {
                "success": True,
                "columns": ["segment", "total_revenue", "order_count", "avg_revenue_per_order"],
                "rows": [
                    ["成长型团队", 2798216.93, 628, 4455.76],
                    ["高价值企业", 2158510.79, 340, 6348.56],
                ],
            },
            "evidence_result": {"validation_status": "validated"},
            "trace": [{"node": "sql_executor_node"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "按客户分群看收入、订单量和客单价，判断哪个分群最值得重点运营。",
        section_runner=conflicting_runner,
    )

    first_section = result["report"]["sections"][0]
    answer = first_section["business_answer"]
    answer_text = json.dumps(answer, ensure_ascii=False)
    assert first_section["status"] == "completed"
    assert "成长型团队" in answer_text
    assert "高价值企业" in answer_text
    assert any(marker in answer_text for marker in ("取舍", "权衡", "口径", "如果目标", "按收入", "按客单价"))
    assert not (
        "高价值企业最值得重点运营" in answer["headline"] + answer["direct_answer"]
        and "证据表第一行显示：segment 为 成长型团队" in answer["why"]
    )
    summary_text = " ".join(result["report"]["executive_summary"])
    assert "内部 section 提示" not in summary_text
    assert "这里的长正文不应被 executive summary 原样重复" not in summary_text


def test_report_section_reuses_reviewed_composed_business_answer(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def reviewed_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "final_answer": "Old draft said Gamma should win on margin_rate.",
            "product_result": {
                "version": "p16.v1",
                "business_answer": {
                    "headline": "Alpha 是当前证据支持的优先对象",
                    "direct_answer": "当前证据支持优先关注 Alpha，因为它在 score_value 上排名第一。",
                    "why": "执行结果显示 Alpha 的 score_value 为 91.0，高于 Beta 的 83.0。",
                    "evidence_bullets": ["Alpha score_value 为 91.0。", "Beta score_value 为 83.0。"],
                    "recommendations": ["围绕 Alpha 做下一步复盘，并继续跟踪 score_value。"],
                    "caveats": ["本结论只基于当前查询返回的数据。"],
                    "confidence": "medium",
                },
            },
            "insight": {
                "answer_review": {
                    "status": "revise",
                    "unsupported_entities": ["Gamma"],
                    "unsupported_metrics": ["margin_rate"],
                },
                "answer_composition": {"source": "provider"},
            },
            "execution_result": {
                "success": True,
                "columns": ["entity_name", "score_value"],
                "rows": [["Alpha", 91.0], ["Beta", 83.0]],
            },
            "evidence_result": {"validation_status": "validated"},
            "trace": [{"node": "answer_reviewer_agent"}, {"node": "final_answer_composer"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "生成一份复盘报告。",
        section_runner=reviewed_runner,
    )

    answer = result["report"]["sections"][0]["business_answer"]
    answer_text = json.dumps(answer, ensure_ascii=False)
    assert result["report"]["sections"][0]["status"] == "completed"
    assert "Alpha" in answer_text
    assert "Gamma" not in answer_text
    assert "margin_rate" not in answer_text
    assert "Old draft" not in answer_text


def test_report_section_business_answer_uses_business_field_labels(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def localized_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        return {
            "status": "completed",
            "product_result": {
                "version": "p16.v1",
                "business_answer": {
                    "headline": "email 渠道收入最高",
                    "direct_answer": "email 渠道收入最高。",
                    "why": "证据显示 email 的 total_revenue 为 44548.53。",
                    "evidence_bullets": ["email total_revenue 为 44548.53，order_count 为 120，avg_order_value 为 371.24。"],
                    "recommendations": ["继续复盘 email。"],
                    "caveats": ["当前只基于本次查询结果。"],
                    "confidence": "high",
                },
            },
            "execution_result": {
                "success": True,
                "columns": ["channel", "total_revenue", "order_count", "avg_order_value"],
                "rows": [["email", 44548.53, 120, 371.24]],
            },
            "evidence_result": {"validation_status": "validated"},
            "trace": [{"node": "final_answer_composer"}],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "生成收入趋势报告。",
        section_runner=localized_runner,
    )

    answer = result["report"]["sections"][0]["business_answer"]
    answer_text = json.dumps(answer, ensure_ascii=False)
    assert result["report"]["sections"][0]["status"] == "completed"
    assert "收入" in answer_text
    assert "订单数" in answer_text
    assert "客单价" in answer_text
    assert "total_revenue" not in answer_text
    assert "order_count" not in answer_text
    assert "avg_order_value" not in answer_text
    assert answer["headline"] != "completed"


def test_business_review_section_questions_are_specific_internal_analysis_prompts():
    report_goal = "基于最近 90 天的订单、客户和营销数据，生成面向管理层的收入复盘报告。"
    sections = {
        section["section_id"]: section
        for section in REPORT_TYPE_PRESETS["business_review"]["sections"]
    }

    channel_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["top_channels_or_products"],
    )
    overall_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["overall_revenue"],
    )
    trend_question = _section_question(
        report_goal=report_goal,
        report_type="business_review",
        section_plan=sections["trend_or_recent_change"],
    )

    assert "报告内部 section" in channel_question
    assert "不要请求用户补充" in channel_question
    assert "渠道" in channel_question
    assert "channel" in channel_question
    assert "收入" in channel_question
    assert "产品或其他" not in channel_question
    assert "只使用订单、渠道、收入、日期等聚合字段" in overall_question
    assert "非个人级聚合" in overall_question
    assert "不访问个人身份字段" in overall_question
    assert "customer_id" not in overall_question
    assert "客户数" not in overall_question
    assert "order_date" in trend_question
    assert "最近 90 天" in trend_question
    assert "按月" in trend_question or "按周" in trend_question
    assert "不要请求用户补充" in trend_question


def test_existing_semantic_layer_is_not_overwritten(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    existing_semantic = {
        "workspace_id": workspace["workspace_id"],
        "metrics": [{"name": "reviewed_revenue", "formula": "SUM(orders.revenue)"}],
        "dimensions": [],
        "time_fields": [],
        "entities": [],
        "join_paths": [],
    }
    Path(workspace["semantic_layer_path"]).write_text(
        yaml.safe_dump(existing_semantic, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析收入趋势。",
        section_runner=_fake_section_runner([]),
    )

    loaded = yaml.safe_load(
        Path(workspace["semantic_layer_path"]).read_text(encoding="utf-8")
    )
    assert loaded["metrics"][0]["name"] == "reviewed_revenue"


def test_provider_unavailable_section_is_retried_before_marking_failed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def retryable_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        if len(calls) == 1:
            return {
                "status": "waiting_for_clarification",
                "final_answer": (
                    "需要补充信息后才能继续分析：Provider question understanding is unavailable; "
                    "please retry with a configured provider."
                ),
                "execution_result": {},
                "question_understanding": {
                    "provider_called": True,
                    "source": "provider_unavailable",
                    "strategy": "clarify",
                    "missing_slots": ["provider_output"],
                    "fallback_used": True,
                },
                "trace": [
                    {"node": "question_understanding_agent"},
                    {"node": "clarification_router_agent"},
                    {"node": "early_response_node"},
                ],
            }
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=retryable_runner,
    )

    assert result["success"] is True
    assert result["report"]["status"] == "completed"
    assert len(calls) == len(result["report"]["sections"]) + 1
    assert result["report"]["sections"][0]["status"] == "completed"
    assert "early_response_node" not in result["report"]["sections"][0]["trace_nodes"]


def test_provider_unavailable_section_can_retry_twice_before_success(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def retryable_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        if len(calls) <= 2:
            return {
                "status": "waiting_for_clarification",
                "final_answer": (
                    "需要补充信息后才能继续分析：Provider question understanding is unavailable; "
                    "please retry with a configured provider."
                ),
                "execution_result": {},
                "question_understanding": {
                    "provider_called": True,
                    "source": "provider_unavailable",
                    "strategy": "clarify",
                    "missing_slots": ["provider_output"],
                    "fallback_used": True,
                    "validation_error": "question_understanding schema validation failed",
                },
                "trace": [
                    {"node": "question_understanding_agent"},
                    {"node": "clarification_router_agent"},
                    {"node": "early_response_node"},
                ],
            }
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=retryable_runner,
    )

    assert result["success"] is True
    assert result["report"]["status"] == "completed"
    assert len(calls) == len(result["report"]["sections"]) + 2
    assert result["report"]["sections"][0]["status"] == "completed"


def test_safety_reject_section_is_not_retried_into_completed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def rejecting_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        calls.append(user_question)
        return {
            "status": "failed",
            "final_answer": "请求包含敏感字段或不安全操作，已在 SQL 生成前拒绝。",
            "execution_result": {},
            "question_understanding": {
                "provider_called": True,
                "source": "provider",
                "strategy": "reject",
                "risk_flags": ["sensitive_field"],
                "rejection_reason": "Request asks for sensitive fields or unsafe data access.",
                "fallback_used": False,
            },
            "trace": [
                {"node": "question_understanding_agent"},
                {"node": "early_response_node"},
            ],
        }

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析最近 90 天收入趋势。",
        section_runner=rejecting_runner,
    )

    assert result["success"] is False
    assert result["report"]["status"] == "failed"
    assert len(calls) == len(result["report"]["sections"])
    assert all(section["status"] == "failed" for section in result["report"]["sections"])


def test_one_section_failure_marks_report_partial(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)
    calls = []

    def flaky_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        if len(calls) == 1:
            calls.append(user_question)
            raise RuntimeError("section analysis failed")
        calls.append(user_question)
        return _fake_section_runner([])(
            store, workspace_id, user_question, initial_sql, providers
        )

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "channel_performance",
        "比较渠道表现。",
        section_runner=flaky_runner,
    )

    statuses = [section["status"] for section in result["report"]["sections"]]
    assert result["report"]["status"] == "partial"
    assert "completed" in statuses
    assert "failed" in statuses
    assert Path(result["report"]["json_path"]).is_file()
    assert Path(result["report"]["markdown_path"]).is_file()


def test_all_section_failures_mark_report_failed(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    def failing_runner(store, workspace_id, user_question, initial_sql=None, providers=None):
        raise RuntimeError("provider unavailable")

    result = run_workspace_report(
        store,
        workspace["workspace_id"],
        "revenue_trend",
        "分析收入趋势。",
        section_runner=failing_runner,
    )

    assert result["success"] is False
    assert result["report"]["status"] == "failed"
    assert all(section["status"] == "failed" for section in result["report"]["sections"])
    assert all(section["error"] == "provider unavailable" for section in result["report"]["sections"])
    assert Path(result["report"]["json_path"]).is_file()
    assert Path(result["report"]["markdown_path"]).is_file()


def test_unsupported_report_type_raises_clear_error(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    with pytest.raises(ValueError, match="Unsupported report_type: unknown_report"):
        run_workspace_report(
            store,
            workspace["workspace_id"],
            "unknown_report",
            "生成报告。",
            section_runner=_fake_section_runner([]),
        )


def test_missing_report_goal_raises_clear_error(tmp_path):
    store, workspace = _create_workspace_with_orders(tmp_path)

    with pytest.raises(ValueError, match="report_goal is required"):
        run_workspace_report(
            store,
            workspace["workspace_id"],
            "business_review",
            "   ",
            section_runner=_fake_section_runner([]),
        )
