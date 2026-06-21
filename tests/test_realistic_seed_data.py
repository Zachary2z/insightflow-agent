import sqlite3


REALISTIC_TABLES = {
    "marketing_campaigns": 4,
    "campaign_daily_metrics": 16,
    "traffic_sessions": 20,
    "inventory_snapshots": 16,
    "stockout_events": 3,
    "refund_requests": 12,
    "product_reviews": 24,
    "pricing_events": 5,
    "promotion_events": 3,
    "fulfillment_events": 12,
}


def seed_tmp_database(tmp_path):
    from data.seed_data import seed_database

    db_path = tmp_path / "ecommerce.db"
    result = seed_database(db_path)
    assert result["success"] is True
    return db_path


def fetch_one(db_path, sql, params=()):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, params).fetchone()


def test_realistic_scenario_profiles_are_registered():
    from data.scenario_profiles import SCENARIO_PROFILES

    profile_ids = {profile["id"] for profile in SCENARIO_PROFILES}

    assert profile_ids == {
        "cameras_gmv_decline_stockout_refunds",
        "paid_search_high_gmv_low_roi",
        "promotion_orders_up_aov_down",
        "high_gmv_negative_reviews_refunds",
        "city_checkout_conversion_drop",
    }
    assert all(profile["validation_sql"].strip().lower().startswith("select") for profile in SCENARIO_PROFILES)


def test_seed_database_creates_realistic_scenario_tables_with_stable_counts(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    with sqlite3.connect(db_path) as conn:
        counts = {
            table_name: conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            for table_name in REALISTIC_TABLES
        }

    assert counts == REALISTIC_TABLES


def test_cameras_gmv_decline_is_queryable_with_stockout_and_refund_increase(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    row = fetch_one(
        db_path,
        """
        WITH category_daily AS (
            SELECT
                o.order_date,
                SUM(oi.quantity * oi.unit_price) AS gmv
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE o.status = 'paid'
              AND c.category_name = 'Cameras'
              AND o.order_date IN ('2026-06-05', '2026-06-15')
            GROUP BY o.order_date
        ),
        refund_daily AS (
            SELECT request_date, COUNT(*) AS refund_requests
            FROM refund_requests
            WHERE category_name = 'Cameras'
              AND request_date IN ('2026-06-05', '2026-06-15')
            GROUP BY request_date
        ),
        stockout_daily AS (
            SELECT COUNT(*) AS stockout_events
            FROM stockout_events
            WHERE category_name = 'Cameras'
              AND start_date <= '2026-06-15'
              AND end_date >= '2026-06-15'
        )
        SELECT
            pre.gmv AS pre_gmv,
            post.gmv AS post_gmv,
            pre_refunds.refund_requests AS pre_refunds,
            post_refunds.refund_requests AS post_refunds,
            stockout_daily.stockout_events AS stockout_events
        FROM category_daily pre
        JOIN category_daily post ON post.order_date = '2026-06-15'
        JOIN refund_daily pre_refunds ON pre_refunds.request_date = '2026-06-05'
        JOIN refund_daily post_refunds ON post_refunds.request_date = '2026-06-15'
        CROSS JOIN stockout_daily
        WHERE pre.order_date = '2026-06-05'
        """,
    )

    assert row["post_gmv"] < row["pre_gmv"]
    assert row["post_refunds"] > row["pre_refunds"]
    assert row["stockout_events"] >= 1


def test_paid_search_has_high_gmv_but_roi_declines_after_spend_increase(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    row = fetch_one(
        db_path,
        """
        SELECT
            SUM(CASE WHEN metric_date = '2026-06-05' THEN attributed_gmv END) AS pre_gmv,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN attributed_gmv END) AS post_gmv,
            SUM(CASE WHEN metric_date = '2026-06-05' THEN attributed_gmv / spend END) AS pre_roi,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN attributed_gmv / spend END) AS post_roi,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN spend END) AS post_spend
        FROM campaign_daily_metrics cdm
        JOIN marketing_campaigns mc ON cdm.campaign_id = mc.id
        WHERE mc.channel = 'Paid Search'
          AND metric_date IN ('2026-06-05', '2026-06-15')
        """,
    )

    assert row["post_gmv"] > row["pre_gmv"]
    assert row["post_spend"] >= 20000
    assert row["post_roi"] < row["pre_roi"]


def test_promotion_increases_orders_but_lowers_aov_and_net_gmv_quality(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    row = fetch_one(
        db_path,
        """
        SELECT
            SUM(CASE WHEN metric_date = '2026-06-05' THEN attributed_orders END) AS baseline_orders,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN attributed_orders END) AS promo_orders,
            SUM(CASE WHEN metric_date = '2026-06-05' THEN attributed_gmv / attributed_orders END) AS baseline_aov,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN attributed_gmv / attributed_orders END) AS promo_aov,
            SUM(CASE WHEN metric_date = '2026-06-05' THEN net_gmv END) AS baseline_net_gmv,
            SUM(CASE WHEN metric_date = '2026-06-15' THEN net_gmv END) AS promo_net_gmv
        FROM campaign_daily_metrics cdm
        JOIN promotion_events pe ON cdm.promotion_id = pe.id
        WHERE pe.promotion_name = '618 Bundle Flash Sale'
          AND metric_date IN ('2026-06-05', '2026-06-15')
        """,
    )

    assert row["promo_orders"] > row["baseline_orders"]
    assert row["promo_aov"] < row["baseline_aov"]
    assert row["promo_net_gmv"] < row["baseline_net_gmv"]


def test_high_gmv_product_has_negative_reviews_and_refund_risk(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    row = fetch_one(
        db_path,
        """
        WITH product_gmv AS (
            SELECT p.id AS product_id, p.product_name, SUM(oi.quantity * oi.unit_price) AS gmv
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.status = 'paid'
            GROUP BY p.id, p.product_name
        ),
        review_risk AS (
            SELECT
                product_id,
                AVG(CASE WHEN sentiment = 'negative' THEN 1.0 ELSE 0.0 END) AS negative_review_rate
            FROM product_reviews
            GROUP BY product_id
        ),
        refund_risk AS (
            SELECT product_id, COUNT(*) AS refund_requests
            FROM refund_requests
            GROUP BY product_id
        )
        SELECT product_gmv.product_name, gmv, negative_review_rate, refund_requests
        FROM product_gmv
        JOIN review_risk ON product_gmv.product_id = review_risk.product_id
        JOIN refund_risk ON product_gmv.product_id = refund_risk.product_id
        WHERE product_gmv.product_name = 'Mirrorless Camera A'
        """,
    )

    assert row["gmv"] >= 50000
    assert row["negative_review_rate"] >= 0.5
    assert row["refund_requests"] >= 4


def test_city_conversion_declines_with_stable_sessions_and_lower_checkout_conversion(tmp_path):
    db_path = seed_tmp_database(tmp_path)

    row = fetch_one(
        db_path,
        """
        SELECT
            SUM(CASE WHEN session_date = '2026-06-05' THEN sessions END) AS pre_sessions,
            SUM(CASE WHEN session_date = '2026-06-15' THEN sessions END) AS post_sessions,
            SUM(CASE WHEN session_date = '2026-06-05' THEN checkout_starts END) * 1.0
                / SUM(CASE WHEN session_date = '2026-06-05' THEN add_to_carts END) AS pre_checkout_conversion,
            SUM(CASE WHEN session_date = '2026-06-15' THEN checkout_starts END) * 1.0
                / SUM(CASE WHEN session_date = '2026-06-15' THEN add_to_carts END) AS post_checkout_conversion,
            SUM(CASE WHEN session_date = '2026-06-05' THEN paid_orders END) * 1.0
                / SUM(CASE WHEN session_date = '2026-06-05' THEN sessions END) AS pre_conversion,
            SUM(CASE WHEN session_date = '2026-06-15' THEN paid_orders END) * 1.0
                / SUM(CASE WHEN session_date = '2026-06-15' THEN sessions END) AS post_conversion
        FROM traffic_sessions
        WHERE city = 'Shanghai'
          AND session_date IN ('2026-06-05', '2026-06-15')
        """,
    )

    session_delta = abs(row["post_sessions"] - row["pre_sessions"]) / row["pre_sessions"]

    assert session_delta <= 0.05
    assert row["post_checkout_conversion"] < row["pre_checkout_conversion"]
    assert row["post_conversion"] < row["pre_conversion"]
