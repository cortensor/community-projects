"""Source loading: live URLs and bundled offline samples.

The model never fetches anything. All network and filesystem access
happens here, in plain Python, so runs are inspectable and testable.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import httpx

MAX_CHARS = 24_000
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"


class _TextExtractor(HTMLParser):
    """Minimal HTML -> text extractor (stdlib only)."""

    _SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "div"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text + " ")

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


def _verify_from_env() -> str | bool:
    """Prefer the environment/system CA bundle over certifi.

    TLS-intercepting egress proxies present certificates signed by a
    local CA that lives in the system bundle / ``SSL_CERT_FILE``, not in
    certifi. Falling back to certifi (``True``) keeps normal setups
    unchanged.
    """
    import os

    for candidate in (
        os.environ.get("SSL_CERT_FILE"),
        "/etc/ssl/certs/ca-certificates.crt",
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return True


def _proxy_from_env() -> str | None:
    import os

    for key in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        value = os.environ.get(key)
        if value:
            return value
    return None


def fetch_url(url: str, timeout: float = 20.0) -> str:
    """Fetch a public URL and return readable text (bounded length).

    Uses an explicit proxy (from the standard env vars) with
    ``trust_env=False``: some environments export a ``NO_PROXY`` with
    bracketed IPv6 entries (``[::1]``) that httpx's URL-pattern parser
    rejects, which would otherwise crash every fetch.
    """
    headers = {"User-Agent": "FixBriefAgent/0.1 (Cortensor Hackathon #5)"}
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
        trust_env=False,
        proxy=_proxy_from_env(),
        verify=_verify_from_env(),
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        body = response.text
    if "html" in content_type or body.lstrip().lower().startswith("<!doctype html"):
        body = html_to_text(body)
    return body[:MAX_CHARS]


def list_samples(samples_dir: Path | None = None) -> list[str]:
    directory = samples_dir or SAMPLES_DIR
    if not directory.exists():
        return []
    return sorted(p.name for p in directory.glob("*.md"))


def load_sample(name: str, samples_dir: Path | None = None) -> str:
    """Load a bundled offline sample by filename (path traversal safe)."""
    directory = (samples_dir or SAMPLES_DIR).resolve()
    candidate = (directory / Path(name).name).resolve()
    if directory not in candidate.parents and candidate.parent != directory:
        raise ValueError(f"sample escapes samples dir: {name!r}")
    if not candidate.exists():
        available = ", ".join(list_samples(directory)) or "(none)"
        raise FileNotFoundError(f"sample not found: {name!r}. Available: {available}")
    return candidate.read_text(encoding="utf-8")[:MAX_CHARS]
