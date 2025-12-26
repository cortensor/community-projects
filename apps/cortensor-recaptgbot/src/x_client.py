from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp


@dataclass(frozen=True)
class XPost:
    id: str
    created_at: dt.datetime
    text: str
    url: str


class XClient:
    """Minimal X API v2 client.

    Uses bearer token auth (X_BEARER_TOKEN).
    """

    def __init__(self, bearer_token: str, session: aiohttp.ClientSession) -> None:
        self._bearer_token = bearer_token
        self._session = session
        self._user_id_cache: dict[str, str] = {}

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._bearer_token}"}

    async def get_user_id(self, username: str) -> str:
        username = username.lstrip("@").strip()
        cached = self._user_id_cache.get(username.lower())
        if cached:
            return cached
        url = f"https://api.x.com/2/users/by/username/{username}"
        params = {"user.fields": "id"}
        data = await _request_json_with_retries(
            self._session,
            method="GET",
            url=url,
            headers=self._headers,
            params=params,
        )
        user = (data or {}).get("data") or {}
        user_id = user.get("id")
        if not user_id:
            raise RuntimeError(f"Could not resolve X user id for @{username}: {data!r}")
        user_id = str(user_id)
        self._user_id_cache[username.lower()] = user_id
        return user_id

    async def fetch_original_posts(
        self,
        *,
        user_id: str,
        username: str,
        start_time: dt.datetime,
        end_time: dt.datetime,
        max_pages: int = 1,
    ) -> list[XPost]:
        """Fetches posts from a user's timeline (Mode B).

        Rules implemented:
        - Include: posts, quote posts, retweets, and self-replies (threads).
        - Exclude: replies to other accounts.

        Note: default max_pages=1 (up to 100 tweets) to minimize API calls on Free plan.
        """
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("start_time and end_time must be timezone-aware")

        url = f"https://api.x.com/2/users/{user_id}/tweets"
        params: dict[str, Any] = {
            "tweet.fields": "created_at,referenced_tweets,in_reply_to_user_id",
            "start_time": start_time.isoformat().replace("+00:00", "Z"),
            "end_time": end_time.isoformat().replace("+00:00", "Z"),
            "max_results": 100,
        }

        posts: list[XPost] = []
        pagination_token: Optional[str] = None

        for _ in range(max_pages):
            if pagination_token:
                params["pagination_token"] = pagination_token
            elif "pagination_token" in params:
                params.pop("pagination_token", None)

            data = await _request_json_with_retries(
                self._session,
                method="GET",
                url=url,
                headers=self._headers,
                params=params,
            )

            for item in (data or {}).get("data") or []:
                # Drop replies to other accounts, but allow self-replies (threads).
                in_reply_to_user_id = item.get("in_reply_to_user_id")
                if in_reply_to_user_id is not None and str(in_reply_to_user_id) != str(user_id):
                    continue

                created_at_raw = item.get("created_at")
                if not created_at_raw:
                    continue
                created_at = _parse_x_datetime(created_at_raw)

                tweet_id = str(item.get("id"))
                text = (item.get("text") or "").strip()
                if not tweet_id or not text:
                    continue
                posts.append(
                    XPost(
                        id=tweet_id,
                        created_at=created_at,
                        text=text,
                        url=f"https://x.com/{username}/status/{tweet_id}",
                    )
                )

            meta = (data or {}).get("meta") or {}
            pagination_token = meta.get("next_token")
            if not pagination_token:
                break

        posts.sort(key=lambda p: p.created_at)
        return posts


def _parse_x_datetime(value: str) -> dt.datetime:
    # Example: 2025-12-16T12:34:56.000Z
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


async def _request_json_with_retries(
    session: aiohttp.ClientSession,
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    params: Optional[dict[str, Any]] = None,
    max_attempts: int = 5,
) -> Any:
    """Best-effort retry wrapper for X API.

    Handles:
    - 429 Too Many Requests: returns an error (no automatic retry).
    - transient 5xx: exponential backoff with jitter.
    """
    attempt = 0
    while True:
        attempt += 1
        async with session.request(method, url, headers=headers, params=params) as resp:
            data = await resp.json(content_type=None)

            if resp.status < 300:
                return data

            if attempt >= max_attempts:
                raise RuntimeError(f"X API error {resp.status}: {data!r}")

            if resp.status == 429:
                raise RuntimeError(
                    "X API rate limit hit (429 Too Many Requests). "
                    "Please wait 15 minutes and try again."
                )

            if 500 <= resp.status <= 599:
                base = 1.0 * (2 ** (attempt - 1))
                wait_s = min(base + random.uniform(0, 0.5), 30.0)
                await asyncio_sleep(wait_s)
                continue

            raise RuntimeError(f"X API error {resp.status}: {data!r}")


async def asyncio_sleep(seconds: float) -> None:
    # isolated for testability and to keep imports localized
    import asyncio

    await asyncio.sleep(seconds)
