from __future__ import annotations

import sqlite3


REALISTIC_TABLE_COUNTS = {
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

REALISTIC_TABLES = list(REALISTIC_TABLE_COUNTS)


def drop_realistic_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS fulfillment_events;
        DROP TABLE IF EXISTS pricing_events;
        DROP TABLE IF EXISTS product_reviews;
        DROP TABLE IF EXISTS refund_requests;
        DROP TABLE IF EXISTS stockout_events;
        DROP TABLE IF EXISTS inventory_snapshots;
        DROP TABLE IF EXISTS traffic_sessions;
        DROP TABLE IF EXISTS campaign_daily_metrics;
        DROP TABLE IF EXISTS promotion_events;
        DROP TABLE IF EXISTS marketing_campaigns;
        """
    )


def create_realistic_schema(conn: sqlite3.Connection) -> None:
    drop_realistic_tables(conn)
    conn.executescript(
        """
        CREATE TABLE marketing_campaigns (
            id INTEGER PRIMARY KEY,
            campaign_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            owner TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            objective TEXT NOT NULL
        );

        CREATE TABLE promotion_events (
            id INTEGER PRIMARY KEY,
            promotion_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            discount_type TEXT NOT NULL,
            target_scope TEXT NOT NULL,
            target_category_name TEXT,
            target_product_id INTEGER,
            expected_margin_impact REAL NOT NULL,
            FOREIGN KEY (target_product_id) REFERENCES products(id)
        );

        CREATE TABLE campaign_daily_metrics (
            id INTEGER PRIMARY KEY,
            campaign_id INTEGER NOT NULL,
            promotion_id INTEGER,
            metric_date TEXT NOT NULL,
            impressions INTEGER NOT NULL,
            clicks INTEGER NOT NULL,
            spend REAL NOT NULL,
            attributed_orders INTEGER NOT NULL,
            attributed_gmv REAL NOT NULL,
            net_gmv REAL NOT NULL,
            FOREIGN KEY (campaign_id) REFERENCES marketing_campaigns(id),
            FOREIGN KEY (promotion_id) REFERENCES promotion_events(id)
        );

        CREATE TABLE traffic_sessions (
            id INTEGER PRIMARY KEY,
            session_date TEXT NOT NULL,
            city TEXT NOT NULL,
            channel TEXT NOT NULL,
            landing_category_name TEXT NOT NULL,
            sessions INTEGER NOT NULL,
            add_to_carts INTEGER NOT NULL,
            checkout_starts INTEGER NOT NULL,
            paid_orders INTEGER NOT NULL
        );

        CREATE TABLE inventory_snapshots (
            id INTEGER PRIMARY KEY,
            snapshot_date TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category_name TEXT NOT NULL,
            available_quantity INTEGER NOT NULL,
            inbound_quantity INTEGER NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE stockout_events (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            lost_sales_estimate REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE refund_requests (
            id INTEGER PRIMARY KEY,
            request_date TEXT NOT NULL,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            refund_amount REAL NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('requested', 'approved', 'rejected')),
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE product_reviews (
            id INTEGER PRIMARY KEY,
            review_date TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            sentiment TEXT NOT NULL CHECK (sentiment IN ('positive', 'neutral', 'negative')),
            topic TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE pricing_events (
            id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            old_price REAL NOT NULL,
            new_price REAL NOT NULL,
            reason TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE fulfillment_events (
            id INTEGER PRIMARY KEY,
            event_date TEXT NOT NULL,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            city TEXT NOT NULL,
            delay_days INTEGER NOT NULL,
            delivery_status TEXT NOT NULL,
            issue_reason TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )


def _insert_scenario_orders(conn: sqlite3.Connection) -> None:
    orders = [
        (1001, 1, "2026-06-05", "paid", 26495.00),
        (1002, 2, "2026-06-05", "paid", 26495.00),
        (1003, 3, "2026-06-05", "paid", 12495.00),
        (1004, 4, "2026-06-15", "paid", 1899.00),
        (1005, 5, "2026-06-15", "paid", 2499.00),
        (1006, 6, "2026-06-15", "paid", 13980.00),
    ]
    order_items = [
        (10001, 1001, 1, 5, 5299.00),
        (10002, 1002, 1, 5, 5299.00),
        (10003, 1003, 3, 5, 2499.00),
        (10004, 1004, 2, 1, 1899.00),
        (10005, 1005, 3, 1, 2499.00),
        (10006, 1006, 20, 6, 2330.00),
    ]
    conn.executemany(
        """
        INSERT INTO orders (id, user_id, order_date, status, total_amount)
        VALUES (?, ?, ?, ?, ?)
        """,
        orders,
    )
    conn.executemany(
        """
        INSERT INTO order_items (id, order_id, product_id, quantity, unit_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        order_items,
    )


def _seed_campaigns(conn: sqlite3.Connection) -> None:
    campaigns = [
        (1, "Paid Search Growth Sprint", "Paid Search", "Growth", "2026-06-01", "2026-06-30", "Acquire high-intent buyers"),
        (2, "618 Bundle Flash Sale", "Promotion", "Merchandising", "2026-06-10", "2026-06-18", "Lift order count"),
        (3, "Lifecycle Email Recovery", "Email", "CRM", "2026-06-01", "2026-06-30", "Recover repeat buyers"),
        (4, "Organic Content Push", "Organic", "Content", "2026-06-01", "2026-06-30", "Improve assisted demand"),
    ]
    promotions = [
        (1, "618 Bundle Flash Sale", "2026-06-10", "2026-06-18", "bundle_discount", "category", "Home", None, -0.18),
        (2, "Camera Accessory Coupon", "2026-06-12", "2026-06-20", "coupon", "category", "Cameras", None, -0.08),
        (3, "Audio Member Day", "2026-06-08", "2026-06-09", "member_price", "category", "Audio", None, -0.05),
    ]
    metrics = [
        (1, 1, None, "2026-06-05", 180000, 9100, 9000.00, 122, 43200.00, 39100.00),
        (2, 1, None, "2026-06-10", 195000, 9800, 12000.00, 130, 45900.00, 40400.00),
        (3, 1, None, "2026-06-15", 260000, 13100, 22000.00, 150, 50600.00, 41000.00),
        (4, 1, None, "2026-06-20", 240000, 11900, 21000.00, 142, 48200.00, 39500.00),
        (5, 2, 1, "2026-06-05", 76000, 3900, 3000.00, 90, 31500.00, 29200.00),
        (6, 2, 1, "2026-06-10", 94000, 5600, 5200.00, 130, 37700.00, 30100.00),
        (7, 2, 1, "2026-06-15", 130000, 9200, 7800.00, 210, 46200.00, 24800.00),
        (8, 2, 1, "2026-06-20", 88000, 4100, 3600.00, 105, 28600.00, 23500.00),
        (9, 3, None, "2026-06-05", 42000, 2400, 1200.00, 58, 19800.00, 18800.00),
        (10, 3, None, "2026-06-10", 43000, 2500, 1300.00, 61, 20500.00, 19300.00),
        (11, 3, None, "2026-06-15", 45000, 2550, 1400.00, 60, 20100.00, 18700.00),
        (12, 3, None, "2026-06-20", 46000, 2600, 1500.00, 63, 21000.00, 19500.00),
        (13, 4, None, "2026-06-05", 90000, 3200, 600.00, 44, 14200.00, 13900.00),
        (14, 4, None, "2026-06-10", 94000, 3400, 650.00, 46, 15000.00, 14600.00),
        (15, 4, None, "2026-06-15", 98000, 3600, 700.00, 47, 15100.00, 14700.00),
        (16, 4, None, "2026-06-20", 101000, 3700, 720.00, 49, 15800.00, 15400.00),
    ]
    conn.executemany(
        """
        INSERT INTO marketing_campaigns
            (id, campaign_name, channel, owner, start_date, end_date, objective)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        campaigns,
    )
    conn.executemany(
        """
        INSERT INTO promotion_events
            (id, promotion_name, start_date, end_date, discount_type, target_scope,
             target_category_name, target_product_id, expected_margin_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        promotions,
    )
    conn.executemany(
        """
        INSERT INTO campaign_daily_metrics
            (id, campaign_id, promotion_id, metric_date, impressions, clicks, spend,
             attributed_orders, attributed_gmv, net_gmv)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        metrics,
    )


def _seed_traffic(conn: sqlite3.Connection) -> None:
    rows = []
    row_id = 1
    city_values = {
        "Shanghai": [(4200, 980, 610, 290), (4300, 970, 585, 275), (4270, 940, 390, 170), (4220, 930, 360, 155)],
        "Beijing": [(3500, 730, 430, 205), (3520, 740, 435, 210), (3540, 735, 430, 208), (3560, 745, 438, 212)],
        "Shenzhen": [(2800, 620, 360, 174), (2850, 630, 370, 178), (2820, 628, 365, 176), (2870, 635, 372, 180)],
        "Guangzhou": [(2600, 540, 320, 150), (2620, 548, 322, 152), (2650, 552, 325, 153), (2660, 555, 328, 155)],
        "Hangzhou": [(2200, 470, 282, 132), (2220, 475, 286, 135), (2230, 476, 284, 134), (2250, 480, 288, 136)],
    }
    dates = ["2026-06-05", "2026-06-10", "2026-06-15", "2026-06-20"]
    for city, metrics in city_values.items():
        for session_date, values in zip(dates, metrics):
            sessions, add_to_carts, checkout_starts, paid_orders = values
            rows.append(
                (
                    row_id,
                    session_date,
                    city,
                    "Paid Search" if city == "Shanghai" else "Organic",
                    "Cameras" if city == "Shanghai" else "Home",
                    sessions,
                    add_to_carts,
                    checkout_starts,
                    paid_orders,
                )
            )
            row_id += 1
    conn.executemany(
        """
        INSERT INTO traffic_sessions
            (id, session_date, city, channel, landing_category_name, sessions,
             add_to_carts, checkout_starts, paid_orders)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_inventory_and_stockouts(conn: sqlite3.Connection) -> None:
    products = [
        (1, "Mirrorless Camera A", "Cameras", [42, 18, 0, 4], [0, 0, 12, 30]),
        (2, "Action Camera B", "Cameras", [35, 12, 0, 8], [0, 0, 20, 25]),
        (3, "Camera Lens C", "Cameras", [55, 33, 14, 18], [0, 0, 10, 20]),
        (20, "Robot Vacuum", "Home", [120, 118, 116, 110], [20, 20, 15, 15]),
    ]
    dates = ["2026-06-05", "2026-06-10", "2026-06-15", "2026-06-20"]
    rows = []
    row_id = 1
    for product_id, product_name, category_name, available_values, inbound_values in products:
        for snapshot_date, available_quantity, inbound_quantity in zip(dates, available_values, inbound_values):
            rows.append(
                (
                    row_id,
                    snapshot_date,
                    product_id,
                    product_name,
                    category_name,
                    available_quantity,
                    inbound_quantity,
                )
            )
            row_id += 1
    stockouts = [
        (1, 1, "Mirrorless Camera A", "Cameras", "2026-06-14", "2026-06-18", 58000.00),
        (2, 2, "Action Camera B", "Cameras", "2026-06-13", "2026-06-17", 24000.00),
        (3, 7, "Noise Cancelling Headphones", "Audio", "2026-06-19", "2026-06-20", 9000.00),
    ]
    conn.executemany(
        """
        INSERT INTO inventory_snapshots
            (id, snapshot_date, product_id, product_name, category_name, available_quantity, inbound_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.executemany(
        """
        INSERT INTO stockout_events
            (id, product_id, product_name, category_name, start_date, end_date, lost_sales_estimate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        stockouts,
    )


def _seed_refunds_reviews_pricing_and_fulfillment(conn: sqlite3.Connection) -> None:
    refunds = [
        (1, "2026-06-05", 1001, 1, "Mirrorless Camera A", "Cameras", "damaged_package", 5299.00, "approved"),
        (2, "2026-06-15", 1001, 1, "Mirrorless Camera A", "Cameras", "focus_issue", 5299.00, "approved"),
        (3, "2026-06-15", 1002, 1, "Mirrorless Camera A", "Cameras", "late_delivery", 5299.00, "approved"),
        (4, "2026-06-15", 1003, 3, "Camera Lens C", "Cameras", "compatibility_issue", 2499.00, "requested"),
        (5, "2026-06-15", 1004, 2, "Action Camera B", "Cameras", "quality_issue", 1899.00, "approved"),
        (6, "2026-06-15", 1005, 3, "Camera Lens C", "Cameras", "not_as_described", 2499.00, "requested"),
        (7, "2026-06-10", 1006, 20, "Robot Vacuum", "Home", "promo_price_dispute", 2330.00, "approved"),
        (8, "2026-06-20", 1006, 20, "Robot Vacuum", "Home", "quality_issue", 2330.00, "requested"),
        (9, "2026-06-10", 180, 7, "Noise Cancelling Headphones", "Audio", "damaged_package", 1599.00, "approved"),
        (10, "2026-06-20", 220, 13, "Laptop Pro 14", "Computers", "late_delivery", 8999.00, "requested"),
        (11, "2026-06-16", 1002, 1, "Mirrorless Camera A", "Cameras", "repeat_quality_complaint", 5299.00, "requested"),
        (12, "2026-06-15", 300, 25, "Yoga Mat", "Sports", "wrong_item", 159.00, "approved"),
    ]
    reviews = [
        (1, "2026-06-05", 1, "Mirrorless Camera A", 5, "positive", "image_quality"),
        (2, "2026-06-06", 1, "Mirrorless Camera A", 2, "negative", "focus_issue"),
        (3, "2026-06-07", 1, "Mirrorless Camera A", 1, "negative", "overheating"),
        (4, "2026-06-10", 1, "Mirrorless Camera A", 2, "negative", "late_delivery"),
        (5, "2026-06-12", 1, "Mirrorless Camera A", 3, "neutral", "battery_life"),
        (6, "2026-06-15", 1, "Mirrorless Camera A", 1, "negative", "quality_issue"),
        (7, "2026-06-16", 1, "Mirrorless Camera A", 2, "negative", "damaged_package"),
        (8, "2026-06-20", 1, "Mirrorless Camera A", 4, "positive", "image_quality"),
        (9, "2026-06-05", 2, "Action Camera B", 4, "positive", "portability"),
        (10, "2026-06-12", 2, "Action Camera B", 2, "negative", "quality_issue"),
        (11, "2026-06-15", 2, "Action Camera B", 3, "neutral", "battery_life"),
        (12, "2026-06-18", 2, "Action Camera B", 4, "positive", "value"),
        (13, "2026-06-05", 3, "Camera Lens C", 5, "positive", "sharpness"),
        (14, "2026-06-14", 3, "Camera Lens C", 2, "negative", "compatibility_issue"),
        (15, "2026-06-18", 3, "Camera Lens C", 3, "neutral", "weight"),
        (16, "2026-06-20", 3, "Camera Lens C", 4, "positive", "sharpness"),
        (17, "2026-06-05", 20, "Robot Vacuum", 4, "positive", "convenience"),
        (18, "2026-06-10", 20, "Robot Vacuum", 2, "negative", "promo_price_dispute"),
        (19, "2026-06-15", 20, "Robot Vacuum", 3, "neutral", "noise"),
        (20, "2026-06-20", 20, "Robot Vacuum", 4, "positive", "cleaning"),
        (21, "2026-06-05", 7, "Noise Cancelling Headphones", 5, "positive", "sound_quality"),
        (22, "2026-06-10", 7, "Noise Cancelling Headphones", 4, "positive", "comfort"),
        (23, "2026-06-15", 13, "Laptop Pro 14", 5, "positive", "performance"),
        (24, "2026-06-20", 25, "Yoga Mat", 4, "positive", "value"),
    ]
    pricing = [
        (1, 1, "Mirrorless Camera A", "2026-06-01", "2026-06-09", 5599.00, 5299.00, "competitive_match"),
        (2, 2, "Action Camera B", "2026-06-10", "2026-06-18", 1999.00, 1899.00, "camera_coupon"),
        (3, 20, "Robot Vacuum", "2026-06-10", "2026-06-18", 2399.00, 1999.00, "bundle_flash_sale"),
        (4, 7, "Noise Cancelling Headphones", "2026-06-08", "2026-06-09", 1599.00, 1399.00, "member_day"),
        (5, 13, "Laptop Pro 14", "2026-06-15", "2026-06-20", 8999.00, 8799.00, "paid_search_landing_test"),
    ]
    fulfillment = [
        (1, "2026-06-05", 1001, 1, "Mirrorless Camera A", "Shanghai", 0, "delivered", "none"),
        (2, "2026-06-05", 1002, 1, "Mirrorless Camera A", "Beijing", 1, "delivered", "carrier_delay"),
        (3, "2026-06-05", 1003, 3, "Camera Lens C", "Shenzhen", 0, "delivered", "none"),
        (4, "2026-06-10", 1006, 20, "Robot Vacuum", "Shanghai", 2, "delivered", "warehouse_backlog"),
        (5, "2026-06-12", 1006, 20, "Robot Vacuum", "Shanghai", 3, "delivered", "warehouse_backlog"),
        (6, "2026-06-15", 1001, 1, "Mirrorless Camera A", "Shanghai", 4, "delayed", "stockout_wait"),
        (7, "2026-06-15", 1002, 1, "Mirrorless Camera A", "Beijing", 5, "delayed", "stockout_wait"),
        (8, "2026-06-15", 1004, 2, "Action Camera B", "Shanghai", 4, "delayed", "stockout_wait"),
        (9, "2026-06-15", 1005, 3, "Camera Lens C", "Guangzhou", 1, "delivered", "carrier_delay"),
        (10, "2026-06-20", 220, 13, "Laptop Pro 14", "Hangzhou", 2, "delivered", "carrier_delay"),
        (11, "2026-06-20", 180, 7, "Noise Cancelling Headphones", "Chengdu", 1, "delivered", "carrier_delay"),
        (12, "2026-06-20", 300, 25, "Yoga Mat", "Nanjing", 0, "delivered", "none"),
    ]
    conn.executemany(
        """
        INSERT INTO refund_requests
            (id, request_date, order_id, product_id, product_name, category_name, reason, refund_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        refunds,
    )
    conn.executemany(
        """
        INSERT INTO product_reviews
            (id, review_date, product_id, product_name, rating, sentiment, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        reviews,
    )
    conn.executemany(
        """
        INSERT INTO pricing_events
            (id, product_id, product_name, start_date, end_date, old_price, new_price, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        pricing,
    )
    conn.executemany(
        """
        INSERT INTO fulfillment_events
            (id, event_date, order_id, product_id, product_name, city, delay_days, delivery_status, issue_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        fulfillment,
    )


def seed_realistic_scenarios(conn: sqlite3.Connection) -> None:
    create_realistic_schema(conn)
    _insert_scenario_orders(conn)
    _seed_campaigns(conn)
    _seed_traffic(conn)
    _seed_inventory_and_stockouts(conn)
    _seed_refunds_reviews_pricing_and_fulfillment(conn)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table_name: conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        for table_name in REALISTIC_TABLES
    }
