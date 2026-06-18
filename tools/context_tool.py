from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXT_PATHS = {
    "business_rules": ROOT_DIR / "data" / "business_rules.md",
    "table_docs": ROOT_DIR / "data" / "table_docs.md",
    "sql_examples": ROOT_DIR / "data" / "sql_examples.json",
}


def _normalize(text: str) -> str:
    return str(text).lower().replace(" ", "")


def _trace_event(
    question: str,
    rule_count: int,
    table_doc_count: int,
    sql_example_count: int,
    status: str,
    latency_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    summary = f"{rule_count} rules, {table_doc_count} table docs, {sql_example_count} sql examples"
    event = {
        "tool_name": "retrieve_business_context",
        "tool_input_summary": question[:120],
        "tool_output_summary": summary,
        "status": status,
        "latency_ms": latency_ms,
    }
    if error:
        event["error_type"] = "context_load_error"
        event["error"] = error
    return event


def _resolve_context_paths(context_paths: dict[str, str | Path] | None) -> dict[str, Path]:
    resolved = dict(DEFAULT_CONTEXT_PATHS)
    if context_paths:
        for key, value in context_paths.items():
            resolved[key] = Path(value)
    return resolved


def _load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Context file not found: {path}")
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Context file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _parse_keywords(line: str) -> list[str]:
    _, _, raw = line.partition(":")
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


def _parse_markdown_sections(path: Path, kind: str) -> list[dict[str, Any]]:
    text = _load_text(path)
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    content_lines: list[str] = []

    def finish_current() -> None:
        if current is None:
            return
        content = "\n".join(content_lines).strip()
        current["content"] = content
        sections.append(current)

    for line in text.splitlines():
        if line.startswith("## "):
            finish_current()
            title = line.removeprefix("## ").strip()
            current = {
                "id": title.lower().replace(" ", "_"),
                "title": title,
                "source_path": str(path),
                "keywords": [],
            }
            if kind == "table_doc":
                current["table_name"] = title.split()[0]
            content_lines = []
            continue

        if current is None:
            continue

        if line.lower().startswith("keywords:"):
            current["keywords"] = _parse_keywords(line)
            continue

        content_lines.append(line)

    finish_current()
    return sections


def _score_keywords(question: str, keywords: list[str]) -> tuple[int, list[str]]:
    normalized_question = _normalize(question)
    matched = [keyword for keyword in keywords if _normalize(keyword) in normalized_question]
    return len(matched), matched


def _matched_sections(question: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = []
    for section in sections:
        score, matched_keywords = _score_keywords(question, section.get("keywords", []))
        if score <= 0:
            continue
        selected = {
            key: value
            for key, value in section.items()
            if key in {"id", "title", "table_name", "content", "source_path"}
        }
        selected["matched_keywords"] = matched_keywords
        selected["score"] = score
        matched.append(selected)

    return sorted(matched, key=lambda item: (-item["score"], item.get("title", "")))


def _matched_sql_examples(question: str, examples: Any) -> list[dict[str, Any]]:
    if not isinstance(examples, list):
        raise ValueError("SQL examples file must contain a list of examples.")

    matched = []
    for example in examples:
        if not isinstance(example, dict):
            continue
        score, matched_keywords = _score_keywords(question, example.get("question_keywords", []))
        if score <= 0:
            continue
        selected = {
            "id": example.get("id", ""),
            "title": example.get("title", ""),
            "tables": example.get("tables", []),
            "metrics": example.get("metrics", []),
            "sql": example.get("sql", ""),
            "notes": example.get("notes", ""),
            "matched_keywords": matched_keywords,
            "score": score,
        }
        matched.append(selected)

    return sorted(matched, key=lambda item: (-item["score"], item.get("title", "")))


def _context_summary(
    matched_rules: list[dict[str, Any]],
    matched_table_docs: list[dict[str, Any]],
    matched_sql_examples: list[dict[str, Any]],
) -> str:
    if not matched_rules and not matched_table_docs and not matched_sql_examples:
        return "No business context matched."

    table_names = [doc["table_name"] for doc in matched_table_docs if doc.get("table_name")]
    example_titles = [example["title"] for example in matched_sql_examples if example.get("title")]
    parts = [
        f"Matched {len(matched_rules)} business rules",
        f"{len(matched_table_docs)} table docs",
        f"{len(matched_sql_examples)} sql examples",
    ]
    if table_names:
        parts.append("tables: " + ", ".join(table_names))
    if example_titles:
        parts.append("examples: " + "; ".join(example_titles))
    return ". ".join(parts) + "."


def retrieve_business_context(
    question: str,
    context_paths: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    started_at = perf_counter()
    paths = _resolve_context_paths(context_paths)

    try:
        rule_sections = _parse_markdown_sections(paths["business_rules"], kind="business_rule")
        table_sections = _parse_markdown_sections(paths["table_docs"], kind="table_doc")
        sql_examples = _load_json(paths["sql_examples"])
        matched_rules = _matched_sections(question, rule_sections)
        matched_table_docs = _matched_sections(question, table_sections)
        matched_sql_examples = _matched_sql_examples(question, sql_examples)
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error = str(exc)
        return {
            "success": False,
            "question": question,
            "matched_rules": [],
            "matched_table_docs": [],
            "matched_sql_examples": [],
            "context_summary": "",
            "error": error,
            "trace_event": _trace_event(question, 0, 0, 0, "error", latency_ms, error),
        }

    latency_ms = int((perf_counter() - started_at) * 1000)
    return {
        "success": True,
        "question": question,
        "matched_rules": matched_rules,
        "matched_table_docs": matched_table_docs,
        "matched_sql_examples": matched_sql_examples,
        "context_summary": _context_summary(matched_rules, matched_table_docs, matched_sql_examples),
        "trace_event": _trace_event(
            question,
            len(matched_rules),
            len(matched_table_docs),
            len(matched_sql_examples),
            "success",
            latency_ms,
        ),
    }
