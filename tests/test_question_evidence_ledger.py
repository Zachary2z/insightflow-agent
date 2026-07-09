from workspaces.analysis_contracts import AnalysisTask, QuestionEvidencePack, WorkbenchToolCall


def _pack(rows=None, columns=None, data_limits=None, task_id=""):
    return QuestionEvidencePack(
        task=AnalysisTask(
            resolved_question="最近90天哪个渠道收入最高？",
            metrics=["收入"],
            dimensions=["渠道"],
            time_range={"raw_text": "最近90天"},
            business_lens={
                "business_domain": "channel_performance",
                "metrics": [
                    {
                        "label": "收入",
                        "source_table": "orders",
                        "source_field": "revenue",
                        "time_field": "order_date",
                    }
                ],
                "dimensions": [{"label": "渠道", "source_table": "orders", "source_field": "channel"}],
                "time_policy_note": "收入按下单日期统计，时间范围为最近90天。",
                "data_limits": [],
            },
        ),
        rows=rows
        if rows is not None
        else [
            {"channel": "私域社群", "total_revenue": 300000.0},
            {"channel": "搜索广告", "total_revenue": 100000.0},
        ],
        columns=columns if columns is not None else ["channel", "total_revenue"],
        metrics=["收入"],
        tool_calls=[
            WorkbenchToolCall(
                tool_name="sql_execution",
                purpose="执行已审核查询",
                input_summary="SELECT channel, SUM(revenue) FROM orders /tmp/ws/runs/run_1/trace.json",
                output_summary="rows=2 provider_metadata={'api_key':'sk-test'}",
                status="completed",
            )
        ],
        data_limits=data_limits or [],
        sql="SELECT channel, SUM(revenue) FROM orders GROUP BY channel",
    )


def test_builds_ledger_from_question_evidence_pack_and_execution_result():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(),
        execution_result={
            "success": True,
            "columns": ["channel", "total_revenue"],
            "rows": [["私域社群", 300000.0], ["搜索广告", 100000.0]],
        },
        evidence_validation={"validation_status": "validated"},
        chart_artifacts=[{"artifact_id": "chart_1", "evidence_refs": ["question_evidence_pack"]}],
    )

    assert ledger["ledger_id"].startswith("qledger_")
    assert ledger["source_pack_id"] == "question_evidence_pack"
    assert ledger["business_lens"]["business_domain"] == "channel_performance"
    assert ledger["time_policy_note"] == "收入按下单日期统计，时间范围为最近90天。"
    assert ledger["confidence"] in {"medium", "high"}
    assert ledger["facts"]
    assert ledger["evidence_refs"]
    assert ledger["chart_refs"] == ["chart_1"]


def test_hard_facts_include_source_columns_row_refs_and_evidence_refs():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    first = ledger["facts"][0]

    assert first["fact_id"] == "fact_revenue_by_channel_1"
    assert first["task_id"] == "revenue_by_channel"
    assert first["label"] == "收入"
    assert first["value"] == 300000.0
    assert first["dimension"] == {"channel": "私域社群"}
    assert first["source_columns"] == ["channel", "total_revenue"]
    assert first["source_row_refs"] == ["revenue_by_channel:row:0"]
    assert first["evidence_ref"] in ledger["evidence_refs"]
    assert first["evidence_ref"].startswith("evidence:revenue_by_channel:")


def test_derived_metrics_preserve_formula_and_source_columns():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(),
        task_id="revenue_by_channel",
        fact_payload={
            "derived_metrics": [
                {
                    "metric_id": "total_revenue_share",
                    "label": "收入占比",
                    "formula": "total_revenue / SUM(total_revenue)",
                    "source_columns": ["total_revenue"],
                    "values": [{"row_index": 0, "value": 0.75, "display_value": "75.0%"}],
                }
            ]
        },
    )

    derived = ledger["derived_metrics"][0]
    assert derived["metric_id"] == "total_revenue_share"
    assert derived["task_id"] == "revenue_by_channel"
    assert derived["label"] == "收入占比"
    assert derived["formula"] == "total_revenue / SUM(total_revenue)"
    assert derived["value"] == 0.75
    assert derived["source_columns"] == ["total_revenue"]
    assert derived["evidence_ref"] in ledger["evidence_refs"]


def test_missing_evidence_creates_data_limits_not_fake_facts():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(rows=[], columns=["channel", "roi"], data_limits=["ROI 需要成本字段，当前证据不足，未计算。"]),
        evidence_validation={"validation_status": "not_validated"},
    )

    assert ledger["facts"] == []
    assert ledger["derived_metrics"] == []
    assert ledger["data_limits"] == ["ROI 需要成本字段，当前证据不足，未计算。"]
    assert ledger["confidence"] == "low"


def test_ledger_strips_sql_trace_provider_and_local_path_metadata():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(question_evidence_pack=_pack())
    payload_text = str(ledger)

    assert "SELECT" not in payload_text.upper()
    assert "/tmp/ws" not in payload_text
    assert "trace.json" not in payload_text
    assert "provider_metadata" not in payload_text
    assert "api_key" not in payload_text
    assert "sk-test" not in payload_text
    assert "sql" not in ledger


def test_merges_task_ledgers_with_task_limits_and_without_internal_leaks():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger, merge_question_evidence_ledgers

    revenue = build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    spend = build_question_evidence_ledger(
        question_evidence_pack=_pack(
            rows=[{"channel": "私域社群", "total_spend": 30000.0}],
            columns=["channel", "total_spend"],
        ),
        task_id="spend_by_channel",
    )

    merged = merge_question_evidence_ledgers(
        [revenue, spend],
        data_limits=[
            "task unsafe_support failed: SELECT * FROM orders; trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
        ],
    )
    text = str(merged)

    assert merged["source_pack_id"] == "merged_question_evidence_pack"
    assert {fact["task_id"] for fact in merged["facts"]} == {"revenue_by_channel", "spend_by_channel"}
    assert any("unsafe_support" in limit for limit in merged["data_limits"])
    assert "SELECT" not in text.upper()
    assert "/tmp/ws" not in text
    assert "provider_metadata" not in text
    assert "sk-test" not in text


def test_answer_input_ledger_exposes_business_facts_without_task_or_execution_internals():
    import workspaces.question_evidence_ledger as qel

    ledger = qel.build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    ledger["data_limits"].append(
        "证据任务 revenue_by_channel 未能完成：SELECT * FROM orders; trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
    )

    assert hasattr(qel, "build_answer_input_ledger")
    answer_input = qel.build_answer_input_ledger(ledger)
    text = str(answer_input)

    first_fact = answer_input["evidence_groups"][0]["facts"][0]
    assert first_fact["label"] == "收入"
    assert first_fact["value"] == 300000.0
    assert first_fact["business_object"] == "私域社群"
    assert first_fact["dimension"] == {"label": "渠道", "value": "私域社群"}
    assert first_fact["fact_text"] == "私域社群的收入为300000.0元。"
    assert "time_policy_note" in answer_input
    assert "data_limits" in answer_input
    assert "evidence_refs" in answer_input
    assert "facts" not in answer_input
    assert "derived_metrics" not in answer_input
    forbidden = (
        "task_id",
        "task_purpose",
        "task_refs",
        "source_pack_id",
        "source_row_refs",
        "source_columns",
        "ledger_id",
        "SELECT",
        "trace_path",
        "provider_metadata",
        "sk-test",
        "/tmp/ws",
    )
    for marker in forbidden:
        assert marker not in text


def test_chart_candidate_uses_business_labels_units_refs_and_excludes_task_internals():
    import workspaces.question_evidence_ledger as qel

    ledger = qel.build_question_evidence_ledger(
        question_evidence_pack=_pack(),
        task_id="core_fact_revenue_by_channel",
    )
    ledger["data_limits"].append(
        "证据任务 core_fact_revenue_by_channel 失败：SELECT * FROM orders trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
    )

    assert hasattr(qel, "build_grouped_chart_candidate")
    candidate = qel.build_grouped_chart_candidate(ledger, question="最近90天按渠道比较收入，并生成图表")
    payload_text = str(candidate)

    assert candidate["success"] is True
    assert candidate["source"] == "question_evidence_ledger.evidence_groups"
    assert candidate["dimension_label"] == "渠道"
    assert candidate["metric_labels"] == ["收入"]
    assert candidate["unit"] == "元"
    assert candidate["row_grain"] == "渠道"
    assert candidate["columns"] == ["渠道", "收入"]
    assert candidate["rows"][0] == ["私域社群", 300000.0]
    assert candidate["row_count"] == 2
    assert candidate["evidence_refs"]
    assert candidate["chart_spec"]["title"] == "最近90天渠道收入对比"
    assert candidate["chart_spec"]["x"] == "渠道"
    assert candidate["chart_spec"]["y"] == "收入"
    forbidden = (
        "task_id",
        "task_purpose",
        "core_fact_revenue_by_channel",
        "SELECT",
        "trace_path",
        "provider_metadata",
        "sk-test",
        "/tmp/ws",
    )
    for marker in forbidden:
        assert marker not in payload_text


def test_ledger_supports_chinese_display_units_and_ignores_time_window_numbers():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger, ledger_supports_claim

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(
            rows=[{"total_sales": 56655.44}],
            columns=["total_sales"],
        )
    )

    assert ledger_supports_claim(ledger, "最近90天收入 为 5.7 万。")


def test_ledger_supports_ranked_chinese_fact_without_treating_rank_as_metric_value():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger, ledger_supports_claim

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(
            rows=[{"channel_name": "私域社群", "total_revenue": 180000.0}],
            columns=["channel_name", "total_revenue"],
        )
    )

    assert ledger_supports_claim(ledger, "私域社群销售额180000元，排名第1。")


def test_ledger_supports_percentage_display_claims_against_ratio_metrics():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger, ledger_supports_claim

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(
            rows=[
                {"channel_name": "私域社群", "sum_revenue": 180000.0},
                {"channel_name": "搜索广告", "sum_revenue": 120000.0},
                {"channel_name": "直播间", "sum_revenue": 90000.0},
            ],
            columns=["channel_name", "sum_revenue"],
        ),
        fact_payload={
            "derived_metrics": [
                {
                    "metric_id": "sum_revenue_share",
                    "label": "销售额占比",
                    "formula": "sum_revenue / SUM(sum_revenue)",
                    "source_columns": ["sum_revenue"],
                    "values": [
                        {"row_index": 0, "value": 0.46153846153846156},
                        {"row_index": 1, "value": 0.3076923076923077},
                        {"row_index": 2, "value": 0.23076923076923078},
                    ],
                }
            ]
        },
    )

    assert ledger_supports_claim(ledger, "私域社群销售额占比为46.15%。")


def test_question_evidence_plan_and_groups_capture_source_roles_and_chartability():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    ledger = build_question_evidence_ledger(
        question_evidence_pack=_pack(
            rows=[{"channel": "私域社群", "total_revenue": 300000.0}],
            columns=["channel", "total_revenue"],
        ),
        task_id="revenue_by_channel",
    )

    plan = ledger["question_evidence_plan"]
    groups = ledger["evidence_groups"]

    assert plan["plan_id"].startswith("qplan_")
    assert plan["groups"] == ["group_revenue_by_channel"]
    assert len(groups) == 1
    group = groups[0]
    assert group["group_id"] == "group_revenue_by_channel"
    assert group["purpose"] == "关键事实"
    assert group["source"]["tables"] == ["orders"]
    assert group["source"]["fields"] == ["channel", "revenue", "total_revenue"]
    assert group["dimension"] == {"role": "dimension", "label": "渠道", "source_columns": ["channel"]}
    assert group["metrics"] == [
        {
            "role": "metric",
            "label": "收入",
            "source_column": "total_revenue",
            "source_fields": ["revenue"],
            "unit": "currency",
        }
    ]
    assert group["time_policy"] == "收入按下单日期统计，时间范围为最近90天。"
    assert group["row_grain"] == "渠道"
    assert group["supports_answer"] is True
    assert group["supports_chart"] is True
    assert group["evidence_refs"] == [ledger["facts"][0]["evidence_ref"]]


def test_metric_labels_follow_returned_source_columns_not_planner_metric_order():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger

    pack = _pack(
        rows=[{"channel": "私域社群", "total_spend": 30000.0, "total_revenue": 180000.0}],
        columns=["channel", "total_spend", "total_revenue"],
    )
    pack.metrics = ["销售额", "投放成本"]
    pack.task.metrics = ["销售额", "投放成本"]
    pack.task.business_lens["metrics"] = [
        {"label": "销售额", "source_table": "orders", "source_field": "revenue"},
        {"label": "投放成本", "source_table": "marketing_spend", "source_field": "spend"},
    ]

    ledger = build_question_evidence_ledger(question_evidence_pack=pack, task_id="channel_efficiency")
    by_column = {
        fact["source_columns"][-1]: fact["label"]
        for fact in ledger["facts"]
        if fact["dimension"].get("channel") == "私域社群"
    }

    assert by_column["total_spend"] == "投放成本"
    assert by_column["total_revenue"] == "销售额"
    group_metrics = {metric["source_column"]: metric["label"] for metric in ledger["evidence_groups"][0]["metrics"]}
    assert group_metrics["total_spend"] == "投放成本"
    assert group_metrics["total_revenue"] == "销售额"


def test_merged_ledger_keeps_business_objects_in_separate_evidence_groups():
    from workspaces.question_evidence_ledger import build_question_evidence_ledger, merge_question_evidence_ledgers

    channel_revenue = build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    support_pack = _pack(
        rows=[{"sales_owner": "张敏", "support_issue": "发货延迟", "ticket_count": 18}],
        columns=["sales_owner", "support_issue", "ticket_count"],
    )
    support_pack.task.resolved_question = "按销售负责人和问题类型查看客服压力"
    support_pack.task.metrics = ["工单数"]
    support_pack.task.dimensions = ["销售负责人", "问题类型"]
    support_pack.task.business_lens = {
        "business_domain": "support_pressure",
        "metrics": [{"label": "工单数", "source_table": "support_tickets", "source_field": "ticket_id"}],
        "dimensions": [
            {"label": "销售负责人", "source_table": "support_tickets", "source_field": "sales_owner"},
            {"label": "问题类型", "source_table": "support_tickets", "source_field": "support_issue"},
        ],
        "time_policy_note": "客服压力按工单创建日期统计，时间范围为最近90天。",
    }
    support = build_question_evidence_ledger(question_evidence_pack=support_pack, task_id="support_by_owner_issue")

    merged = merge_question_evidence_ledgers([channel_revenue, support])
    group_sources = {
        group["group_id"]: (
            tuple(group["source"]["tables"]),
            tuple(metric["source_column"] for metric in group["metrics"]),
            group["row_grain"],
        )
        for group in merged["evidence_groups"]
    }

    assert set(group_sources) == {"group_revenue_by_channel", "group_support_by_owner_issue"}
    assert group_sources["group_revenue_by_channel"] == (("orders",), ("total_revenue",), "渠道")
    assert group_sources["group_support_by_owner_issue"] == (
        ("support_tickets",),
        ("ticket_count",),
        "销售负责人 / 问题类型",
    )


def test_grouped_answer_projection_is_primary_and_hides_rows_sql_provider_task_internals():
    import workspaces.question_evidence_ledger as qel

    ledger = qel.build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    ledger["data_limits"].append(
        "证据任务 revenue_by_channel 失败：SELECT * FROM orders trace_path=/tmp/ws/trace.json provider_metadata={'token':'sk-test'}"
    )

    answer_input = qel.build_answer_input_ledger(ledger)
    payload_text = str(answer_input)

    assert "evidence_groups" in answer_input
    assert "facts" not in answer_input
    assert "derived_metrics" not in answer_input
    assert answer_input["evidence_groups"][0]["purpose"] == "关键事实"
    assert answer_input["evidence_groups"][0]["facts"][0]["label"] == "收入"
    assert answer_input["evidence_groups"][0]["facts"][0]["business_object"] == "私域社群"
    assert answer_input["evidence_groups"][0]["facts"][0]["fact_text"] == "私域社群的收入为300000.0元。"
    forbidden = (
        "task_id",
        "task_purpose",
        "source_row_refs",
        "source_columns",
        "ledger_id",
        "SELECT",
        "trace_path",
        "provider_metadata",
        "sk-test",
        "/tmp/ws",
    )
    for marker in forbidden:
        assert marker not in payload_text


def test_chart_candidate_uses_one_group_and_refuses_broad_mixed_groups():
    import workspaces.question_evidence_ledger as qel

    revenue = qel.build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    support_pack = _pack(
        rows=[{"sales_owner": "张敏", "support_issue": "发货延迟", "ticket_count": 18}],
        columns=["sales_owner", "support_issue", "ticket_count"],
    )
    support_pack.task.metrics = ["工单数"]
    support_pack.task.dimensions = ["销售负责人", "问题类型"]
    support_pack.task.business_lens = {
        "business_domain": "support_pressure",
        "metrics": [{"label": "工单数", "source_table": "support_tickets", "source_field": "ticket_id"}],
        "dimensions": [
            {"label": "销售负责人", "source_table": "support_tickets", "source_field": "sales_owner"},
            {"label": "问题类型", "source_table": "support_tickets", "source_field": "support_issue"},
        ],
    }
    support = qel.build_question_evidence_ledger(question_evidence_pack=support_pack, task_id="support_by_owner_issue")
    merged = qel.merge_question_evidence_ledgers([revenue, support])

    candidate = qel.build_grouped_chart_candidate(merged)

    assert candidate["success"] is False
    assert candidate["source"] == "question_evidence_ledger.evidence_groups"
    assert "不能在同一张图中混合" in candidate["reason"]
    assert candidate["rows"] == []


def test_chart_candidate_combines_same_dimension_same_grain_currency_metrics():
    import workspaces.question_evidence_ledger as qel

    revenue = qel.build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    spend_pack = _pack(
        rows=[
            {"channel": "私域社群", "total_spend": 30000.0},
            {"channel": "搜索广告", "total_spend": 80000.0},
        ],
        columns=["channel", "total_spend"],
    )
    spend_pack.task.resolved_question = "最近90天按渠道比较投放花费"
    spend_pack.task.metrics = ["投放花费"]
    spend_pack.task.business_lens["metrics"] = [
        {"label": "投放花费", "source_table": "marketing_spend", "source_field": "spend"}
    ]
    spend = qel.build_question_evidence_ledger(question_evidence_pack=spend_pack, task_id="spend_by_channel")
    merged = qel.merge_question_evidence_ledgers([revenue, spend])

    candidate = qel.build_grouped_chart_candidate(merged, question="最近90天各渠道投放花费和收入表现怎么样？")

    assert candidate["success"] is True
    assert candidate["chart_type"] == "grouped_bar"
    assert candidate["dimension_label"] == "渠道"
    assert candidate["metric_labels"] == ["收入", "投放花费"]
    assert candidate["unit"] == "元"
    assert candidate["columns"] == ["渠道", "指标", "金额"]
    assert ["私域社群", "收入", 300000.0] in candidate["rows"]
    assert ["私域社群", "投放花费", 30000.0] in candidate["rows"]
    assert candidate["chart_spec"]["title"] == "最近90天渠道收入与投放花费对比"
    assert candidate["chart_spec"]["series"] == "指标"
    assert candidate["chart_spec"]["y"] == "金额"


def test_chart_candidate_selects_currency_subset_when_roas_is_mixed_in():
    import workspaces.question_evidence_ledger as qel

    pack = _pack(
        rows=[
            {"channel": "私域社群", "total_revenue": 300000.0, "total_spend": 30000.0, "roas": 10.0},
            {"channel": "搜索广告", "total_revenue": 100000.0, "total_spend": 80000.0, "roas": 1.25},
        ],
        columns=["channel", "total_revenue", "total_spend", "roas"],
    )
    pack.task.metrics = ["收入", "投放金额", "ROAS"]
    pack.task.business_lens["metrics"] = [
        {"label": "收入", "source_table": "channel_performance", "source_field": "revenue"},
        {"label": "投放金额", "source_table": "channel_performance", "source_field": "spend"},
        {"label": "ROAS", "source_table": "channel_performance", "source_field": "roas"},
    ]

    ledger = qel.build_question_evidence_ledger(question_evidence_pack=pack, task_id="channel_efficiency")
    candidate = qel.build_grouped_chart_candidate(
        ledger,
        question="最近90天比较各渠道收入和投放金额，哪个渠道投放效率更值得关注？请生成图表。",
    )

    assert candidate["success"] is True
    assert candidate["chart_type"] == "grouped_bar"
    assert candidate["metric_labels"] == ["收入", "投放金额"]
    assert candidate["unit"] == "元"
    assert candidate["columns"] == ["渠道", "指标", "金额"]
    assert ["私域社群", "收入", 300000.0] in candidate["rows"]
    assert ["私域社群", "投放金额", 30000.0] in candidate["rows"]
    assert all(row[1] != "ROAS" for row in candidate["rows"])
    assert candidate["chart_spec"]["metric_units"] == {"收入": "元", "投放金额": "元"}
    assert "ROAS" not in candidate["chart_spec"]["y"]


def test_chart_candidate_uses_scatter_for_two_incompatible_units_with_same_dimension():
    import workspaces.question_evidence_ledger as qel

    revenue = qel.build_question_evidence_ledger(question_evidence_pack=_pack(), task_id="revenue_by_channel")
    roi_pack = _pack(
        rows=[
            {"channel": "私域社群", "roi": 6.0},
            {"channel": "搜索广告", "roi": 1.5},
        ],
        columns=["channel", "roi"],
    )
    roi_pack.task.metrics = ["ROI"]
    roi_pack.task.business_lens["metrics"] = [{"label": "ROI", "source_table": "channel_performance", "source_field": "roi"}]
    roi = qel.build_question_evidence_ledger(question_evidence_pack=roi_pack, task_id="roi_by_channel")
    merged = qel.merge_question_evidence_ledgers([revenue, roi])

    candidate = qel.build_grouped_chart_candidate(merged, question="最近90天按渠道比较收入和 ROI")

    assert candidate["success"] is True
    assert candidate["chart_type"] == "scatter"
    assert candidate["columns"] == ["渠道", "收入", "ROI"]
    assert ["私域社群", 300000.0, 6.0] in candidate["rows"]
    assert candidate["chart_spec"]["x"] == "收入"
    assert candidate["chart_spec"]["y"] == "ROI"
    assert candidate["chart_spec"]["label"] == "渠道"


def test_chart_candidate_uses_scatter_for_two_metric_groups_and_excludes_derived_metrics():
    import workspaces.question_evidence_ledger as qel

    pack = _pack(
        rows=[
            {"store_name": "上海旗舰店", "total_sales": 300000.0, "satisfaction_score": 4.8},
            {"store_name": "北京国贸店", "total_sales": 100000.0, "satisfaction_score": 4.3},
        ],
        columns=["store_name", "total_sales", "satisfaction_score"],
    )
    pack.task.metrics = ["销售额", "满意度"]
    pack.task.dimensions = ["门店"]
    pack.task.business_lens = {
        "business_domain": "store_operations",
        "metrics": [
            {"label": "销售额", "source_table": "store_sales", "source_field": "sales_amount"},
            {"label": "满意度", "source_table": "store_sales", "source_field": "satisfaction_score"},
        ],
        "dimensions": [{"label": "门店", "source_table": "store_sales", "source_field": "store_name"}],
    }

    ledger = qel.build_question_evidence_ledger(question_evidence_pack=pack, task_id="store_compare")
    candidate = qel.build_grouped_chart_candidate(ledger, question="比较各门店销售额和满意度")

    assert candidate["success"] is True
    assert candidate["chart_type"] == "scatter"
    assert candidate["columns"] == ["门店", "销售额", "满意度"]
    assert ["上海旗舰店", 300000.0, 4.8] in candidate["rows"]
    assert "占比" not in str(candidate)
    assert "排名" not in str(candidate)


def test_chart_candidate_rejects_three_or_more_metrics_without_comparable_units():
    import workspaces.question_evidence_ledger as qel

    pack = _pack(
        rows=[
            {"store_name": "上海旗舰店", "total_sales": 300000.0, "margin_rate": 0.41, "satisfaction_score": 4.8},
            {"store_name": "北京国贸店", "total_sales": 100000.0, "margin_rate": 0.36, "satisfaction_score": 4.3},
        ],
        columns=["store_name", "total_sales", "margin_rate", "satisfaction_score"],
    )
    pack.task.metrics = ["销售额", "毛利率", "满意度"]
    pack.task.dimensions = ["门店"]
    pack.task.business_lens = {
        "business_domain": "store_operations",
        "metrics": [
            {"label": "销售额", "source_table": "store_sales", "source_field": "sales_amount"},
            {"label": "毛利率", "source_table": "store_sales", "source_field": "margin_rate"},
            {"label": "满意度", "source_table": "store_sales", "source_field": "satisfaction_score"},
        ],
        "dimensions": [{"label": "门店", "source_table": "store_sales", "source_field": "store_name"}],
    }

    ledger = qel.build_question_evidence_ledger(question_evidence_pack=pack, task_id="store_review")
    candidate = qel.build_grouped_chart_candidate(ledger, question="结合销售额、毛利率和满意度比较门店")

    assert candidate["success"] is False
    assert "单位" in candidate["reason"]
    assert candidate["rows"] == []
