from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from llm_ops.deepseek_provider import DeepSeekProvider, load_deepseek_config
from llm_ops.provider import LLMProvider


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _values(env: dict[str, str] | None = None) -> dict[str, str]:
    return env if env is not None else os.environ


def _flag_enabled(name: str, env: dict[str, str] | None = None) -> bool:
    values = _values(env)
    return str(values.get(name, "")).strip().lower() in _TRUE_VALUES


def product_live_mode_enabled(env: dict[str, str] | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_PRODUCT_LIVE_MODE", env)


def _product_safe_provider_enabled(name: str, env: dict[str, str] | None = None) -> bool:
    return _flag_enabled(name, env) or product_live_mode_enabled(env)


def provider_question_understanding_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_QUESTION_UNDERSTANDING", env)


def provider_clarification_router_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_CLARIFICATION_ROUTER", env)


def provider_sql_planning_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_SQL_PLANNING", env)


def provider_sql_candidate_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_SQL_CANDIDATE", env)


def provider_business_review_planner_enabled(env: dict[str, str] | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_USE_PROVIDER_BUSINESS_REVIEW_PLANNER", env)


def provider_report_writer_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_REPORT_WRITER", env)


def provider_claim_typing_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_CLAIM_TYPING", env)


def provider_insight_drafting_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_INSIGHT_DRAFTING", env)


def provider_action_drafter_enabled(env: dict[str, str] | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_USE_PROVIDER_ACTION_DRAFTER", env)


def provider_analysis_planner_enabled(env: dict[str, str] | None = None) -> bool:
    return _flag_enabled("INSIGHTFLOW_USE_PROVIDER_ANALYSIS_PLANNER", env)


def provider_visualization_agent_enabled(env: dict[str, str] | None = None) -> bool:
    return _product_safe_provider_enabled("INSIGHTFLOW_USE_PROVIDER_VISUALIZATION_AGENT", env)


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


def build_claim_typing_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_claim_typing_enabled(env):
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
    if not provider_insight_drafting_enabled(env):
        return None

    config = load_deepseek_config(env_path=env_path, require_api_key=True)
    if not config.success:
        return None

    try:
        return DeepSeekProvider(config)
    except Exception:
        return None


def build_action_drafter_provider(
    env_path: str | Path = ".env",
    env: dict[str, str] | None = None,
) -> LLMProvider | None:
    if not provider_action_drafter_enabled(env):
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
    if not provider_analysis_planner_enabled(env):
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
    if not provider_visualization_agent_enabled(env):
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
