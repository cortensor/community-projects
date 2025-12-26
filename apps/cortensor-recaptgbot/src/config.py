from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    router_base_url: str
    router_api_key: str
    router_session_id: Optional[int]
    target_chat_id: Optional[int]
    side_chat_id: Optional[int]
    allow_main_chat: bool
    request_timeout: int
    router_prompt_type: int
    router_prompt_template: str
    router_precommit_timeout: int
    router_client_reference: str
    router_max_tokens: int
    router_temperature: float
    router_top_p: float
    router_top_k: int
    router_presence_penalty: float
    router_frequency_penalty: float

    # X (Twitter) API v2
    x_username: str
    x_bearer_token: str
    x_fetch_mode: str
    x_scrape_rss_base_urls: list[str]
    x_user_id: Optional[str]

    # Recap schedule
    recap_interval_days: int
    auto_recap_enabled: bool
    recap_post_hour_utc: int

    # Access control (Telegram)
    admin_only: bool
    admin_user_ids: set[int]
    allowed_chat_ids: set[int]


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip() in {"1", "true", "True", "yes", "on"}


def _parse_int_set(value: str | None) -> set[int]:
    if not value:
        return set()
    out: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def _parse_str_list(value: str | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            out.append(part)
    return out


def load_settings() -> Settings:
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    # Fallback: try default search path if the explicit path didn't load values
    if not os.getenv("BOT_TOKEN"):
        load_dotenv(override=True)

    bot_token = os.getenv("BOT_TOKEN")
    router_base_url = os.getenv("ROUTER_BASE_URL", "http://localhost:5010").rstrip("/")
    router_api_key = os.getenv("ROUTER_API_KEY") or "default-dev-token"
    router_session_id = os.getenv("ROUTER_SESSION_ID")
    target_chat_id = os.getenv("TARGET_CHAT_ID")
    side_chat_id = os.getenv("SIDE_CHAT_ID")
    allow_main_chat = _parse_bool(os.getenv("ALLOW_MAIN_CHAT"), default=False)
    request_timeout = int(os.getenv("REQUEST_TIMEOUT") or 90)

    if not bot_token:
        raise ValueError(
            "BOT_TOKEN is required (ensure .env exists and is readable at"
            f" {env_path}, exists={env_path.exists()})"
        )

    def _envfloat(key, default):
        v = os.getenv(key)
        return float(v) if v is not None else default
    def _envint(key, default):
        v = os.getenv(key)
        return int(v) if v is not None else default

    x_username = (os.getenv("X_USERNAME") or "cortensor").lstrip("@").strip()
    x_fetch_mode = (os.getenv("X_FETCH_MODE") or "api").strip().lower()
    if x_fetch_mode not in {"api", "scrape"}:
        x_fetch_mode = "api"
    x_bearer_token = (os.getenv("X_BEARER_TOKEN") or "").strip()
    x_user_id = (os.getenv("X_USER_ID") or "").strip() or None
    if x_user_id is not None:
        # Defensive validation (X IDs are numeric strings)
        if not x_user_id.isdigit():
            raise ValueError("X_USER_ID must be a numeric string")
    x_scrape_rss_base_urls = _parse_str_list(os.getenv("X_SCRAPE_RSS_BASE_URLS"))
    if x_fetch_mode == "scrape" and not x_scrape_rss_base_urls:
        # Reasonable default; user can override with their own instance.
        x_scrape_rss_base_urls = ["https://nitter.net"]
    if x_fetch_mode == "api" and not x_bearer_token:
        raise ValueError("X_BEARER_TOKEN is required when X_FETCH_MODE=api")

    recap_interval_days = _envint("RECAP_INTERVAL_DAYS", 3)
    if recap_interval_days < 1:
        recap_interval_days = 3
    auto_recap_enabled = _parse_bool(os.getenv("AUTO_RECAP_ENABLED"), default=True)
    recap_post_hour_utc = _envint("RECAP_POST_HOUR_UTC", 7)
    if recap_post_hour_utc < 0 or recap_post_hour_utc > 23:
        recap_post_hour_utc = 7

    admin_only = _parse_bool(os.getenv("ADMIN_ONLY"), default=True)
    admin_user_ids = _parse_int_set(os.getenv("ADMIN_USER_IDS"))
    allowed_chat_ids = _parse_int_set(os.getenv("ALLOWED_CHAT_IDS"))
    return Settings(
        bot_token=bot_token,
        router_base_url=router_base_url,
        router_api_key=router_api_key,
        router_session_id=int(router_session_id) if router_session_id else None,
        target_chat_id=int(target_chat_id) if target_chat_id else None,
        side_chat_id=int(side_chat_id) if side_chat_id else None,
        allow_main_chat=allow_main_chat,
        request_timeout=request_timeout,
        router_prompt_type=_envint("ROUTER_PROMPT_TYPE", 0),
        router_prompt_template=os.getenv("ROUTER_PROMPT_TEMPLATE", ""),
        router_precommit_timeout=_envint("ROUTER_PRECOMMIT_TIMEOUT", 90),
        router_client_reference=os.getenv("ROUTER_CLIENT_REFERENCE", "user-request-123"),
        router_max_tokens=_envint("ROUTER_MAX_TOKENS", 1024),
        router_temperature=_envfloat("ROUTER_TEMPERATURE", 0.7),
        router_top_p=_envfloat("ROUTER_TOP_P", 0.95),
        router_top_k=_envint("ROUTER_TOP_K", 40),
        router_presence_penalty=_envfloat("ROUTER_PRESENCE_PENALTY", 0.0),
        router_frequency_penalty=_envfloat("ROUTER_FREQUENCY_PENALTY", 0.0),
        x_username=x_username,
        x_bearer_token=x_bearer_token,
        x_fetch_mode=x_fetch_mode,
        x_scrape_rss_base_urls=x_scrape_rss_base_urls,
        x_user_id=x_user_id,
        recap_interval_days=recap_interval_days,
        auto_recap_enabled=auto_recap_enabled,
        recap_post_hour_utc=recap_post_hour_utc,
        admin_only=admin_only,
        admin_user_ids=admin_user_ids,
        allowed_chat_ids=allowed_chat_ids,
    )
