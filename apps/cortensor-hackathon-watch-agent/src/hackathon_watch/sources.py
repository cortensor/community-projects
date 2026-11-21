"""Public list-page fetchers + parsers (deterministic, no model calls).

Verified against live pages on 2026-11-17 (see docs/WHAT_WE_LEARNED.md):

- DoraHacks ``https://dorahacks.io/`` — HTTP 200, ~522 KB. The hackathon
  listing itself is a JS-rendered Vue SPA: the static HTML only exposes
  a handful of ``/hackathon/<slug>`` links (featured / testimonial
  cards). Names are therefore derived from the slug and marked
  ``name_source="slug"`` — a placeholder, not a page title.
- Devfolio ``https://devfolio.co/hackathons`` — HTTP 200, ~191 KB,
  server-rendered cards: ``<a href="https://<slug>.devfolio.co/">
  <h3>Real Name</h3></a>``. Real names; deadline/prize are NOT on the
  list page, so they stay None (never guessed).
- Kaggle ``https://www.kaggle.com/competitions`` — HTTP 200 but the body
  is a Google reCAPTCHA challenge page, not a competition list. Plain
  HTTP fetch cannot read it; recorded as ``unavailable`` with evidence,
  never faked. (Matches the 2026-11-16 baseline note: JS-rendered / 429.)

Only public list pages are fetched. No login, no robots-violating crawl:
Devfolio's robots.txt allows all; DoraHacks' robots.txt is itself behind
a human-verification page from this network, so we fetch only the two
public pages above at low frequency and record that fact.
"""

from __future__ import annotations

import html as html_lib
import re
from dataclasses import dataclass

import httpx

from .config import fix_proxy_env
from .models import HackathonEntry
from .normalize import humanize_slug, normalize_url

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "Chrome/120 Safari/537.36")

SOURCES: dict[str, dict[str, str]] = {
    "dorahacks": {"label": "DoraHacks",
                  "list_url": "https://dorahacks.io/",
                  "alt_url": "https://dorahacks.io/hackathon"},
    "devfolio": {"label": "Devfolio",
                 "list_url": "https://devfolio.co/hackathons"},
    "kaggle": {"label": "Kaggle",
               "list_url": "https://www.kaggle.com/competitions"},
}


class SourceUnavailable(RuntimeError):
    """The list page could not be read as a list (bot wall, JS-only, 429...)."""


@dataclass
class FetchOutcome:
    source: str
    url: str
    entries: list[HackathonEntry]
    detail: str = ""


def fetch_html(url: str, timeout_sec: float = 25.0,
               transport: httpx.BaseTransport | None = None) -> str:
    fix_proxy_env()
    with httpx.Client(transport=transport, timeout=timeout_sec,
                      follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": USER_AGENT})
    if resp.status_code == 429:
        raise SourceUnavailable(f"HTTP 429 rate-limited on {url}")
    if resp.status_code >= 400:
        raise SourceUnavailable(f"HTTP {resp.status_code} on {url}")
    return resp.text


def parse_dorahacks(html_text: str) -> list[HackathonEntry]:
    """Extract /hackathon/<slug> links; name from slug (placeholder)."""
    seen: dict[str, HackathonEntry] = {}
    for slug in re.findall(r'href="/hackathon/([a-z0-9][a-z0-9-]*)"', html_text):
        if slug in ("hackathon",):
            continue
        url = normalize_url(f"https://dorahacks.io/hackathon/{slug}")
        if url in seen:
            continue
        seen[url] = HackathonEntry(
            name=humanize_slug(slug), url=url, source="dorahacks",
            name_source="slug",
            notes="Name derived from URL slug; list page is JS-rendered, "
                  "verify the real title on the official page.")
    return list(seen.values())


_EXCLUDED_DEVFOLIO_SUBDOMAINS = {"assets", "guide", "status", "api", "www"}


def parse_devfolio(html_text: str) -> list[HackathonEntry]:
    """Extract server-rendered cards: subdomain link + <h3> real name."""
    seen: dict[str, HackathonEntry] = {}
    pattern = re.compile(
        r'<a href="(https://[a-z0-9-]+\.devfolio\.co/)"[^>]*>'
        r'\s*<h3[^>]*>([^<]+)</h3>\s*</a>', re.IGNORECASE)
    for url, raw_name in pattern.findall(html_text):
        subdomain = url.split("://", 1)[1].split(".", 1)[0]
        if subdomain in _EXCLUDED_DEVFOLIO_SUBDOMAINS:
            continue
        name = html_lib.unescape(raw_name).strip()
        if not name:
            continue
        norm = normalize_url(url)
        if norm in seen:
            continue
        seen[norm] = HackathonEntry(name=name, url=norm, source="devfolio",
                                    name_source="page")
    return list(seen.values())


def parse_kaggle(html_text: str) -> list[HackathonEntry]:
    """Kaggle list page: fail closed when the body is a bot wall."""
    lowered = html_text.lower()
    if "recaptcha" in lowered or "challengepage" in lowered:
        raise SourceUnavailable(
            "Kaggle competitions page returned a reCAPTCHA challenge page "
            "(~20 KB) instead of a competition list; plain HTTP fetch "
            "cannot read it.")
    links = re.findall(r'href="(/competitions/[a-z0-9][a-z0-9-]*)"', html_text)
    if not links:
        raise SourceUnavailable(
            "Kaggle competitions page contained no /competitions/<slug> "
            "links in static HTML (JS-rendered or blocked).")
    seen: dict[str, HackathonEntry] = {}
    for slug in links:
        url = normalize_url(f"https://www.kaggle.com{slug}")
        if url not in seen:
            seen[url] = HackathonEntry(
                name=humanize_slug(slug.rsplit("/", 1)[-1]), url=url,
                source="kaggle", name_source="slug")
    return list(seen.values())


PARSERS = {"dorahacks": parse_dorahacks, "devfolio": parse_devfolio,
           "kaggle": parse_kaggle}


def fetch_source(source: str, transport: httpx.BaseTransport | None = None,
                 html_override: str | None = None) -> FetchOutcome:
    """Fetch + parse one source. ``html_override`` is for tests/fixtures."""
    if source not in SOURCES:
        raise ValueError(f"unknown source {source!r}; choose from {sorted(SOURCES)}")
    cfg = SOURCES[source]
    if html_override is not None:
        entries = PARSERS[source](html_override)
        return FetchOutcome(source=source, url=cfg["list_url"],
                            entries=entries, detail="fixture HTML")
    try:
        html_text = fetch_html(cfg["list_url"], transport=transport)
    except SourceUnavailable:
        if source == "dorahacks":
            # The /hackathon listing page is the same SPA; try it once as
            # a fallback before declaring the source unavailable.
            html_text = fetch_html(cfg["alt_url"], transport=transport)
        else:
            raise
    entries = PARSERS[source](html_text)
    return FetchOutcome(source=source, url=cfg["list_url"], entries=entries,
                        detail=f"{len(entries)} entries parsed from list page")
