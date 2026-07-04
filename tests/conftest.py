from __future__ import annotations

import os


def pytest_configure() -> None:
    os.environ.setdefault("INSIGHTFLOW_PRODUCT_LIVE_MODE", "0")
