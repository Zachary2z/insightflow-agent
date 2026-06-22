import pandas as pd

from workspaces.synthetic_data import generate_general_business_dataset


def test_synthetic_dataset_creates_csv_and_excel_exports(tmp_path):
    result = generate_general_business_dataset(output_dir=tmp_path, months=12)

    assert result["success"] is True
    assert (tmp_path / "orders.csv").exists()
    assert (tmp_path / "customers.csv").exists()
    assert (tmp_path / "marketing_spend.csv").exists()
    assert (tmp_path / "general_business_workspace.xlsx").exists()

    orders = pd.read_csv(tmp_path / "orders.csv")
    assert {"order_id", "order_date", "customer_id", "revenue", "channel"}.issubset(orders.columns)
    assert orders["order_date"].nunique() > 30
    assert orders["revenue"].notna().sum() > 100
