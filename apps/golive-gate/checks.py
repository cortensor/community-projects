"""Deterministic, read-only website checks used as OpenMinion tools.

Every function returns plain facts (status codes, tags found) so the model
judges evidence instead of guessing. Network calls have short timeouts.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

UA = "Mozilla/5.0 (GoLiveGate; +https://github.com/DesignMaster-Solutions/golive-gate)"
AI_BOTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User", "PerplexityBot",
    "ClaudeBot", "Claude-User", "Google-Extended", "Applebot-Extended",
]


def fetch(url: str, limit: int = 600_000) -> tuple[int, str, str]:
    """Return (status, final_url, body). Status 0 means the request failed."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.geturl(), r.read(limit).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read(limit).decode("utf-8", "replace")
    except Exception as e:  # DNS, TLS, timeout
        return 0, url, f"{type(e).__name__}: {e}"


def origin(url: str) -> str:
    p = urlparse(url if "://" in url else f"https://{url}")
    return f"{p.scheme}://{p.netloc}"


class _Head(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: dict[str, str] = {}
        self.title = ""
        self.h1: list[str] = []
        self.ld: list[str] = []
        self._in: str | None = None
        self._svg = 0  # <title> inside inline SVG icons is not the page title

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "svg":
            self._svg += 1
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key.lower()] = a.get("content", "")
        elif tag == "link" and a.get("rel"):
            for rel in a["rel"].lower().split():
                self.links.setdefault(rel, a.get("href", ""))
        elif tag == "html" and a.get("lang"):
            self.meta["html:lang"] = a["lang"]
        elif tag == "title" and (self._svg or self.title):
            return
        elif tag in ("title", "h1") or (tag == "script" and a.get("type") == "application/ld+json"):
            self._in = "ld" if tag == "script" else tag
            if tag == "h1":
                self.h1.append("")
            if tag == "script":
                self.ld.append("")

    def handle_endtag(self, tag):
        if tag == "svg" and self._svg:
            self._svg -= 1
        if tag in ("title", "h1", "script"):
            self._in = None

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in == "h1":
            self.h1[-1] += data
        elif self._in == "ld":
            self.ld[-1] += data


def _ld_types(blocks: list[str]) -> list[str]:
    types: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            types.extend(t if isinstance(t, list) else [t] if t else [])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for b in blocks:
        try:
            walk(json.loads(b))
        except ValueError:
            types.append("INVALID_JSON_LD")
    return sorted(set(map(str, types)))


def page_facts(url: str) -> dict:
    """Head tags of one page: title, description, canonical, Open Graph, JSON-LD types, h1."""
    status, final, body = fetch(url)
    p = _Head()
    if status:
        p.feed(body)
    m = p.meta
    return {
        "url": url, "status": status, "final_url": final,
        "title": p.title.strip(), "title_len": len(p.title.strip()),
        "description": m.get("description", ""), "description_len": len(m.get("description", "")),
        "canonical": p.links.get("canonical", ""),
        "og": {k: m.get(k, "") for k in ("og:title", "og:description", "og:image", "og:url")},
        "lang": m.get("html:lang", ""), "viewport": bool(m.get("viewport")),
        "favicon": bool(p.links.get("icon") or p.links.get("shortcut")),
        "apple_touch_icon": bool(p.links.get("apple-touch-icon")),
        "h1": [h.strip() for h in p.h1][:3],
        "json_ld_types": _ld_types(p.ld),
        "error": body if status == 0 else "",
    }


def robots_facts(site: str) -> dict:
    """robots.txt: whether it exists, sitemap lines, and which AI crawlers are fully blocked."""
    status, _, body = fetch(origin(site) + "/robots.txt")
    if status != 200:
        return {"status": status, "exists": False, "sitemaps": [], "ai_bots_blocked": []}
    groups: dict[str, list[str]] = {}
    agents: list[str] = []
    last_was_agent = False
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = (s.strip() for s in line.split(":", 1))
        k = k.lower()
        if k == "user-agent":
            agents = agents + [v] if last_was_agent else [v]
            last_was_agent = True
            continue
        last_was_agent = False
        if k == "disallow":
            for a in agents:
                groups.setdefault(a.lower(), []).append(v)
    def blocked(bot: str) -> bool:
        rules = groups.get(bot.lower(), groups.get("*", []))
        return "/" in rules
    return {
        "status": status, "exists": True,
        "sitemaps": re.findall(r"(?im)^\s*sitemap:\s*(\S+)", body),
        "ai_bots_blocked": [b for b in AI_BOTS if blocked(b)],
        "wildcard_blocks_all": "/" in groups.get("*", []),
    }


def sitemap_facts(site: str, declared: list[str] | None = None) -> dict:
    """First sitemap (declared in robots.txt or /sitemap.xml): status and URL count."""
    url = (declared or [origin(site) + "/sitemap.xml"])[0]
    status, _, body = fetch(url)
    return {"url": url, "status": status,
            "url_count": body.count("<loc>") if status == 200 else 0,
            "is_index": "<sitemapindex" in body}


def llms_facts(site: str) -> dict:
    """/llms.txt and /llms-full.txt: present as text and not an HTML fallback page."""
    out = {}
    for path in ("/llms.txt", "/llms-full.txt"):
        status, _, body = fetch(origin(site) + path, 200_000)
        is_html = body.lstrip()[:200].lower().startswith(("<!doctype", "<html"))
        out[path] = {"status": status, "ok": status == 200 and not is_html and len(body.strip()) > 50,
                     "bytes": len(body), "first_line": body.strip().splitlines()[0][:120] if body.strip() else ""}
    return out


def not_found_facts(site: str) -> dict:
    """A random missing path must answer HTTP 404 (soft-404 pages hurt indexing)."""
    status, final, _ = fetch(origin(site) + "/golive-gate-missing-page-7f3a")
    return {"status": status, "final_url": final, "real_404": status == 404}
