import os
import re
import requests
from typing import Optional, Dict, Any

try:
    # Lightweight OAuth1 signing for Twitter API v2 calls (user context)
    from requests_oauthlib import OAuth1  # type: ignore
except Exception:  # pragma: no cover - optional dep
    OAuth1 = None  # type: ignore

_X_STATUS_RE = re.compile(r"https?://(?:x|twitter)\.com/[^/]+/status/(\d+)")
_X_URL_RE = re.compile(r"https?://(?:x|twitter)\.com/[^\s]+/status/\d+[^\s]*")

def parse_x_status_id(url: str) -> Optional[str]:
    m = _X_STATUS_RE.search(url)
    return m.group(1) if m else None

def fetch_x_tweet_json(status_id: str, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    # 1) Try official Twitter API v2 if credentials are present
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    if OAuth1 and all([api_key, api_secret, access_token, access_secret]):
        try:
            url = f"https://api.twitter.com/2/tweets/{status_id}"
            params = {
                "expansions": "author_id,attachments.media_keys",
                "tweet.fields": "text,lang,public_metrics,author_id",
                "user.fields": "name,username",
                "media.fields": "type",
            }
            auth = OAuth1(api_key, api_secret, access_token, access_secret)
            r = requests.get(url, params=params, auth=auth, timeout=timeout)
            if r.status_code == 200:
                j = r.json()
                data = j.get("data") or {}
                if not data or not data.get("text"):
                    raise ValueError("No tweet text")
                # Build a normalized shape compatible with build_reply_context_from_x
                includes = j.get("includes", {})
                users = {u.get("id"): u for u in includes.get("users", [])}
                media = includes.get("media", []) or []
                author = users.get(data.get("author_id") or "") or {}
                photos = [m for m in media if m.get("type") == "photo"]
                has_video = any(m.get("type") in ("video", "animated_gif") for m in media)
                normalized = {
                    "text": data.get("text", ""),
                    "user": {
                        "name": author.get("name"),
                        "screen_name": author.get("username"),
                    },
                    # only counts matter for context summary
                    "photos": [{} for _ in photos],
                    "video": True if has_video else None,
                }
                return normalized
        except Exception:
            # fall back to public endpoint below
            pass

    # 1b) Try OAuth2 bearer if provided (often more reliable on v2)
    bearer = os.getenv("TWITTER_BEARER_TOKEN")
    if bearer:
        try:
            url = f"https://api.twitter.com/2/tweets/{status_id}"
            params = {
                "expansions": "author_id,attachments.media_keys",
                "tweet.fields": "text,lang,public_metrics,author_id",
                "user.fields": "name,username",
                "media.fields": "type",
            }
            headers = {"Authorization": f"Bearer {bearer}"}
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                j = r.json()
                data = j.get("data") or {}
                if not data or not data.get("text"):
                    raise ValueError("No tweet text")
                includes = j.get("includes", {})
                users = {u.get("id"): u for u in includes.get("users", [])}
                media = includes.get("media", []) or []
                author = users.get(data.get("author_id") or "") or {}
                photos = [m for m in media if m.get("type") == "photo"]
                has_video = any(m.get("type") in ("video", "animated_gif") for m in media)
                normalized = {
                    "text": data.get("text", ""),
                    "user": {
                        "name": author.get("name"),
                        "screen_name": author.get("username"),
                    },
                    "photos": [{} for _ in photos],
                    "video": True if has_video else None,
                }
                return normalized
        except Exception:
            pass

    # 2) Fallback: public syndication endpoint (no auth)
    try:
        resp = requests.get(
            "https://cdn.syndication.twimg.com/widgets/tweet",
            params={"id": status_id, "lang": "en"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, dict) or not data.get("text"):
            return None
        return data
    except Exception:
        return None

def fetch_x_tweet_json_from_text(source_text: str, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
    """Try to resolve a tweet from any text containing a tweet URL.
    Attempts by ID, then by URL-param syndication.
    """
    if not source_text:
        return None
    # Try by ID first
    sid = parse_x_status_id(source_text) or ""
    data = fetch_x_tweet_json(sid, timeout=timeout) if sid else None
    if data:
        return data
    # Try by URL form
    m = _X_URL_RE.search(source_text)
    if not m:
        return None
    try:
        resp = requests.get(
            "https://cdn.syndication.twimg.com/widgets/tweet",
            params={"url": m.group(0), "lang": "en"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        j = resp.json()
        if isinstance(j, dict) and j.get("text"):
            return j
    except Exception:
        return None
    return None

def build_reply_context_from_x(data: Dict[str, Any], source_url: Optional[str] = None) -> str:
    user = data.get("user") or {}
    author = user.get("name") or user.get("screen_name") or ""
    handle = user.get("screen_name") or ""
    text = data.get("text") or ""
    text = text.replace("\r", " ").replace("\n\n", "\n").strip()

    media_bits = []
    photos = data.get("photos") or []
    if isinstance(photos, list) and photos:
        media_bits.append(f"{len(photos)} photo(s)")
    video = data.get("video")
    if video:
        media_bits.append("video")
    media_str = f"\nMedia: {', '.join(media_bits)}" if media_bits else ""

    # Cleaned permalink
    link = None
    if source_url:
        sid = parse_x_status_id(source_url)
        if sid:
            link = f"https://x.com/i/web/status/{sid}"
    src = f"\nLink: {link or source_url}" if (link or source_url) else ""
    by = f" by {author} (@{handle})" if (author or handle) else ""
    header = f"Original post{by}:\n"
    return f"{header}{text}{media_str}{src}".strip()

def build_basic_context_from_url(source_url: str) -> str:
    """Best-effort context when we only have an X/Twitter URL and cannot fetch content.
    Includes the author handle if present and a cleaned Link line.
    """
    if not source_url:
        return ""
    # Try to extract handle and status id
    m = re.search(r"https?://(?:x|twitter)\.com/([^/]+)/status/(\d+)", source_url)
    handle = m.group(1) if m else None
    sid = m.group(2) if m else parse_x_status_id(source_url)
    clean = f"https://x.com/i/web/status/{sid}" if sid else source_url
    by = f" by @{handle}" if handle else ""
    header = f"Original post{by}:\n"
    return f"{header}Link: {clean}".strip()
