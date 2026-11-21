"""Normalisation + de-duplication keys.

The memory key is the normalised URL; the normalised name is the
fallback key when two list pages spell the same event's URL differently
(e.g. with/without a trailing slash or tracking parameters).
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "ref", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"https?://", url, re.IGNORECASE):
        url = "https://" + url.lstrip("/")
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
               if k.lower() not in _TRACKING_PARAMS),
        doseq=True,
    )
    return urlunparse((parsed.scheme.lower(), host, path, "", query, ""))


def normalize_name(name: str) -> str:
    text = unicodedata.normalize("NFKC", name or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def entry_key(url: str, name: str = "") -> str:
    norm_url = normalize_url(url)
    if norm_url:
        return "url:" + norm_url
    return "name:" + normalize_name(name)


def humanize_slug(slug: str) -> str:
    """Turn a URL slug into a readable placeholder name.

    The name is explicitly marked name_source="slug" by callers: it is a
    placeholder derived from the URL, not a title read off the page.
    """
    words = re.sub(r"[^a-z0-9]+", " ", slug.lower()).strip().split()
    return " ".join(w.capitalize() for w in words) or slug
