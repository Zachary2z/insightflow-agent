from __future__ import annotations

import os
from pathlib import Path

from data.seed_data import seed_database


ROOT = Path(__file__).resolve().parents[1]


def pytest_configure() -> None:
    os.environ.setdefault("INSIGHTFLOW_PRODUCT_LIVE_MODE", "0")
    fixture_db = ROOT / "data" / "ecommerce.db"
    if not fixture_db.exists():
        seed_database(fixture_db)
