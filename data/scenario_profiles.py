SCENARIO_PROFILES = [
    {
        "id": "cameras_gmv_decline_stockout_refunds",
        "title": "Cameras GMV decline linked to stockout and refund pressure",
        "question_examples": [
            "Cameras 品类 GMV 为什么下滑？",
            "Cameras 是否受到缺货和退款影响？",
        ],
        "tables": ["orders", "order_items", "products", "categories", "stockout_events", "refund_requests"],
        "validation_sql": """
            SELECT category_name, COUNT(*) AS refund_requests
            FROM refund_requests
            WHERE category_name = 'Cameras'
            GROUP BY category_name
        """,
    },
    {
        "id": "paid_search_high_gmv_low_roi",
        "title": "Paid search GMV remains high while ROI declines",
        "question_examples": [
            "Paid Search GMV 很高但 ROI 变差了吗？",
            "付费搜索投放效率为什么下降？",
        ],
        "tables": ["marketing_campaigns", "campaign_daily_metrics"],
        "validation_sql": """
            SELECT metric_date, attributed_gmv / spend AS roi
            FROM campaign_daily_metrics cdm
            JOIN marketing_campaigns mc ON cdm.campaign_id = mc.id
            WHERE mc.channel = 'Paid Search'
        """,
    },
    {
        "id": "promotion_orders_up_aov_down",
        "title": "Promotion increases order count but lowers AOV and net GMV quality",
        "question_examples": [
            "618 促销是否拉低客单价？",
            "促销订单上涨但净 GMV 质量是否下降？",
        ],
        "tables": ["promotion_events", "campaign_daily_metrics", "pricing_events"],
        "validation_sql": """
            SELECT metric_date, attributed_orders, attributed_gmv / attributed_orders AS aov, net_gmv
            FROM campaign_daily_metrics
            WHERE promotion_id = 1
        """,
    },
    {
        "id": "high_gmv_negative_reviews_refunds",
        "title": "High-GMV product carries negative review and refund risk",
        "question_examples": [
            "高 GMV 商品是否有负面评价和退款风险？",
            "Mirrorless Camera A 的售后风险如何？",
        ],
        "tables": ["orders", "order_items", "product_reviews", "refund_requests"],
        "validation_sql": """
            SELECT product_id, COUNT(*) AS negative_reviews
            FROM product_reviews
            WHERE sentiment = 'negative'
            GROUP BY product_id
        """,
    },
    {
        "id": "city_checkout_conversion_drop",
        "title": "City-level conversion falls because checkout conversion drops",
        "question_examples": [
            "上海转化率为什么下降？",
            "城市 sessions 稳定但 checkout conversion 是否下降？",
        ],
        "tables": ["traffic_sessions"],
        "validation_sql": """
            SELECT city, session_date, sessions, checkout_starts, paid_orders
            FROM traffic_sessions
            WHERE city = 'Shanghai'
        """,
    },
]
