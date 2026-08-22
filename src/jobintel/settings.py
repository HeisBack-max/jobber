"""Application configuration: environment variables + YAML config loading.

Environment variables hold secrets and deployment-specific values (see
.env.example). YAML files under config/ hold everything else, so
preference/scoring/source changes never require touching code.
"""

from __future__ import annotations

import functools
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOBINTEL_", env_file=".env", extra="ignore")

    database_url: str = Field(default=f"sqlite:///{DATA_DIR / 'jobintel.db'}")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-sonnet-5")
    daily_llm_budget_usd: float = Field(default=5.00)

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    slack_webhook_url: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    notification_email_from: str | None = None
    notification_email_to: str | None = None  # comma-separated

    request_timeout_seconds: int = 20
    user_agent: str = "RemoteJobIntelligence/0.1 (personal use; contact: bestrichardanthonyspencer@gmail.com)"


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@functools.lru_cache
def load_profile() -> dict[str, Any]:
    return _load_yaml("profile.yaml")


@functools.lru_cache
def load_roles() -> dict[str, Any]:
    return _load_yaml("roles.yaml")


@functools.lru_cache
def load_sources() -> dict[str, Any]:
    return _load_yaml("sources.yaml")


@functools.lru_cache
def load_strategic_companies() -> dict[str, Any]:
    return _load_yaml("strategic_companies.yaml")


@functools.lru_cache
def load_search_queries() -> dict[str, Any]:
    return _load_yaml("search_queries.yaml")


@functools.lru_cache
def load_scoring() -> dict[str, Any]:
    return _load_yaml("scoring.yaml")


@functools.lru_cache
def load_cv_evidence_map() -> dict[str, Any]:
    path = CONFIG_DIR / "cv_evidence_map.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# Caches derived from config that live outside this module (e.g. the
# embedding index built from roles.yaml + cv_evidence_map.json) register
# their clearer here, so clear_config_cache() stays the single place a
# test or a config reload has to call.
_EXTRA_CACHE_CLEARERS: list[Callable[[], None]] = []


def register_cache_clearer(clearer: Callable[[], None]) -> None:
    if clearer not in _EXTRA_CACHE_CLEARERS:
        _EXTRA_CACHE_CLEARERS.append(clearer)


def clear_config_cache() -> None:
    """Used by tests that need to reload config after monkeypatching CONFIG_DIR."""
    for fn in (
        load_profile,
        load_roles,
        load_sources,
        load_strategic_companies,
        load_search_queries,
        load_scoring,
        load_cv_evidence_map,
    ):
        fn.cache_clear()
    for clearer in _EXTRA_CACHE_CLEARERS:
        clearer()
