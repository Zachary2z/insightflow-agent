from __future__ import annotations

import json

from observability.redaction import (
    classify_error,
    is_path_like,
    is_prohibited_text,
    is_secret_like,
    is_sql_like,
    safe_truncate,
    sanitize_observability_fields,
)


class HostileString:
    str_calls = 0
    repr_calls = 0

    def __str__(self):
        type(self).str_calls += 1
        raise RuntimeError("must not be called")

    def __repr__(self):
        type(self).repr_calls += 1
        raise RuntimeError("must not be called")


def test_allowlist_drops_sensitive_and_unknown_fields_recursively():
    payload = {
        "event": "http_request_completed",
        "status": "success",
        "api_key": "health-secret-do-not-leak",
        "Authorization": "Bearer synthetic-token-do-not-leak",
        "prompt": "complete Prompt",
        "system_message": "private",
        "messages": ["private"],
        "sql": "SELECT * FROM customer",
        "raw_rows": [["customer-secret"]],
        "provider_response": {"secret": "sk-synthetic-do-not-leak"},
        "database_path": "/app/workspaces/private/data.db",
        "trace_path": "/Users/private/logs/trace.json",
        "environment": ".env contents",
        "unknown": {"operation": "Bearer nested-secret"},
    }
    result = sanitize_observability_fields(payload)
    assert result == {"event": "http_request_completed", "status": "success"}
    serialized = str(result)
    for forbidden in (
        "health-secret-do-not-leak",
        "synthetic-token-do-not-leak",
        "sk-synthetic-do-not-leak",
        "Prompt",
        "SELECT",
        "customer-secret",
        "/Users/private",
        "/app/workspaces",
        ".env",
    ):
        assert forbidden not in serialized


def test_secret_and_path_detection_covers_synthetic_fixtures():
    assert is_secret_like("Authorization: Bearer synthetic-token-do-not-leak")
    assert is_secret_like("DEEPSEEK_API_KEY=health-secret-do-not-leak")
    assert is_secret_like("sk-synthetic-do-not-leak")
    assert is_path_like("/Users/private/project/file.csv")
    assert is_path_like("/app/workspaces/customer/data.db")


def test_path_detection_covers_embedded_unix_file_uri_database_and_windows_paths():
    for path in (
        "/Users/private/file",
        "path=/Users/private/file",
        "file:/app/workspaces/file",
        "db_path=/tmp/data.db",
        r"C:\Users\private\file",
    ):
        assert is_path_like(path)


def test_sql_and_dotenv_are_detected_from_text_not_only_field_names():
    assert is_sql_like("SELECT * FROM customer")
    assert is_prohibited_text("operation uses .env contents")
    assert is_prohibited_text("provider payload")


def test_original_nested_operation_reproduction_fails_closed():
    result = sanitize_observability_fields(
        {
            "operation": [
                "SELECT * FROM customer",
                "path=/Users/private/customer.csv",
                ".env contents",
                "file:/app/workspaces/customer.csv",
                "provider payload synthetic secret",
            ],
            "status": "success",
        }
    )
    assert result == {"status": "success"}
    serialized = json.dumps(result)
    for forbidden in (
        "SELECT",
        "customer",
        "/Users/",
        "/app/",
        ".env",
        "provider payload",
        "synthetic secret",
    ):
        assert forbidden not in serialized


def test_nested_dictionary_cannot_reuse_allowlisted_keys():
    result = sanitize_observability_fields(
        {
            "operation": {
                "operation": "analysis",
                "status": "success",
                "provider": "deepseek",
            },
            "status": "success",
        }
    )
    assert result == {"status": "success"}


def test_nested_provider_payload_and_secret_are_dropped_as_a_collection():
    result = sanitize_observability_fields(
        {
            "provider": {
                "provider": "provider payload",
                "operation": "Bearer synthetic-token-do-not-leak",
            },
            "event": "llm_request_completed",
        }
    )
    assert result == {"event": "llm_request_completed"}
    serialized = json.dumps(result)
    assert "provider payload" not in serialized
    assert "synthetic-token-do-not-leak" not in serialized


def test_safe_truncate_remains_bounded_for_explicit_text_utility():
    assert safe_truncate("x" * 300) == "x" * 256


def test_valid_scalar_schema_remains_json_serializable():
    result = sanitize_observability_fields(
        {
            "timestamp": "2026-07-11T13:00:00Z",
            "level": "info",
            "event": "http_request_completed",
            "request_id": "req_scalar",
            "operation": "health_check",
            "provider": "local",
            "status": "success",
            "latency_ms": 12,
            "retry_count": 0,
        }
    )
    assert json.loads(json.dumps(result)) == result
    assert result["operation"] == "health_check"


def test_hostile_or_unserializable_objects_fail_closed():
    HostileString.str_calls = 0
    HostileString.repr_calls = 0
    result = sanitize_observability_fields(
        {"operation": HostileString(), "provider": object(), "status": "success"}
    )
    assert result == {"status": "success"}
    assert HostileString.str_calls == 0
    assert HostileString.repr_calls == 0


def test_exception_messages_are_never_used_for_error_classification():
    secret = "Bearer synthetic-token-do-not-leak /Users/private/file SELECT * FROM secrets"
    assert classify_error(RuntimeError(secret)) == "internal_error"
    assert classify_error(TimeoutError(secret)) == "timeout"
