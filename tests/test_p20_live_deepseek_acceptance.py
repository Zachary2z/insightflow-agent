import json
import os
from pathlib import Path

import pytest

from llm_ops.deepseek_provider import load_deepseek_config
from llm_ops.runtime_provider import (
    build_report_composer_provider,
    product_live_mode_enabled,
    provider_question_understanding_enabled,
    provider_report_composer_enabled,
    provider_sql_candidate_enabled,
    provider_sql_planning_enabled,
    provider_visualization_agent_enabled,
)
from workspaces.analysis_runner import run_workspace_analysis
from workspaces.importers import import_csv
from workspaces.profiler import profile_workspace_database
from workspaces.report_runner import run_workspace_report
from workspaces.semantic_draft import generate_semantic_layer_draft
from workspaces.store import WorkspaceStore


pytestmark = pytest.mark.skipif(
    os.getenv("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS") != "1",
    reason="Live DeepSeek tests are opt-in.",
)


def _require_live_deepseek_p20() -> None:
    if not product_live_mode_enabled():
        pytest.skip("Set INSIGHTFLOW_PRODUCT_LIVE_MODE=1 for P20 live acceptance.")
    if not provider_question_understanding_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING=1.")
    if not provider_sql_planning_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING=1.")
    if not provider_sql_candidate_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE=1.")
    config = load_deepseek_config(require_api_key=True)
    if not config.success:
        pytest.skip("Set DEEPSEEK_API_KEY to run P20 live DeepSeek acceptance.")


def _prepare_store_sales_workspace(tmp_path: Path) -> tuple[WorkspaceStore, str]:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    csv_path = dataset_dir / "store_sales.csv"
    csv_path.write_text(
        "\n".join(
            [
                "store_name,business_date,city,sales_amount,gross_margin,satisfaction_score",
                "上海旗舰店,2026-04-01,上海,21500,0.37,4.8",
                "上海旗舰店,2026-05-01,上海,23800,0.39,4.7",
                "上海旗舰店,2026-06-01,上海,26255.44,0.41,4.8",
                "北京国贸店,2026-04-01,北京,17600,0.34,4.3",
                "北京国贸店,2026-05-01,北京,18100,0.35,4.4",
                "北京国贸店,2026-06-01,北京,18400,0.36,4.4",
                "深圳湾店,2026-04-01,深圳,11000,0.31,4.1",
                "深圳湾店,2026-05-01,深圳,11600,0.32,4.2",
                "深圳湾店,2026-06-01,深圳,12000,0.33,4.1",
            ]
        ),
        encoding="utf-8",
    )
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P20 Live DeepSeek Store Acceptance")
    import_csv(store, workspace["workspace_id"], csv_path)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    assert profile["tables"]
    assert semantic_layer["metrics"]
    assert semantic_layer["dimensions"]
    return store, workspace["workspace_id"]


def _require_live_deepseek_p24() -> None:
    _require_live_deepseek_p20()
    if not provider_visualization_agent_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT=1.")
    if not provider_report_composer_enabled():
        pytest.skip("Set INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER=1.")


def _prepare_p24_business_workspace(tmp_path: Path) -> tuple[WorkspaceStore, str, dict, dict]:
    dataset_dir = tmp_path / "p24_dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "store_sales.csv": (
            "门店,营业日期,城市,销售额,订单数",
            [
                "上海旗舰店,2026-06-01,上海,38200,126",
                "北京国贸店,2026-06-01,北京,29100,98",
                "深圳湾店,2026-06-01,深圳,24600,88",
            ],
        ),
        "product_sales.csv": (
            "品类,销售月份,成交金额,销量",
            [
                "咖啡豆,2026-06,186000,620",
                "挂耳咖啡,2026-06,94000,1880",
                "杯具周边,2026-06,52000,430",
            ],
        ),
        "customer_segments.csv": (
            "客户分群,月份,客户数,成交金额",
            [
                "高价值会员,2026-06,460,248000",
                "新客,2026-06,980,176000",
                "沉睡唤醒,2026-06,210,39000",
            ],
        ),
        "support_tickets.csv": (
            "客服团队,工单日期,工单数,平均响应分钟,满意度",
            [
                "华东客服组,2026-06-01,178,16,4.8",
                "华北客服组,2026-06-01,155,33,4.2",
                "华南客服组,2026-06-01,138,22,4.5",
            ],
        ),
        "channel_spend.csv": (
            "渠道,日期,收入金额,投放金额",
            [
                "小红书,2026-06-01,320000,86000",
                "抖音,2026-06-01,410000,160000",
                "私域社群,2026-06-01,198000,28000",
            ],
        ),
        "regional_sales.csv": (
            "区域,统计日期,GMV,订单数",
            [
                "华东,2026-06-01,520000,1810",
                "华北,2026-06-01,330000,1200",
                "华南,2026-06-01,365000,1375",
            ],
        ),
    }
    store = WorkspaceStore(tmp_path / "workspaces")
    workspace = store.create_workspace("P24 Live DeepSeek Business Acceptance")
    for filename, (header, rows) in files.items():
        csv_path = dataset_dir / filename
        csv_path.write_text("\n".join([header, *rows]), encoding="utf-8")
        import_csv(store, workspace["workspace_id"], csv_path)
    profile = profile_workspace_database(store, workspace["workspace_id"])
    semantic_layer = generate_semantic_layer_draft(store, workspace["workspace_id"], profile)
    return store, workspace["workspace_id"], profile, semantic_layer


def _business_answer_text(result: dict) -> str:
    answer = result["product_result"]["business_answer"]
    return "\n".join(
        [
            answer["headline"],
            answer["direct_answer"],
            answer["why"],
            *answer["evidence_bullets"],
            *answer["recommendations"],
            *answer["caveats"],
        ]
    )


def _business_decision_text(result: dict) -> str:
    answer = result["product_result"]["business_answer"]
    return "\n".join([answer["headline"], answer["direct_answer"], *answer["recommendations"]])


def _execution_entities(result: dict) -> list[str]:
    columns = [str(column) for column in result["execution_result"].get("columns") or []]
    rows = result["execution_result"].get("rows") or []
    entities: list[str] = []
    for row in rows:
        values = row if isinstance(row, (list, tuple)) else [row.get(column) for column in columns]
        for value in values:
            if isinstance(value, str) and value.strip() and value.strip() not in entities:
                entities.append(value.strip())
                break
    return entities


def _mentioned_entities(text: str, entities: list[str]) -> list[str]:
    return [entity for entity in entities if entity and entity in str(text or "")]


def _assert_no_core_recommendation_conflict(result: dict) -> None:
    entities = _execution_entities(result)
    final_mentions = _mentioned_entities(str(result.get("final_answer") or ""), entities)
    product_mentions = _mentioned_entities(_business_decision_text(result), entities)
    if len(final_mentions) == 1 and len(product_mentions) == 1:
        assert final_mentions == product_mentions


def _priority_review_risk_entity(result: dict) -> str:
    execution = result["execution_result"]
    columns = [str(column) for column in execution.get("columns") or []]
    rows = execution.get("rows") or []
    if len(rows) < 2:
        return ""
    row_dicts = [
        {column: row[index] for index, column in enumerate(columns) if index < len(row)}
        if isinstance(row, (list, tuple))
        else {str(key): value for key, value in row.items()}
        for row in rows
    ]
    entity_key = next((key for key in columns if any(isinstance(row.get(key), str) for row in row_dicts)), "")
    if not entity_key:
        return ""
    positive_tokens = ("sales", "revenue", "销售", "收入", "毛利", "margin", "满意", "satisfaction", "score")
    risk_tokens = ("response", "响应", "duration", "minutes", "投诉", "complaint", "工单压力")
    metric_directions: list[tuple[str, bool]] = []
    for column in columns:
        if column == entity_key:
            continue
        values = [_to_number(row.get(column)) for row in row_dicts]
        if not any(value is not None for value in values):
            continue
        lowered = column.lower()
        if any(token in lowered for token in positive_tokens):
            metric_directions.append((column, False))
        elif any(token in lowered for token in risk_tokens):
            metric_directions.append((column, True))
    if not metric_directions:
        return ""

    scores: dict[str, int] = {}
    for column, higher_is_risk in metric_directions:
        candidates = [
            (str(row.get(entity_key) or ""), _to_number(row.get(column)))
            for row in row_dicts
            if str(row.get(entity_key) or "").strip() and _to_number(row.get(column)) is not None
        ]
        ordered = sorted(candidates, key=lambda item: item[1] or 0, reverse=higher_is_risk)
        for rank, (entity, _value) in enumerate(ordered):
            scores[entity] = scores.get(entity, 0) + rank
    if not scores:
        return ""
    ordered_scores = sorted(scores.items(), key=lambda item: item[1])
    if len(ordered_scores) > 1 and ordered_scores[0][1] == ordered_scores[1][1]:
        return ""
    return ordered_scores[0][0]


def _to_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def test_live_deepseek_p20_store_analysis_uses_provider_chain_and_chinese_evidence(tmp_path):
    _require_live_deepseek_p20()
    store, workspace_id = _prepare_store_sales_workspace(tmp_path)

    result = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question="最近90天比较各门店销售额、毛利率和满意度，哪个门店最值得优先复盘？请给证据和风险边界。",
    )

    answer_text = _business_answer_text(result)
    assert result["status"] == "completed"
    assert result["question_understanding"]["provider_called"] is True
    assert result["question_understanding"]["source"] == "provider"
    assert result["sql_planning"]["provider_called"] is True
    assert result["sql_planning"]["source"] == "provider"
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["rows"]
    assert any("\u4e00" <= char <= "\u9fff" for char in answer_text)
    assert "SELECT " not in answer_text.upper()
    assert "provider_called" not in answer_text
    assert "参数" not in answer_text
    assert result["product_result"]["evidence"]["fact_payload"]["rows"] == result["execution_result"]["rows"]
    _assert_no_core_recommendation_conflict(result)
    risk_entity = _priority_review_risk_entity(result)
    assert risk_entity
    assert risk_entity in _business_decision_text(result)
    if risk_entity in str(result.get("final_answer") or ""):
        assert risk_entity in _business_decision_text(result)


def test_live_deepseek_p24_business_acceptance_records_analysis_report_evidence_and_limits(tmp_path):
    _require_live_deepseek_p24()
    store, workspace_id, profile, semantic_layer = _prepare_p24_business_workspace(tmp_path)

    analysis_question = "最近90天按渠道比较收入、投放金额和 ROI，哪个渠道投放效率最高？请给证据、图表和风险边界。"
    analysis = run_workspace_analysis(
        store=store,
        workspace_id=workspace_id,
        user_question=analysis_question,
    )
    answer_text = _business_answer_text(analysis)
    fact_payload = analysis["product_result"]["evidence"]["fact_payload"]
    formulas_text = json.dumps(fact_payload.get("formulas"), ensure_ascii=False)
    requirements_text = json.dumps(fact_payload.get("evidence_requirements"), ensure_ascii=False)

    assert profile["tables"]
    semantic_text = json.dumps(semantic_layer, ensure_ascii=False)
    for keyword in ["门店", "品类", "客户", "客服", "渠道", "区域", "投放"]:
        assert keyword in semantic_text
    assert analysis["status"] == "completed"
    assert analysis["question_understanding"]["provider_called"] is True
    assert analysis["sql_planning"]["provider_called"] is True
    assert analysis["llm_sql_enhancement"]["provider_called"] is True
    assert analysis["execution_result"]["success"] is True
    assert analysis["execution_result"]["rows"]
    assert analysis["product_result"]["chart_artifacts"]
    assert "渠道" in requirements_text
    assert "ROI" in requirements_text or "投放" in requirements_text
    assert "roas" in formulas_text
    assert "net_return" in formulas_text
    assert "私域社群" in json.dumps(fact_payload.get("display_values"), ensure_ascii=False) + answer_text
    assert any("\u4e00" <= char <= "\u9fff" for char in answer_text)
    assert "SELECT " not in answer_text.upper()
    assert "provider_called" not in answer_text

    report_goal = "生成经营复盘报告，覆盖门店表现、商品表现、客户分群、客服运营、渠道投放表现、利润和复购率。"
    report_provider = build_report_composer_provider()
    assert report_provider is not None
    report_result = run_workspace_report(
        store=store,
        workspace_id=workspace_id,
        report_type="business_review",
        report_goal=report_goal,
        providers={"report_composer": report_provider},
    )
    report = report_result["report"]
    document_text = json.dumps(report["document"], ensure_ascii=False)
    ledger_text = json.dumps(report["document"]["technical_appendix"]["evidence_ledger"], ensure_ascii=False)
    acceptance_record = {
        "analysis_question": analysis_question,
        "recognized_task": analysis["analysis_task"],
        "recognized_fields_and_metrics": {
            "semantic_metrics": semantic_layer.get("metrics", []),
            "semantic_dimensions": semantic_layer.get("dimensions", []),
        },
        "evidence_requirements": fact_payload.get("evidence_requirements"),
        "evidence_rows": fact_payload.get("display_values"),
        "model_answer": analysis["product_result"]["business_answer"],
        "report_goal": report_goal,
        "report_opening_summary": report["document"]["opening_summary"],
        "report_sections": report["document"]["sections"],
        "report_data_boundaries": report["document"]["data_boundaries"],
    }

    assert report_result["success"] is True
    assert report["status"] == "completed"
    assert report["provider_metadata"]["provider_supplied"] is True
    assert report["validation"]["status"] == "passed"
    assert "p23.report_ledger.v1" in ledger_text
    assert "门店表现" in document_text or "门店表现" in ledger_text
    assert "渠道投放" in document_text or "渠道投放" in ledger_text
    assert any("复购" in item or "利润" in item for item in report["document"]["data_boundaries"])
    assert report["artifacts"]
    assert any(artifact["artifact_type"] == "chart" for artifact in report["artifacts"])
    assert "章节业务答案" not in document_text
    assert "SELECT " not in document_text.upper()
    assert "provider_called" not in document_text
    assert acceptance_record["analysis_question"]
    assert acceptance_record["recognized_fields_and_metrics"]["semantic_metrics"]
    assert acceptance_record["evidence_requirements"]
    assert acceptance_record["model_answer"]["headline"]
    assert acceptance_record["report_sections"]
