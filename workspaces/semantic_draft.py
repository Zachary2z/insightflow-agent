from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from workspaces.store import WorkspaceStore


_CHINESE_ALIASES_BY_MEANING = {
    "revenue_like": ["销售额", "收入", "营收", "营业额", "成交额"],
    "cost_like": ["成本", "费用", "支出", "花费", "投放成本"],
    "amount_like": ["金额", "数值"],
    "count_like": ["数量", "次数", "单量", "件数"],
    "rating_like": ["满意度", "评分", "得分"],
    "date_like": ["日期", "时间"],
    "status": ["状态", "阶段"],
}

_CHINESE_ALIASES_BY_NAME = (
    (("store", "shop", "branch", "门店", "店铺"), ["门店", "店铺"]),
    (("team", "group", "团队", "小组", "客服组"), ["团队", "客服团队"]),
    (("customer", "client", "user", "客户", "用户"), ["客户", "用户"]),
    (("product", "sku", "商品", "产品"), ["产品", "商品"]),
    (("ticket", "case", "工单", "客服"), ["工单", "客服工单"]),
    (("response", "resolution", "handle", "响应", "解决", "处理"), ["响应时长", "处理时长"]),
    (("city", "城市"), ["城市"]),
    (("region", "area", "地区", "区域"), ["区域", "地区"]),
    (("sales", "revenue", "income", "turnover", "营业额", "营收", "收入", "销售额"), ["销售额", "收入", "营收", "营业额", "成交额"]),
    (("cost", "expense", "spend", "fee", "成本", "费用", "支出"), ["成本", "费用", "支出", "花费", "投放成本"]),
    (("score", "rating", "nps", "满意度", "评分", "得分"), ["满意度", "评分", "得分"]),
    (("date", "time", "日期", "时间"), ["日期", "时间"]),
)


def generate_semantic_layer_draft(
    store: WorkspaceStore,
    workspace_id: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    metrics = []
    dimensions = []
    time_fields = []
    entities = []
    field_roles: dict[str, str] = {}
    semantic_aliases: dict[str, list[str]] = {}
    tables = []
    for table in profile.get("tables", []):
        table_name = table["table_name"]
        tables.append(
            {
                "table_name": table_name,
                "row_count": table.get("row_count", 0),
                "columns": [column.get("name", "") for column in table.get("columns", [])],
            }
        )
        for column in table.get("columns", []):
            name = column["name"]
            roles = column.get("role_candidates", {})
            qualified = f"{table_name}.{name}"
            field_role = column.get("field_role") or _field_role_from_candidates(roles)
            field_roles[qualified] = field_role
            semantic_aliases[qualified] = _aliases_for_field(
                name,
                field_role=field_role,
                meanings=column.get("business_meaning_candidates", []),
            )
            if field_role == "metric":
                metrics.extend(_metric_definitions(table_name, name, qualified, column))
            if field_role in {"dimension", "status"}:
                dimensions.append(
                    {
                        "name": name,
                        "label": _label_for_field(
                            name,
                            field_role=field_role,
                            meanings=column.get("business_meaning_candidates", []),
                        ),
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "role": field_role,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected groupable {field_role} from {qualified}.",
                    }
                )
            if field_role == "time":
                time_fields.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected time field from {qualified}.",
                    }
                )
            if field_role == "id":
                entities.append(
                    {
                        "name": name,
                        "table": table_name,
                        "field": qualified,
                        "enabled": True,
                        "aliases": semantic_aliases[qualified],
                        "description": f"Auto-detected identifier from {qualified}.",
                    }
                )
    relationships = _relationship_candidates(profile)
    semantic_layer = {
        "workspace_id": workspace_id,
        "tables": tables,
        "metrics": metrics,
        "dimensions": dimensions,
        "time_fields": time_fields,
        "entities": entities,
        "field_roles": field_roles,
        "semantic_aliases": semantic_aliases,
        "relationships": relationships,
        "available_analysis_capabilities": {
            "metrics": [metric["field"] for metric in metrics],
            "groupable_dimensions": [dimension["field"] for dimension in dimensions],
            "time_fields": [field["field"] for field in time_fields],
            "relationships": [relationship["name"] for relationship in relationships],
        },
        "join_paths": [],
    }
    save_semantic_layer(store, workspace_id, semantic_layer)
    return semantic_layer


def save_semantic_layer(store: WorkspaceStore, workspace_id: str, semantic_layer: dict[str, Any]) -> dict[str, Any]:
    workspace = store.get_workspace(workspace_id)
    semantic_layer["workspace_id"] = workspace_id
    Path(workspace["semantic_layer_path"]).write_text(
        yaml.safe_dump(semantic_layer, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return {"success": True, "semantic_layer_path": workspace["semantic_layer_path"]}


def _field_role_from_candidates(roles: dict[str, Any]) -> str:
    for role in ("time", "metric", "measure", "status", "id", "dimension", "text"):
        if roles.get(role):
            return "metric" if role == "measure" else role
    return "dimension"


def _quote_sql_identifier(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def _qualified_sql_identifier(table_name: str, column_name: str) -> str:
    return f"{_quote_sql_identifier(table_name)}.{_quote_sql_identifier(column_name)}"


def _label_for_field(name: str, *, field_role: str = "", meanings: list[str] | None = None) -> str:
    chinese_aliases = _chinese_business_aliases(name, field_role=field_role, meanings=meanings or [])
    if chinese_aliases:
        return chinese_aliases[0]
    return str(name).replace("_", " ").strip().title() if str(name).isascii() else str(name)


def _aliases_for_field(name: str, *, field_role: str = "", meanings: list[str] | None = None) -> list[str]:
    text = str(name)
    aliases = _chinese_business_aliases(text, field_role=field_role, meanings=meanings or [])
    aliases.append(text)
    spaced = text.replace("_", " ").strip()
    if spaced and spaced != text:
        aliases.append(spaced)
    compact = text.replace("_", "").strip()
    if compact and compact not in aliases:
        aliases.append(compact)
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _chinese_business_aliases(name: str, *, field_role: str, meanings: list[str]) -> list[str]:
    aliases: list[str] = []
    for meaning in meanings:
        aliases.extend(_CHINESE_ALIASES_BY_MEANING.get(str(meaning), []))
    if field_role == "id":
        aliases.extend(["编号", "ID"])
    if field_role == "status":
        aliases.extend(_CHINESE_ALIASES_BY_MEANING["status"])

    compact_name = str(name).lower().replace("_", "").replace("-", "").replace(" ", "")
    for tokens, token_aliases in _CHINESE_ALIASES_BY_NAME:
        if any(str(token).lower().replace("_", "").replace("-", "").replace(" ", "") in compact_name for token in tokens):
            aliases.extend(token_aliases)
    return list(dict.fromkeys(alias for alias in aliases if alias))


def _metric_definitions(table_name: str, name: str, qualified: str, column: dict[str, Any]) -> list[dict[str, Any]]:
    meaning_list = list(column.get("business_meaning_candidates", []))
    meaning_set = set(meaning_list)
    aggregations = set(column.get("suitable_aggregations", [])) or {"sum", "avg", "count"}
    if "rating_like" in meaning_set:
        selected_aggregations = ["avg"]
    elif "sum" in aggregations:
        selected_aggregations = ["sum"]
    elif "avg" in aggregations:
        selected_aggregations = ["avg"]
    else:
        selected_aggregations = ["count"]

    definitions = []
    for aggregation in selected_aggregations:
        metric_name = f"{aggregation}_{name}"
        aliases = _aliases_for_field(name, field_role="metric", meanings=meaning_list) + _aliases_for_field(
            metric_name,
            field_role="metric",
            meanings=meaning_list,
        )
        definitions.append(
            {
                "name": metric_name,
                "label": _label_for_field(name, field_role="metric", meanings=meaning_list),
                "table": table_name,
                "field": qualified,
                "formula": f"{aggregation.upper()}({_qualified_sql_identifier(table_name, name)})",
                "aggregation": aggregation,
                "enabled": True,
                "business_meaning_candidates": meaning_list,
                "aliases": list(dict.fromkeys(aliases)),
                "description": f"Auto-detected {aggregation} metric from {qualified}.",
            }
        )
    return definitions


def _normalized_join_key(name: str) -> str:
    text = str(name).lower().replace("_", "").replace("-", "").replace(" ", "")
    for suffix in ("id", "编号", "编码"):
        if text.endswith(suffix):
            return text[: -len(suffix)] or text
    return text


def _relationship_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    id_fields: list[dict[str, str]] = []
    for table in profile.get("tables", []):
        table_name = table.get("table_name", "")
        for column in table.get("columns", []):
            roles = column.get("role_candidates", {})
            if column.get("field_role") == "id" or roles.get("id"):
                name = column.get("name", "")
                id_fields.append(
                    {
                        "table": table_name,
                        "column": name,
                        "field": f"{table_name}.{name}",
                        "join_key": _normalized_join_key(name),
                    }
                )

    relationships = []
    seen: set[tuple[str, str]] = set()
    for left_index, left in enumerate(id_fields):
        for right in id_fields[left_index + 1 :]:
            if left["table"] == right["table"] or left["join_key"] != right["join_key"]:
                continue
            key = tuple(sorted((left["field"], right["field"])))
            if key in seen:
                continue
            seen.add(key)
            relationships.append(
                {
                    "name": f"{left['table']}_{right['table']}_{left['join_key']}",
                    "left_table": left["table"],
                    "left_column": left["column"],
                    "left_field": left["field"],
                    "right_table": right["table"],
                    "right_column": right["column"],
                    "right_field": right["field"],
                    "confidence": "candidate",
                    "reason": "Columns share an identifier-like name across tables.",
                }
            )
    return relationships
