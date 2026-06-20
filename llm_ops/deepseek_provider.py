from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from openai import OpenAI

from llm_ops.provider import LLMRequest


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_MODEL_ALIASES = {
    "deepseekv4pro": "deepseek-v4-pro",
    "deepseek-v4-pro": "deepseek-v4-pro",
    "deepseek_v4_pro": "deepseek-v4-pro",
    "v4pro": "deepseek-v4-pro",
    "deepseekv4flash": "deepseek-v4-flash",
    "deepseek-v4-flash": "deepseek-v4-flash",
    "deepseek_v4_flash": "deepseek-v4-flash",
    "v4flash": "deepseek-v4-flash",
}


def live_deepseek_tests_enabled(env: dict[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get("INSIGHTFLOW_LIVE_DEEPSEEK_TESTS", "")).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str = ""
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL
    live_tests_enabled: bool = False
    success: bool = True
    error: str = ""

    def __repr__(self) -> str:
        return (
            "DeepSeekConfig("
            f"api_key_present={bool(self.api_key)}, "
            f"base_url={self.base_url!r}, "
            f"model={self.model!r}, "
            f"live_tests_enabled={self.live_tests_enabled}, "
            f"success={self.success}, "
            f"error={self.error!r})"
        )

    def safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "api_key_present": bool(self.api_key),
            "base_url": self.base_url,
            "model": self.model,
            "live_tests_enabled": self.live_tests_enabled,
            "error": self.error,
        }


def _load_env_file(env_path: str | Path) -> dict[str, str]:
    path = Path(env_path)
    if not path.exists():
        return {}
    return {key: str(value or "") for key, value in dotenv_values(path).items()}


def normalize_deepseek_model(model: str) -> str:
    normalized = model.strip()
    if not normalized:
        return DEFAULT_DEEPSEEK_MODEL
    alias_key = normalized.lower().replace(" ", "").replace(".", "-")
    return DEEPSEEK_MODEL_ALIASES.get(alias_key, normalized)


def load_deepseek_config(env_path: str | Path = ".env", require_api_key: bool = False) -> DeepSeekConfig:
    file_values = _load_env_file(env_path)
    values = {**file_values, **os.environ}
    api_key = str(values.get("DEEPSEEK_API_KEY", "")).strip()
    base_url = str(values.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL)).strip() or DEFAULT_DEEPSEEK_BASE_URL
    model = normalize_deepseek_model(str(values.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)))
    live_enabled = live_deepseek_tests_enabled(values)

    if require_api_key and not api_key:
        return DeepSeekConfig(
            api_key="",
            base_url=base_url,
            model=model,
            live_tests_enabled=live_enabled,
            success=False,
            error="DEEPSEEK_API_KEY is required",
        )

    return DeepSeekConfig(
        api_key=api_key,
        base_url=base_url,
        model=model,
        live_tests_enabled=live_enabled,
        success=True,
        error="",
    )


class DeepSeekProvider:
    def __init__(self, config: DeepSeekConfig, client: Any | None = None):
        if not config.api_key and client is None:
            raise ValueError("DEEPSEEK_API_KEY is required to create DeepSeekProvider")
        self.config = config
        self.model = config.model
        self.client = client or OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.last_finish_reason = None
        self.last_usage = None

    def generate(self, request: LLMRequest) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. Return only valid JSON. No markdown fences. No prose.",
                },
                {"role": "user", "content": request.prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        choice = response.choices[0]
        self.last_finish_reason = getattr(choice, "finish_reason", None)
        usage = getattr(response, "usage", None)
        self.last_usage = usage.model_dump() if hasattr(usage, "model_dump") else usage
        return choice.message.content or ""
