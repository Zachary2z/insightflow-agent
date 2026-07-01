import yaml

from agents.schema_repair import _semantic_layer_hints


def test_schema_repair_reads_workspace_yaml_semantic_layer_without_json_error(tmp_path):
    semantic_layer_path = tmp_path / "semantic_layer.yaml"
    semantic_layer_path.write_text(
        yaml.safe_dump(
            {
                "workspace_id": "store-workspace",
                "tables": [{"table_name": "store_operations"}],
                "metrics": [{"name": "sum_sales_amount", "field": "store_operations.sales_amount"}],
                "dimensions": [{"name": "store_name", "field": "store_operations.store_name"}],
                "time_fields": [{"name": "business_date", "field": "store_operations.business_date"}],
                "entities": [],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    hints = _semantic_layer_hints(
        {
            "semantic_layer_path": str(semantic_layer_path),
            "metric_context": {"matched_metrics": ["sum_sales_amount"]},
        }
    )

    assert "semantic_layer_error" not in hints
    assert hints["semantic_layer_path"] == str(semantic_layer_path)
    assert hints["semantic_layer"]["tables"][0]["table_name"] == "store_operations"
    assert hints["semantic_layer"]["metrics"][0]["field"] == "store_operations.sales_amount"
    assert hints["semantic_layer"]["time_fields"][0]["field"] == "store_operations.business_date"
