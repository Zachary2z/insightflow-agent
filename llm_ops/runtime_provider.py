from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from llm_ops.deepseek_provider import DeepSeekProvider, load_deepseek_config
from llm_ops.provider import LLMProvider


def provider_question_understanding_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def provider_clarification_router_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def provider_sql_planning_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def provider_sql_candidate_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def provider_business_review_planner_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def provider_report_writer_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_question_understanding_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_question_understanding_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_sql_planning_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_sql_planning_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_sql_candidate_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_sql_candidate_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_business_review_planner_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_business_review_planner_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_report_writer_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_report_writer_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_clarification_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_clarification_router_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None
