def _execution_result():
    return {
        "success": True,
        "columns": ["product_name", "gmv", "order_count"],
        "rows": [["Laptop Pro 14", 511248.56, 128], ["Camera A", 456050.99, 102]],
        "row_count": 2,
    }


def test_validate_evidence_classifies_supported_hypotheses_and_blocks_unsupported_claims():
    from tools.evidence_tool import validate_evidence

    result = validate_evidence(
        claims=[
            "Laptop Pro 14 的 GMV 为 511248.56",
            "可能与广告流量下降有关，需要 ad_impressions、ctr 和 conversion_rate 数据进一步验证",
            "库存不足是导致 Camera A 销量下降的主要原因",
        ],
        execution_result=_execution_result(),
    )

    assert result["success"] is True
    assert result["unsupported_claim_rate"] == 1 / 3
    assert result["data_supported_findings"] == [
        {
            "claim": "Laptop Pro 14 的 GMV 为 511248.56",
            "evidence": "SQL result row: product_name=Laptop Pro 14, gmv=511248.56, order_count=128",
            "confidence": 0.95,
        }
    ]
    assert result["hypotheses"] == [
        {
            "claim": "可能与广告流量下降有关，需要 ad_impressions、ctr 和 conversion_rate 数据进一步验证",
            "reason": "Claim is framed as a hypothesis or references data not present in current evidence.",
            "needs_more_data": ["ad_impressions", "ctr", "conversion_rate"],
        }
    ]
    assert result["unsupported_claims_blocked"] == ["库存不足是导致 Camera A 销量下降的主要原因"]
    assert result["trace_event"]["tool_name"] == "validate_evidence"
    assert result["trace_event"]["status"] == "success"


def test_validate_evidence_uses_business_context_as_supporting_evidence():
    from tools.evidence_tool import validate_evidence

    result = validate_evidence(
        claims=["GMV 必须只统计 paid 订单"],
        execution_result=_execution_result(),
        business_context={
            "matched_rules": [
                {
                    "title": "paid_orders_define_sales",
                    "content": "Sales analysis must use paid orders only. Required SQL filter: orders.status = 'paid'",
                }
            ]
        },
    )

    assert result["success"] is True
    assert result["data_supported_findings"][0]["claim"] == "GMV 必须只统计 paid 订单"
    assert result["data_supported_findings"][0]["evidence"] == "Business rule: paid_orders_define_sales"
    assert result["unsupported_claims_blocked"] == []


def test_validate_evidence_returns_error_for_missing_claims():
    from tools.evidence_tool import validate_evidence

    result = validate_evidence(claims=[], execution_result=_execution_result())

    assert result["success"] is False
    assert result["data_supported_findings"] == []
    assert result["hypotheses"] == []
    assert result["unsupported_claims_blocked"] == []
    assert "claims are required" in result["error"]
    assert result["trace_event"]["status"] == "error"
    assert result["trace_event"]["error_type"] == "evidence_validation_error"


def test_build_evidence_payload_preserves_comparison_rows_formulas_and_business_formats():
    from tools.evidence_tool import build_evidence_payload

    execution_result = {
        "success": True,
        "columns": ["channel", "total_revenue", "total_spend", "roas", "net_return"],
        "rows": [
            ["自然流量", 26255.44, 0.0, None, None],
            ["付费搜索", 18400.0, 5000.0, 3.68, 2.68],
            ["内容种草", 12000.0, 4500.0, 2.6667, 1.6667],
        ],
        "row_count": 3,
    }
    metric_registry = {
        "metrics": {
            "roas": {
                "business_label": "广告投入产出比",
                "formula": "SUM(revenue) / NULLIF(SUM(spend), 0)",
                "unit": "ratio",
            },
            "net_return": {
                "business_label": "净投放回报率",
                "formula": "(SUM(revenue) - SUM(spend)) / NULLIF(SUM(spend), 0)",
                "unit": "percentage",
            },
        },
        "formulas": {
            "roas": "SUM(revenue) / NULLIF(SUM(spend), 0)",
            "net_return": "(SUM(revenue) - SUM(spend)) / NULLIF(SUM(spend), 0)",
        },
        "warnings": [],
    }

    payload = build_evidence_payload(
        task={"task_type": "recommendation", "dimensions": ["渠道"], "metrics": ["ROAS"], "time_range": {"raw_text": "最近 90 天"}},
        execution_result=execution_result,
        metric_registry=metric_registry,
        sql="SELECT ...",
        filters=["country = 'CN'"],
    )

    assert payload["task_type"] == "recommendation"
    assert payload["columns"] == execution_result["columns"]
    assert payload["rows"] == execution_result["rows"]
    assert payload["comparison_scope"]["row_count"] == 3
    assert payload["comparison_scope"]["sufficient"] is True
    assert payload["formulas"]["roas"] != payload["formulas"]["net_return"]
    assert payload["time_scope"] == {"raw_text": "最近 90 天"}
    assert payload["filters"] == ["country = 'CN'"]
    assert payload["display_values"][0]["总收入"] == "2.6 万"
    assert payload["display_values"][1]["广告投入产出比"] == "3.68"
    assert payload["display_values"][1]["净投放回报率"] == "268.0%"
    assert payload["technical_sql"] == "SELECT ..."


def test_build_evidence_payload_warns_when_ranking_has_only_winner_row():
    from tools.evidence_tool import build_evidence_payload

    payload = build_evidence_payload(
        task={"task_type": "rank", "dimensions": ["门店"], "metrics": ["销售额"], "time_range": {"raw_text": "本月"}},
        execution_result={
            "success": True,
            "columns": ["store_name", "total_revenue"],
            "rows": [["上海旗舰店", 99800.0]],
            "row_count": 1,
        },
        metric_registry={"metrics": {}, "formulas": {}, "warnings": []},
        sql="SELECT store_name, SUM(sales) AS total_revenue FROM store_sales GROUP BY store_name ORDER BY total_revenue DESC LIMIT 1",
    )

    assert payload["comparison_scope"]["required_min_rows"] == 2
    assert payload["comparison_scope"]["sufficient"] is False
    assert any("比较范围不足" in warning for warning in payload["warnings"])
    assert payload["display_values"][0]["门店"] == "上海旗舰店"
    assert payload["display_values"][0]["总收入"] == "10.0 万"


def test_build_evidence_payload_supports_non_channel_business_dataset_aliases():
    from tools.evidence_tool import build_evidence_payload

    payload = build_evidence_payload(
        task={"task_type": "rank", "dimensions": ["客服分组"], "metrics": ["平均解决时长"], "time_range": {"raw_text": "最近 30 天"}},
        execution_result={
            "success": True,
            "columns": ["team_name", "avg_resolution_hours", "ticket_count"],
            "rows": [["售后组", 3.2, 84], ["技术组", 5.7, 61]],
        },
        metric_registry={"metrics": {}, "formulas": {}, "warnings": []},
        business_aliases={"team_name": "客服分组", "avg_resolution_hours": "平均解决时长", "ticket_count": "工单数"},
    )

    assert payload["dimensions"] == ["客服分组"]
    assert payload["metrics"] == ["平均解决时长"]
    assert payload["display_values"][0]["客服分组"] == "售后组"
    assert payload["display_values"][0]["平均解决时长"] == "3.2"
    assert payload["display_values"][0]["工单数"] == "84"


def test_build_evidence_payload_exposes_shared_pack_with_traceable_derived_metrics():
    from tools.evidence_tool import build_evidence_payload

    payload = build_evidence_payload(
        task={
            "task_type": "rank",
            "dimensions": ["门店"],
            "metrics": ["销售额"],
            "time_range": {"raw_text": "最近 90 天"},
            "decision_goal": "比较门店销售贡献",
        },
        execution_result={
            "success": True,
            "columns": ["store_name", "sales_amount"],
            "rows": [["上海旗舰店", 300000.0], ["北京国贸店", 100000.0]],
        },
        metric_registry={
            "metrics": {
                "sum_sales_amount": {
                    "business_label": "销售额",
                    "formula": 'SUM("store_sales"."sales_amount")',
                    "unit": "currency",
                    "source_fields": ["store_sales.sales_amount"],
                }
            },
            "formulas": {"sum_sales_amount": 'SUM("store_sales"."sales_amount")'},
            "warnings": [],
        },
        sql='SELECT "store_name", SUM("sales_amount") AS sales_amount FROM "store_sales" GROUP BY "store_name"',
        business_aliases={"store_name": "门店", "sales_amount": "销售额"},
    )

    assert payload["evidence_pack_version"] == "p23.shared.v1"
    assert payload["time_range"] == {"raw_text": "最近 90 天"}
    assert payload["intent"] == {"task_type": "rank", "decision_goal": "比较门店销售贡献"}
    assert payload["result_rows"][0]["dimensions"][0] == {
        "key": "store_name",
        "label": "门店",
        "value": "上海旗舰店",
        "display_value": "上海旗舰店",
    }
    assert payload["result_rows"][0]["metrics"][0]["key"] == "sales_amount"
    assert payload["result_rows"][0]["metrics"][0]["display_value"] == "30.0 万"
    share = next(item for item in payload["derived_metrics"] if item["metric_id"] == "sales_amount_share")
    assert share["label"] == "销售额占比"
    assert share["formula"] == "sales_amount / SUM(sales_amount)"
    assert share["source_columns"] == ["sales_amount"]
    assert share["values"][0]["display_value"] == "75.0%"
    rank = next(item for item in payload["derived_metrics"] if item["metric_id"] == "sales_amount_rank")
    assert rank["values"][0]["display_value"] == "第 1 名"
    assert payload["formula_metadata"][0] == {
        "metric_id": "sum_sales_amount",
        "label": "销售额",
        "formula": 'SUM("store_sales"."sales_amount")',
        "source_columns": ["store_sales.sales_amount"],
        "unit": "currency",
        "derived": False,
    }
    assert payload["chart_data"]["x_axis"] == "store_name"
    assert payload["chart_data"]["y_axis"] == "sales_amount"
    assert payload["data_limits"] == []
    assert payload["technical_refs"] == {"sql": "technical_details.sql", "raw_rows": "technical_details.raw_rows"}


def test_build_evidence_payload_records_missing_metric_limit_instead_of_inventing_roi():
    from tools.evidence_tool import build_evidence_payload

    payload = build_evidence_payload(
        task={
            "task_type": "recommendation",
            "dimensions": ["门店"],
            "metrics": ["销售额", "ROI"],
            "time_range": {"raw_text": "最近 90 天"},
        },
        execution_result={
            "success": True,
            "columns": ["store_name", "sales_amount"],
            "rows": [["上海旗舰店", 300000.0], ["北京国贸店", 100000.0]],
        },
        metric_registry={
            "metrics": {
                "sum_sales_amount": {
                    "business_label": "销售额",
                    "formula": 'SUM("store_sales"."sales_amount")',
                    "unit": "currency",
                    "source_fields": ["store_sales.sales_amount"],
                }
            },
            "formulas": {"sum_sales_amount": 'SUM("store_sales"."sales_amount")'},
            "warnings": [],
        },
        business_aliases={"store_name": "门店", "sales_amount": "销售额"},
    )

    assert "roi" not in {item["metric_id"].lower() for item in payload["derived_metrics"]}
    assert any("ROI" in limit and "未计算" in limit for limit in payload["data_limits"])
