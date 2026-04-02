from __future__ import annotations

from collections.abc import Iterable

from sutra_backend.config import Settings
from sutra_backend.runtime.env_policy import build_runtime_env_plan


_MANAGED_RUNTIME_ENV_NAMES: tuple[str, ...] = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "HERMES_MODEL",
    "LLM_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "MINIMAX_API_KEY",
    "MINIMAX_CN_API_KEY",
    "MINIMAX_BASE_URL",
    "MINIMAX_CN_BASE_URL",
    "BROWSERBASE_API_KEY",
    "BROWSERBASE_PROJECT_ID",
    "BROWSER_USE_API_KEY",
    "FIRECRAWL_API_KEY",
)


def managed_runtime_env_names() -> Iterable[str]:
    return _MANAGED_RUNTIME_ENV_NAMES


def build_managed_runtime_env(settings: Settings) -> dict[str, str]:
    candidate_values = {
        "OPENROUTER_API_KEY": settings.openrouter_api_key,
        "OPENAI_API_KEY": settings.openai_api_key,
        "OPENAI_BASE_URL": settings.openai_base_url,
        "OPENAI_MODEL": settings.openai_model,
        "HERMES_MODEL": settings.hermes_model,
        "LLM_MODEL": settings.llm_model,
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "ANTHROPIC_BASE_URL": settings.anthropic_base_url,
        "MINIMAX_API_KEY": settings.minimax_api_key,
        "MINIMAX_CN_API_KEY": settings.minimax_cn_api_key,
        "MINIMAX_BASE_URL": settings.minimax_base_url,
        "MINIMAX_CN_BASE_URL": settings.minimax_cn_base_url,
        "BROWSERBASE_API_KEY": settings.browserbase_api_key,
        "BROWSERBASE_PROJECT_ID": settings.browserbase_project_id,
        "BROWSER_USE_API_KEY": settings.browser_use_api_key,
        "FIRECRAWL_API_KEY": settings.firecrawl_api_key,
    }
    managed_env = {
        name: value.strip()
        for name, value in candidate_values.items()
        if isinstance(value, str) and value.strip()
    }
    return build_runtime_env_plan(persisted_env=managed_env).persisted_env
