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
