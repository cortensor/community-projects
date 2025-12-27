from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass(frozen=True)
class XPost:
    id: str
    created_at: dt.datetime
    text: str
    url: str


class XScraper:
    """Fetch posts by scraping *public* RSS feeds.

    This is intentionally not a direct X HTML/GraphQL scraper (very frequently blocked).
    Instead, it pulls from a public RSS endpoint (e.g. a Nitter instance or your own RSSHub).

    Configure via Settings -> base_urls (comma-separated in env).

    Notes:
    - Scraping can be fragile and may be restricted; use at your own risk and comply with relevant terms.
    - Filters are best-effort: exclude retweets; exclude replies to other accounts; keep self-threads; allow quote posts.
    """

    def __init__(self, *, base_urls: list[str], timeout_s: int = 20) -> None:
        self._base_urls = [u.rstrip("/") for u in base_urls if u.strip()]
        self._timeout_s = timeout_s

    @staticmethod
    def _strip_html(value: str) -> str:
        value = re.sub(r"<\s*br\s*/?\s*>", "\n", value, flags=re.IGNORECASE)
        value = re.sub(r"<[^>]+>", "", value)
        return value

    def _fetch_rss(self, url: str) -> bytes:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RecapTGBot/1.0; +https://example.invalid)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=self._timeout_s)
        if resp.status_code >= 400:
            raise RuntimeError(f"RSS fetch failed {resp.status_code} for {url}")
        content = resp.content or b""
        if not content:
            raise RuntimeError(f"RSS fetch returned empty body for {url}")
        return content

    def fetch_posts(
        self,
        *,
        username: str,
        start_time: dt.datetime,
        end_time: dt.datetime,
        max_results: int = 200,
    ) -> list[XPost]:
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("start_time and end_time must be timezone-aware")

        username = username.lstrip("@").strip()

        if not self._base_urls:
            raise RuntimeError("No RSS base URLs configured for scrape mode")

        # Import here to keep dependency optional for API-mode users.
        try:
            import feedparser  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "feedparser is required for X_FETCH_MODE=scrape (RSS). Install requirements.txt dependencies."
            ) from exc

        last_error: Optional[Exception] = None
        feed = None
        for base in self._base_urls:
            rss_url = f"{base}/{username}/rss"
            try:
                content = self._fetch_rss(rss_url)
                parsed = feedparser.parse(content)
                if getattr(parsed, "bozo", False) and getattr(parsed, "bozo_exception", None):
                    raise RuntimeError(f"RSS parse error for {rss_url}: {parsed.bozo_exception}")
                feed = parsed
                break
            except Exception as exc:
                last_error = exc
                continue

        if feed is None:
            raise RuntimeError(f"All RSS sources failed: {last_error}")

        if not (getattr(feed, "entries", None) or []):
            raise RuntimeError(
                "RSS feed returned no entries. Your RSS source may be blocked/down; "
                "try a different base URL in X_SCRAPE_RSS_BASE_URLS."
            )

        posts: list[XPost] = []
        # RSS is usually newest-first, but don't rely on it.
        for entry in getattr(feed, "entries", []) or []:
            link = str(getattr(entry, "link", "") or "")

            # Prefer published_parsed
            published_parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if not published_parsed:
                continue
            created_at = dt.datetime(*published_parsed[:6], tzinfo=dt.timezone.utc)

            if created_at < start_time or created_at >= end_time:
                continue

            title = str(getattr(entry, "title", "") or "").strip()
            summary = str(getattr(entry, "summary", "") or "").strip()
            text = (self._strip_html(summary) or title).strip()

            # Best-effort filters (RSS doesn't provide rich metadata):
            # - retweets are often prefixed with "RT".
            if title.startswith("RT ") or title.startswith("RT by "):
                continue

            # - replies often start with @someone; allow self-replies only.
            if text.startswith("@"):
                first = text.split(maxsplit=1)[0].lstrip("@").strip().lower()
                if first and first != username.lower():
                    continue

            # Extract tweet id from link if possible.
            tweet_id = ""
            m = re.search(r"/status/(\d+)", link)
            if m:
                tweet_id = m.group(1)
            elif getattr(entry, "id", None):
                tweet_id = str(getattr(entry, "id"))

            if not tweet_id or not text:
                continue

            posts.append(
                XPost(
                    id=tweet_id,
                    created_at=created_at,
                    text=text,
                    url=link or f"https://x.com/{username}/status/{tweet_id}",
                )
            )

            if len(posts) >= max_results:
                break

        posts.sort(key=lambda p: p.created_at)
        return posts
