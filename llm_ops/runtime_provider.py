from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from llm_ops.deepseek_provider import DeepSeekProvider, load_deepseek_config
from llm_ops.deepseek_provider import _load_env_file
from llm_ops.provider import LLMProvider


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _values(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> dict[str, str]:
    file_values = _load_env_file(env_path) if env_path else {}
    runtime_values = env if env is not None else os.environ
    return {**file_values, **runtime_values}


def _flag_enabled(name: str, env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    values = _values(env, env_path)
    return str(values.get(name, "")).strip().lower() in _TRUE_VALUES


def product_live_mode_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_PRODUCT_LIVE_MODE", env, env_path)


def _product_safe_provider_enabled(
    name: str,
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> bool:
    return _flag_enabled(name, env, env_path) or product_live_mode_enabled(env, env_path)


def provider_question_understanding_enabled(
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", env, env_path)


def provider_clarification_router_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", env, env_path)


def provider_sql_planning_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING", env, env_path)


def provider_sql_candidate_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE", env, env_path)


def provider_claim_typing_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING", env, env_path)


def provider_insight_drafting_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING", env, env_path)


def provider_answer_reviewer_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_ANSWER_REVIEWER", env, env_path)


def provider_final_answer_composer_enabled(
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_FINAL_ANSWER_COMPOSER", env, env_path)


def provider_report_composer_enabled(
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_REPORT_COMPOSER", env, env_path)


def provider_analysis_planner_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_USE_PROVIDER_ANALYSIS_PLANNER", env, env_path)


def provider_visualization_agent_enabled(env: dict[str, str] | None = None, env_path: str | Path | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT", env, env_path)


def build_question_understanding_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_question_understanding_enabled(env, env_path):
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
    if not provider_sql_planning_enabled(env, env_path):
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
    if not provider_sql_candidate_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_claim_typing_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_claim_typing_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_insight_drafting_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_insight_drafting_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_answer_reviewer_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_answer_reviewer_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_final_answer_composer_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_final_answer_composer_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_report_composer_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_report_composer_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_analysis_planner_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_analysis_planner_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_visualization_agent_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_visualization_agent_enabled(env, env_path):
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
    if not provider_clarification_router_enabled(env, env_path):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None
