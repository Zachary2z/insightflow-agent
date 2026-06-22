from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random

import pandas as pd


def generate_general_business_dataset(output_dir: str | Path, months: int = 12, seed: int = 42) -> dict:
    random.seed(seed)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    start = date(2025, 1, 1)
    days = max(30, months * 30)
    channels = ["paid_search", "email", "organic", "partner", "direct"]
    segments = ["startup", "mid_market", "enterprise"]
    regions = ["North", "South", "East", "West"]
    customers = [
        {
            "customer_id": i,
            "customer_name": f"Customer {i}",
            "segment": random.choice(segments),
            "region": random.choice(regions),
        }
        for i in range(1, 101)
    ]
    orders = []
    for order_id in range(1, 1201):
        order_day = start + timedelta(days=random.randrange(days))
        customer = random.choice(customers)
        channel = random.choice(channels)
        base_revenue = random.uniform(80, 1200)
        if channel == "paid_search" and order_day > start + timedelta(days=days - 90):
            base_revenue *= 0.72
        orders.append(
            {
                "order_id": order_id,
                "order_date": order_day.isoformat(),
                "customer_id": customer["customer_id"],
                "revenue": round(base_revenue, 2),
                "channel": channel,
                "status": random.choice(["paid", "paid", "paid", "refunded"]),
            }
        )
    spend = []
    for day_offset in range(days):
        spend_day = start + timedelta(days=day_offset)
        for channel in channels:
            spend.append(
                {
                    "spend_date": spend_day.isoformat(),
                    "channel": channel,
                    "spend": round(random.uniform(100, 2000), 2),
                }
            )
    orders_frame = pd.DataFrame(orders)
    customers_frame = pd.DataFrame(customers)
    spend_frame = pd.DataFrame(spend)
    orders_frame.to_csv(output / "orders.csv", index=False)
    customers_frame.to_csv(output / "customers.csv", index=False)
    spend_frame.to_csv(output / "marketing_spend.csv", index=False)
    with pd.ExcelWriter(output / "general_business_workspace.xlsx") as writer:
        orders_frame.to_excel(writer, sheet_name="orders", index=False)
        customers_frame.to_excel(writer, sheet_name="customers", index=False)
        spend_frame.to_excel(writer, sheet_name="marketing_spend", index=False)
    return {
        "success": True,
        "files": [
            str(output / "orders.csv"),
            str(output / "customers.csv"),
            str(output / "marketing_spend.csv"),
            str(output / "general_business_workspace.xlsx"),
        ],
        "embedded_scenarios": ["paid_search revenue decline in final 90 days"],
    }
