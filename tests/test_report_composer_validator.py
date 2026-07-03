import json

from llm_ops.provider import MockLLMProvider
from workspaces.report_composer import compose_report_document
from workspaces.report_models import (
    EvidenceRequirement,
    ReportChapterPlan,
    ReportDocument,
    ReportDocumentSection,
    ReportEvidenceFact,
    ReportEvidencePack,
    ReportEvidenceTable,
    ReportPlan,
)
from workspaces.report_validator import validate_report_document


def _sample_plan() -> ReportPlan:
    return ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["订单明细", "客服反馈"],
        chapters=[
            ReportChapterPlan(
                chapter_id="overview",
                title="经营概览",
                purpose="说明整体经营表现。",
                evidence_requirements=[
                    EvidenceRequirement(
                        requirement_id="workspace_overview",
                        chapter_id="overview",
                        description="梳理当前工作区数据来源。",
                    )
                ],
            ),
            ReportChapterPlan(
                chapter_id="revenue_structure",
                title="收入结构",
                purpose="说明收入来源和集中度。",
                evidence_requirements=[],
            ),
            ReportChapterPlan(
                chapter_id="customer_segments",
                title="客户分群",
                purpose="说明客户分群贡献。",
                evidence_requirements=[],
            ),
            ReportChapterPlan(
                chapter_id="actions",
                title="行动建议",
                purpose="形成下一步行动。",
                evidence_requirements=[],
            ),
        ],
    )


def _sample_evidence_pack() -> ReportEvidencePack:
    return ReportEvidencePack(
        facts=[
            ReportEvidenceFact(
                fact_id="workspace_table_count",
                label="可用数据表数量",
                value=2,
                display_value="2",
                source_chapter_id="overview",
                evidence_ref="workspace_profile",
            ),
            ReportEvidenceFact(
                fact_id="revenue_total",
                label="总收入",
                value=430000,
                display_value="43.0 万",
                source_chapter_id="revenue_structure",
                evidence_ref="query_revenue_total",
                unit="currency",
            ),
        ],
        tables=[
            ReportEvidenceTable(
                table_id="revenue_by_dimension",
                title="收入结构",
                columns=["产品", "收入"],
                rows=[
                    {"产品": "企业SaaS订阅", "收入": "26.8 万"},
                    {"产品": "数据分析服务", "收入": "8.6 万"},
                ],
                source_chapter_id="revenue_structure",
                description="证据来自订单明细按产品汇总。",
                evidence_ref="query_revenue_by_dimension",
            ),
            ReportEvidenceTable(
                table_id="customer_segment_contribution",
                title="客户分群贡献",
                columns=["客户分群", "收入"],
                rows=[
                    {"客户分群": "成长型团队", "收入": "19.6 万"},
                    {"客户分群": "高价值企业", "收入": "14.8 万"},
                ],
                source_chapter_id="customer_segments",
                description="证据来自订单明细按客户分群汇总。",
                evidence_ref="query_customer_segment_contribution",
            ),
        ],
        data_limits=["当前缺少利润、复购率和销售人效数据。"],
        technical_details={
            "queries": [
                {
                    "sql": "SELECT product_category, SUM(revenue) FROM orders GROUP BY product_category",
                    "execution": {"rows": [["企业SaaS订阅", 268000]]},
                }
            ]
        },
    )


def _share_evidence_pack() -> ReportEvidencePack:
    return ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_revenue",
                title="渠道收入结构",
                columns=["渠道", "收入"],
                rows=[
                    {"渠道": "email", "收入": "26.8 万"},
                    {"渠道": "direct", "收入": "18.6 万"},
                    {"渠道": "organic", "收入": "15.5 万"},
                    {"渠道": "其他渠道", "收入": "39.1 万"},
                ],
                source_chapter_id="revenue_structure",
                description="证据来自订单表按渠道汇总。",
                evidence_ref="query_channel_revenue",
            )
        ]
    )


def _monthly_trend_evidence_pack() -> ReportEvidencePack:
    return ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="recent_trend",
                title="趋势变化",
                columns=["周期", "收入"],
                rows=[
                    {"周期": "2026-04", "收入": "26.8 万"},
                    {"周期": "2026-05", "收入": "18.6 万"},
                    {"周期": "2026-06", "收入": "15.5 万"},
                ],
                source_chapter_id="trend_changes",
                description="证据来自订单表按月份汇总。",
                evidence_ref="query_recent_trend",
            )
        ]
    )


def _document_text(document: ReportDocument) -> str:
    return json.dumps(
        {
            "opening_summary": document.opening_summary,
            "sections": [section.to_dict() for section in document.sections],
            "action_recommendations": document.action_recommendations,
            "data_boundaries": document.data_boundaries,
        },
        ensure_ascii=False,
    )


def test_model_backed_report_composer_uses_provider_json_without_leaking_technical_details():
    provider = MockLLMProvider(
        {
            "title": "最近90天经营复盘报告",
            "time_range": "最近90天",
            "data_sources": ["订单明细", "客服反馈"],
            "opening_summary": "最近90天总收入为 43.0 万，企业SaaS订阅是收入最高的产品，成长型团队是收入最高的客户分群。",
            "sections": [
                {
                    "section_id": "overview",
                    "title": "经营概览",
                    "body": "本报告基于订单明细和客服反馈生成，当前可识别总收入为 43.0 万。",
                    "evidence_refs": ["workspace_table_count", "revenue_total"],
                },
                {
                    "section_id": "revenue_structure",
                    "title": "收入结构",
                    "body": "企业SaaS订阅收入为 26.8 万，位居产品收入第一。",
                    "evidence_refs": ["revenue_by_dimension"],
                },
                {
                    "section_id": "customer_segments",
                    "title": "客户分群",
                    "body": "成长型团队收入为 19.6 万，是当前贡献最高的客户分群。",
                    "evidence_refs": ["customer_segment_contribution"],
                },
            ],
            "action_recommendations": ["建议优先关注收入最高的客户分群，并补齐利润与复购证据。"],
            "data_boundaries": ["当前缺少利润、复购率和销售人效数据。"],
        }
    )

    document = compose_report_document(
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
        provider=provider,
    )

    text = _document_text(document)
    assert document.opening_summary.startswith("最近90天总收入")
    assert "企业SaaS订阅" in text
    assert "成长型团队" in text
    for forbidden in [
        "SELECT",
        "query_revenue",
        "raw rows",
        "raw_rows",
        "technical_details",
        "provider_metadata",
        "直接回答",
        "为什么",
        "置信度",
        "章节业务答案",
    ]:
        assert forbidden not in text
    assert provider.generate  # keeps the fake provider path explicit for this test


def test_report_composer_no_key_fallback_returns_chinese_report_document():
    document = compose_report_document(
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
        provider=None,
    )

    text = _document_text(document)
    assert document.title == "最近90天经营复盘报告"
    assert document.time_range == "最近90天"
    assert document.sections
    assert "43.0 万" in text
    assert "企业SaaS订阅" in text
    assert "行动建议" not in [section.title for section in document.sections]
    assert document.action_recommendations
    assert "直接回答" not in text
    assert "为什么" not in text
    assert "置信度" not in text


def test_report_composer_filters_duplicate_action_sections_from_provider_output():
    provider = MockLLMProvider(
        {
            "title": "最近90天经营复盘报告",
            "time_range": "最近90天",
            "data_sources": ["订单明细", "客服反馈"],
            "opening_summary": "最近90天总收入为 43.0 万。",
            "sections": [
                {
                    "section_id": "revenue_structure",
                    "title": "收入结构",
                    "body": "企业SaaS订阅收入为 26.8 万，位居产品收入第一。",
                    "evidence_refs": ["revenue_by_dimension"],
                },
                {
                    "section_id": "actions",
                    "title": "行动建议",
                    "body": "建议优先复盘高收入来源。",
                    "evidence_refs": ["revenue_by_dimension"],
                },
            ],
            "action_recommendations": ["建议优先复盘高收入来源。"],
            "data_boundaries": ["当前缺少利润、复购率和销售人效数据。"],
        }
    )

    document = compose_report_document(
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
        provider=provider,
    )

    assert [section.title for section in document.sections] == ["收入结构"]
    assert document.action_recommendations == ["建议优先复盘高收入来源。"]


def test_report_composer_keeps_plan_time_range_when_provider_describes_data_months():
    provider = MockLLMProvider(
        {
            "title": "最近90天经营复盘报告",
            "time_range": "2026年4月至2026年6月",
            "data_sources": ["订单明细", "客服反馈"],
            "opening_summary": "最近90天报告覆盖当前数据中的 2026年4月至6月 业务表现。",
            "sections": [
                {
                    "section_id": "trend_changes",
                    "title": "趋势变化",
                    "body": "当前证据表显示 2026年4月至6月 有连续月度收入记录。",
                    "evidence_refs": ["recent_trend"],
                }
            ],
            "action_recommendations": ["继续观察月度趋势变化。"],
            "data_boundaries": [],
        }
    )

    document = compose_report_document(
        plan=_sample_plan(),
        evidence_pack=_monthly_trend_evidence_pack(),
        provider=provider,
    )

    assert document.time_range == "最近90天"
    assert "2026年4月至6月" in _document_text(document)


def test_report_validator_flags_conflicting_top_ranked_entity():
    document = ReportDocument(
        title="最近90天经营复盘报告",
        time_range="最近90天",
        data_sources=["订单明细"],
        opening_summary="数据分析服务是收入最高的产品。",
        sections=[
            ReportDocumentSection(
                section_id="revenue_structure",
                title="收入结构",
                body="数据分析服务收入排名第一。",
                evidence_refs=["revenue_by_dimension"],
            )
        ],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
    )

    assert validation.status == "warning"
    assert any("收入结构" in claim and "企业SaaS订阅" in claim for claim in validation.unsupported_claims)


def test_report_validator_accepts_percentages_derived_from_same_evidence_table():
    plan = ReportPlan(
        title="最近90天渠道表现复盘报告",
        report_style="渠道表现复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="email、direct、organic 分别贡献 26.8%、18.6%、15.5%。",
        sections=[
            ReportDocumentSection(
                section_id="revenue_structure",
                title="渠道收入结构",
                body="email 占比 26.8%，direct 占比 18.6%，organic 占比 15.5%。",
                evidence_refs=["channel_revenue"],
            )
        ],
        action_recommendations=["优先复盘 email 的承接能力。"],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=_share_evidence_pack(),
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_accepts_shared_payload_percentages_and_currency_unit_forms():
    plan = ReportPlan(
        title="最近90天渠道表现复盘报告",
        report_style="渠道表现复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="channel_revenue",
                title="渠道收入结构",
                columns=["渠道", "收入"],
                rows=[{"渠道": "email", "收入": "4.5 万"}],
                source_chapter_id="revenue_structure",
                evidence_ref="query_channel_revenue",
            )
        ],
        evidence_payloads=[
            {
                "evidence_ref": "query_channel_revenue",
                "result_rows": [
                    {
                        "dimensions": [{"display_value": "email"}],
                        "metrics": [{"display_value": "4.5 万"}],
                    }
                ],
                "derived_metrics": [
                    {
                        "metric_id": "revenue_share",
                        "values": [{"display_value": "24.8%", "value": 24.8}],
                    }
                ],
            }
        ],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="email 收入为 4.5万元，占比 24.8%。",
        sections=[
            ReportDocumentSection(
                section_id="revenue_structure",
                title="渠道收入结构",
                body="email 收入 4.5万元，贡献 24.8%。",
                evidence_refs=["channel_revenue"],
            )
        ],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_accepts_percentages_derived_from_chapter_total_fact():
    plan = ReportPlan(
        title="最近90天渠道表现复盘报告",
        report_style="渠道表现复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    evidence_pack = ReportEvidencePack(
        facts=[
            ReportEvidenceFact(
                fact_id="revenue_total",
                label="总收入",
                value=181406.39,
                display_value="18.1 万",
                source_chapter_id="revenue_structure",
                evidence_ref="query_revenue_total",
            )
        ],
        tables=[
            ReportEvidenceTable(
                table_id="channel_revenue",
                title="渠道收入结构",
                columns=["渠道", "收入"],
                rows=[
                    {"渠道": "direct", "收入": "3.7 万"},
                    {"渠道": "partner", "收入": "3.2 万"},
                ],
                source_chapter_id="revenue_structure",
                evidence_ref="query_channel_revenue",
            )
        ],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="direct 收入 3.7万元，占比 20.4%；partner 收入 3.2万元，占比 17.7%。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_accepts_date_numbers_in_evidence_backed_month_ranges():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="当前证据覆盖 2026 年 4 月至 6 月 的月度收入表现。",
        sections=[
            ReportDocumentSection(
                section_id="trend_changes",
                title="趋势变化",
                body="趋势表包含 2026-04、2026-05 和 2026-06，正文可写作 2026年4月至6月。",
                evidence_refs=["recent_trend"],
            )
        ],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=_monthly_trend_evidence_pack(),
    )

    assert validation.status == "passed"
    assert not any("2026" in claim for claim in validation.unsupported_claims)


def test_report_validator_still_flags_unsupported_large_business_numbers():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="当前证据覆盖 2026年4月至6月，但不能证明新增 2026 单订单。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=_monthly_trend_evidence_pack(),
    )

    assert validation.status == "warning"
    assert any("2026单" in claim or "2026 单" in claim for claim in validation.unsupported_claims)


def test_report_validator_accepts_table_column_unit_forms():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["当前工作区数据"],
        chapters=[],
    )
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="workspace_overview",
                title="当前工作区数据概览",
                columns=["数据表", "行数", "字段数"],
                rows=[
                    {"数据表": "customers", "行数": 100, "字段数": 4},
                    {"数据表": "orders", "行数": 1200, "字段数": 6},
                ],
                source_chapter_id="overview",
                evidence_ref="workspace_profile",
            )
        ]
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="customers 有 100 行、4 字段；orders 有 1200 行、6 字段。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_accepts_currency_conversions_from_metric_columns():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    evidence_pack = ReportEvidencePack(
        tables=[
            ReportEvidenceTable(
                table_id="recent_trend",
                title="趋势变化",
                columns=["周期", "收入"],
                rows=[{"周期": "2025-09", "收入": "7678.03"}],
                source_chapter_id="trend_changes",
                evidence_ref="query_recent_trend",
            )
        ]
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="2025年9月为低谷，收入约 0.77万，也可写作 7678元。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_still_flags_underived_percentages():
    plan = ReportPlan(
        title="最近90天渠道表现复盘报告",
        report_style="渠道表现复盘",
        time_range="最近90天",
        data_sources=["订单明细"],
        chapters=[],
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="email 贡献 99.9%。",
        sections=[
            ReportDocumentSection(
                section_id="revenue_structure",
                title="渠道收入结构",
                body="email 占比 99.9%。",
                evidence_refs=["channel_revenue"],
            )
        ],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=_share_evidence_pack(),
    )

    assert validation.status == "warning"
    assert any("99.9%" in claim for claim in validation.unsupported_claims)


def test_report_validator_allows_reasonable_evidence_backed_recommendation():
    document = ReportDocument(
        title="最近90天经营复盘报告",
        time_range="最近90天",
        data_sources=["订单明细", "客服反馈"],
        opening_summary="最近90天总收入为 43.0 万。",
        sections=[
            ReportDocumentSection(
                section_id="customer_segments",
                title="客户分群",
                body="成长型团队收入为 19.6 万，是当前贡献最高的客户分群。",
                evidence_refs=["customer_segment_contribution"],
            )
        ],
        action_recommendations=["建议优先关注收入最高的客户分群。"],
        data_boundaries=["当前缺少利润、复购率和销售人效数据。"],
    )

    validation = validate_report_document(
        document=document,
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_accepts_workspace_profile_numbers_with_chinese_units():
    plan = ReportPlan(
        title="最近90天经营复盘报告",
        report_style="经营复盘",
        time_range="最近90天",
        data_sources=["当前工作区数据"],
        chapters=[],
    )
    evidence_pack = ReportEvidencePack(
        facts=[
            ReportEvidenceFact(
                fact_id="workspace_table_count",
                label="可用数据表数量",
                value=4,
                display_value="4",
                source_chapter_id="overview",
                evidence_ref="workspace_profile",
            ),
            ReportEvidenceFact(
                fact_id="workspace_row_count",
                label="可用数据行数",
                value=3506,
                display_value="3506",
                source_chapter_id="overview",
                evidence_ref="workspace_profile",
            ),
            ReportEvidenceFact(
                fact_id="workspace_field_count",
                label="可用字段数量",
                value=35,
                display_value="35",
                source_chapter_id="overview",
                evidence_ref="workspace_profile",
            ),
        ]
    )
    document = ReportDocument(
        title=plan.title,
        time_range=plan.time_range,
        data_sources=plan.data_sources,
        opening_summary="本报告基于当前工作区 4 张数据表、3506 行记录和 35 个字段生成。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=plan,
        evidence_pack=evidence_pack,
    )

    assert validation.status == "passed"
    assert validation.unsupported_claims == []


def test_report_validator_flags_unseen_key_numbers_and_data_sources():
    document = ReportDocument(
        title="最近30天经营复盘报告",
        time_range="最近30天",
        data_sources=["订单明细", "CRM外部画像"],
        opening_summary="最近30天总收入为 99.9 万。",
        sections=[],
        action_recommendations=[],
        data_boundaries=[],
    )

    validation = validate_report_document(
        document=document,
        plan=_sample_plan(),
        evidence_pack=_sample_evidence_pack(),
    )

    assert validation.status == "warning"
    assert any("标题" in item or "时间范围" in item for item in validation.warnings)
    assert any("99.9 万" in claim for claim in validation.unsupported_claims)
    assert any("CRM外部画像" in claim for claim in validation.unsupported_claims)
