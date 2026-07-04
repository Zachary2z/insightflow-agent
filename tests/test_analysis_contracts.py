import json

from workspaces.analysis_contracts import (
    AnalysisTask,
    AuditResult,
    CoordinatorDecision,
    QuestionEvidencePack,
    WorkbenchToolCall,
)


def test_analysis_workbench_contracts_round_trip_without_provider_dependencies():
    task = AnalysisTask(
        resolved_question="最近90天哪个门店销售额最高？",
        metrics=["销售额"],
        dimensions=["门店"],
        time_range={"raw_text": "最近90天"},
        filters=["区域=华东"],
        decision_goal="找出销售额最高的门店",
        route_hint="fast_fact",
    )
    decision = CoordinatorDecision(
        route="fast_fact",
        required_agents=["data_understanding", "evidence", "evidence_auditor", "business_answer"],
        reason="问题槽位完整且只需要事实排名。",
    )
    tool_call = WorkbenchToolCall(
        tool_name="sql_executor",
        purpose="执行只读销售额排名查询",
        input_summary="按门店聚合销售额，限制返回前 20 行",
        output_summary="返回 2 行门店销售额",
        status="completed",
    )
    evidence_pack = QuestionEvidencePack(
        task=task,
        sql="SELECT store_name, SUM(sales_amount) AS total_sales FROM store_sales GROUP BY store_name",
        rows=[{"门店": "上海旗舰店", "销售额": "30.0 万"}],
        columns=["门店", "销售额"],
        metrics=["销售额"],
        chart_candidates=[{"chart_type": "bar", "title": "门店销售额排名"}],
        tool_calls=[tool_call],
        data_limits=["仅覆盖当前工作区数据。"],
    )
    audit = AuditResult(
        supported_facts=["上海旗舰店销售额为 30.0 万。"],
        reasonable_inferences=["上海旗舰店可作为销售标杆进一步复盘。"],
        unsupported_claims=[],
        data_limits=evidence_pack.data_limits,
        confidence="medium",
    )

    payload = {
        "task": task.to_dict(),
        "decision": decision.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
        "audit": audit.to_dict(),
    }
    restored_pack = QuestionEvidencePack.from_dict(
        json.loads(json.dumps(evidence_pack.to_dict(), ensure_ascii=False))
    )
    result_evidence = evidence_pack.to_result_evidence()

    assert payload["decision"]["user_language"] == "zh"
    assert payload["task"]["missing_slots"] == []
    assert payload["task"]["clarification_question"] == ""
    assert payload["evidence_pack"]["task"]["resolved_question"] == task.resolved_question
    assert payload["evidence_pack"]["tool_calls"][0]["status"] == "completed"
    assert restored_pack.task.metrics == ["销售额"]
    assert restored_pack.rows[0]["门店"] == "上海旗舰店"
    assert result_evidence["columns"] == ["门店", "销售额"]
    assert result_evidence["rows"][0]["销售额"] == "30.0 万"
    assert "sql" not in result_evidence
    assert "DEEPSEEK_API_KEY" not in json.dumps(payload, ensure_ascii=False)


def test_analysis_task_can_normalize_existing_analysis_task_dict():
    task = AnalysisTask.from_dict(
        {
            "resolved_question": "按渠道比较 ROI",
            "metrics": ["ROI"],
            "dimensions": ["渠道"],
            "time_range": {"raw_text": "完整数据时间范围：2025-01-01 至 2026-06-30"},
            "filters": [],
            "decision_goal": "判断投放效率最高渠道",
            "missing_slots": ["time_grain"],
            "clarification_question": "请补充趋势粒度。",
            "route_hint": "clarify",
            "task_type": "rank",
            "output_language": "zh",
        }
    )

    serialized = task.to_dict()

    assert serialized["resolved_question"] == "按渠道比较 ROI"
    assert serialized["metrics"] == ["ROI"]
    assert serialized["dimensions"] == ["渠道"]
    assert serialized["missing_slots"] == ["time_grain"]
    assert serialized["clarification_question"] == "请补充趋势粒度。"
    assert serialized["route_hint"] == "clarify"
    assert "task_type" not in serialized
