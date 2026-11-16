"""Read-only @tool functions, SSRF-guarded URL reader, and ClaimDossier fixture loaders."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx
from openminion.tools import tool

from cortensor_verifier.models import ClaimDossier

_CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
_BLOCKED_LOCAL_SUFFIXES = (".localhost", ".local", ".internal")
_HTML_SKIP_TAGS = frozenset({"script", "style", "noscript"})
_HTML_BLOCK_TAGS = frozenset(
    {
        "article",
        "blockquote",
        "br",
        "dd",
        "div",
        "dt",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "pre",
        "section",
        "td",
        "th",
        "tr",
    }
)
_MAX_URL_REDIRECTS = 5
_MAX_HTML_BYTES = 512 * 1024
_MAX_EXCERPT_CHARS = 2000


class _HTMLTextExtractor(HTMLParser):
    """Strip <script>/<style>/<noscript> tags and extract title + normalized text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        lowered = tag.lower()
        if lowered in _HTML_SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if lowered == "title":
            self._in_title = True
        elif lowered in _HTML_BLOCK_TAGS and not self._in_title:
            self._text_parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if self._skip_depth == 0 and not self._in_title and tag.lower() in _HTML_BLOCK_TAGS:
            self._text_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in _HTML_SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if lowered == "title":
            self._in_title = False
        elif self._skip_depth == 0 and not self._in_title and lowered in _HTML_BLOCK_TAGS:
            self._text_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_parts.append(data)
        else:
            self._text_parts.append(data)

    def extract(self) -> tuple[str, str]:
        title = " ".join("".join(self._title_parts).split())
        body = " ".join("".join(self._text_parts).split())
        return title, body


def resolve_default_fixture_path() -> Path:
    """Locate fixtures/claim_dossiers.json relative to the repository or cwd."""
    package_root = Path(__file__).resolve().parents[2]
    candidate = package_root / "fixtures" / "claim_dossiers.json"
    if candidate.exists():
        return candidate
    return Path.cwd() / "fixtures" / "claim_dossiers.json"


def _load_fixture_bundle(fixture_path: str | Path | None = None) -> dict[str, Any]:
    target = Path(fixture_path) if fixture_path is not None else resolve_default_fixture_path()
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Fixture file {target} must decode to a JSON object.")
    return data


def _load_fixture_evidence_sources(
    fixture_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    target = Path(fixture_path) if fixture_path is not None else resolve_default_fixture_path()
    if not target.exists():
        return []
    bundle = _load_fixture_bundle(target)
    return [
        record
        for record in bundle.get("evidence_sources", [])
        if isinstance(record, dict)
    ]


def _merged_evidence_sources(
    *,
    fixture_path: str | Path | None = None,
    dossier: ClaimDossier | None = None,
) -> list[dict[str, Any]]:
    inline_sources: list[dict[str, Any]] = []
    if dossier is not None and isinstance(dossier.metadata, dict):
        raw_inline = dossier.metadata.get("evidence_sources", [])
        if isinstance(raw_inline, list):
            inline_sources = [record for record in raw_inline if isinstance(record, dict)]

    fixture_sources = _load_fixture_evidence_sources(fixture_path)
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for record in [*inline_sources, *fixture_sources]:
        sid = record.get("source_id")
        if isinstance(sid, str) and sid:
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
        merged.append(record)
    return merged


def list_claim_ids(fixture_path: str | Path | None = None) -> list[str]:
    """Return available claim_id values from the fixture catalog."""
    bundle = _load_fixture_bundle(fixture_path)
    return [
        str(item["claim_id"])
        for item in bundle.get("dossiers", [])
        if isinstance(item, dict) and item.get("claim_id")
    ]


def load_claim_dossier(
    claim_id: str,
    *,
    fixture_path: str | Path | None = None,
) -> ClaimDossier:
    """Load and validate a ClaimDossier by claim_id from the fixture bundle."""
    bundle = _load_fixture_bundle(fixture_path)
    for raw in bundle.get("dossiers", []):
        if isinstance(raw, dict) and raw.get("claim_id") == claim_id:
            return ClaimDossier.model_validate(raw)
    available = ", ".join(list_claim_ids(fixture_path))
    raise KeyError(f"Unknown claim_id {claim_id!r}. Available fixtures: {available}")


def load_dossier_from_file(path: str | Path) -> ClaimDossier:
    """Load and validate a standalone ClaimDossier JSON file."""
    target = Path(path)
    return ClaimDossier.model_validate_json(target.read_text(encoding="utf-8"))


def _tokenize(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9-]+", text.lower()) if len(tok) >= 2}


def _load_dossier_payload(
    claim_id: str,
    *,
    fixture_path: str | Path | None = None,
    dossier: ClaimDossier | None = None,
) -> dict[str, Any]:
    if dossier is not None and claim_id == dossier.claim_id:
        return {"found": True, "dossier": dossier.model_dump(mode="json")}
    try:
        loaded = load_claim_dossier(claim_id, fixture_path=fixture_path)
    except (KeyError, FileNotFoundError) as exc:
        return {"found": False, "claim_id": claim_id, "error": str(exc)}
    return {"found": True, "dossier": loaded.model_dump(mode="json")}


def _search_evidence_records(
    sources: Sequence[dict[str, Any]],
    query: str,
    limit: int = 5,
) -> dict[str, Any]:
    query_tokens = _tokenize(query)
    capped_limit = min(max(int(limit), 1), 10)

    scored: list[tuple[int, dict[str, Any]]] = []
    for record in sources:
        haystack = " ".join(
            [
                str(record.get("source_id", "")),
                str(record.get("title", "")),
                str(record.get("excerpt", "")),
                " ".join(str(kw) for kw in record.get("keywords", [])),
            ]
        )
        record_tokens = _tokenize(haystack)
        overlap = len(query_tokens & record_tokens) if query_tokens else 1
        if overlap > 0:
            scored.append(
                (
                    overlap,
                    {
                        "source_id": record.get("source_id"),
                        "title": record.get("title"),
                        "url": record.get("url"),
                        "published_at": record.get("published_at"),
                        "snippet": str(record.get("excerpt", ""))[:240],
                        "score": overlap,
                    },
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    return {
        "query": query,
        "matches": [item[1] for item in scored[:capped_limit]],
    }


def _fetch_source_from_records(
    sources: Sequence[dict[str, Any]],
    source_id: str,
) -> dict[str, Any]:
    for record in sources:
        if record.get("source_id") == source_id:
            return {
                "found": True,
                "source_id": record.get("source_id"),
                "title": record.get("title"),
                "url": record.get("url"),
                "published_at": record.get("published_at"),
                "excerpt": record.get("excerpt"),
            }
    return {"found": False, "source_id": source_id, "error": "Unknown source_id"}


def _is_disallowed_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        if _is_disallowed_ip(ip.ipv4_mapped):
            return True
    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_NETWORK:
        return True
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or not ip.is_global
    )


def _validate_public_hostname(
    hostname: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if "%" in hostname:
        raise ValueError("IPv6 zone identifiers are not allowed.")
    host_lower = hostname.lower()
    if host_lower == "localhost" or host_lower.endswith(_BLOCKED_LOCAL_SUFFIXES):
        raise ValueError(f"Blocked local/private hostname: {hostname!r}.")
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return None
    if _is_disallowed_ip(literal_ip):
        raise ValueError(f"Blocked non-public IP address: {literal_ip}.")
    return literal_ip


def _resolve_validated_public_ips(hostname: str, port: int) -> list[str]:
    clean_host = str(hostname or "").strip().rstrip(".")
    if not clean_host:
        raise ValueError("URL must contain a valid hostname.")
    literal_ip = _validate_public_hostname(clean_host)
    if literal_ip is not None:
        return [str(literal_ip)]
    try:
        addr_infos = socket.getaddrinfo(clean_host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError(f"DNS resolution failed for {clean_host!r}: {exc}") from exc
    if not addr_infos:
        raise ValueError(f"DNS resolution returned no addresses for {clean_host!r}.")
    resolved_ips: list[str] = []
    for info in addr_infos:
        addr_text = str(info[4][0]).split("%", 1)[0]
        resolved_ip = ipaddress.ip_address(addr_text)
        if _is_disallowed_ip(resolved_ip):
            raise ValueError(
                f"Blocked non-public resolved IP {resolved_ip} for hostname {clean_host!r}."
            )
        ip_str = str(resolved_ip)
        if ip_str not in resolved_ips:
            resolved_ips.append(ip_str)
    return resolved_ips


def _validate_public_url(url: str, *, allow_private_network: bool) -> str:
    raw_url = str(url or "").strip()
    if not raw_url:
        raise ValueError("URL must not be empty.")
    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme {parsed.scheme!r}; only http and https are allowed."
        )
    if parsed.username or parsed.password:
        raise ValueError("Embedded URL credentials are not allowed.")
    hostname = (parsed.hostname or "").strip().rstrip(".")
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    if not allow_private_network:
        port = parsed.port or (443 if scheme == "https" else 80)
        _resolve_validated_public_ips(hostname, port)

    return raw_url


class _SSRFBlockingNetworkBackend(httpcore.SyncBackend):
    """Resolve DNS once at TCP dial time, reject non-public IPs, and connect directly by IP."""

    def __init__(self, *, allow_private_network: bool) -> None:
        self._allow_private_network = allow_private_network

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Any = None,
    ) -> Any:
        if self._allow_private_network:
            return super().connect_tcp(
                host,
                port,
                timeout=timeout,
                local_address=local_address,
                socket_options=socket_options,
            )
        validated_ips = _resolve_validated_public_ips(host, port)
        last_exc: Exception | None = None
        for candidate_ip in validated_ips:
            try:
                return super().connect_tcp(
                    candidate_ip,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except httpcore.ConnectError as exc:
                last_exc = exc
        assert last_exc is not None  # pragma: no cover - resolved_ips is non-empty
        raise last_exc


def _fetch_public_url_excerpt_impl(
    url: str,
    *,
    allow_private_network: bool = False,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    current_url = str(url or "").strip()
    visited: set[str] = set()
    transport = httpx.HTTPTransport(trust_env=False)
    pool = getattr(transport, "_pool", None)
    if pool is not None and hasattr(pool, "_network_backend"):
        pool._network_backend = _SSRFBlockingNetworkBackend(
            allow_private_network=allow_private_network
        )
    try:
        with httpx.Client(
            timeout=float(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"User-Agent": "cortensor-openminion-verifier/0.1.2"},
        ) as client:
            for _ in range(_MAX_URL_REDIRECTS + 1):
                _validate_public_url(
                    current_url,
                    allow_private_network=allow_private_network,
                )
                if current_url in visited:
                    return {
                        "ok": False,
                        "url": current_url,
                        "error": "Redirect loop detected.",
                    }
                visited.add(current_url)

                with client.stream("GET", current_url) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            return {
                                "ok": False,
                                "url": current_url,
                                "error": f"HTTP {response.status_code} redirect missing Location header.",
                            }
                        current_url = urljoin(current_url, location.strip())
                        continue

                    final_url = str(response.url)
                    if response.status_code >= 400:
                        return {
                            "ok": False,
                            "url": final_url,
                            "error": f"HTTP {response.status_code}",
                        }

                    chunks: list[bytes] = []
                    total_bytes = 0
                    for chunk in response.iter_bytes():
                        remaining = _MAX_HTML_BYTES - total_bytes
                        if remaining <= 0:
                            break
                        if len(chunk) > remaining:
                            chunks.append(chunk[:remaining])
                            total_bytes += remaining
                            break
                        chunks.append(chunk)
                        total_bytes += len(chunk)

                    encoding = response.encoding or "utf-8"
                    raw_text = b"".join(chunks).decode(encoding, errors="replace")
                    content_type = str(response.headers.get("content-type", "")).lower()
                    lowered = raw_text.lower()
                    if (
                        "html" in content_type
                        or "<html" in lowered
                        or "<body" in lowered
                        or "<title" in lowered
                    ):
                        parser = _HTMLTextExtractor()
                        parser.feed(raw_text)
                        parser.close()
                        title, body = parser.extract()
                    else:
                        title = ""
                        body = " ".join(raw_text.split())

                    return {
                        "ok": True,
                        "url": final_url,
                        "title": title,
                        "excerpt": body[:_MAX_EXCERPT_CHARS],
                    }

        return {
            "ok": False,
            "url": current_url,
            "error": f"Exceeded maximum redirect hops ({_MAX_URL_REDIRECTS}).",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "url": current_url or str(url),
            "error": str(exc) or type(exc).__name__,
        }


def build_scoped_verifier_tools(
    *,
    fixture_path: str | Path | None = None,
    dossier: ClaimDossier | None = None,
    allow_private_network: bool = False,
    timeout_seconds: float = 8.0,
) -> tuple[Any, ...]:
    """Build READ_ONLY verifier tools scoped to a fixture catalog, active dossier, and SSRF policy."""
    resolved_fixture_path = Path(fixture_path) if fixture_path is not None else None

    @tool(
        name="load_delphi_market_fixture",
        min_scope="READ_ONLY",
        idempotent=True,
    )
    def _scoped_load_delphi_market_fixture(claim_id: str) -> dict[str, Any]:
        """Load a Delphi/prediction-market claim dossier fixture by claim_id."""
        return _load_dossier_payload(
            claim_id,
            fixture_path=resolved_fixture_path,
            dossier=dossier,
        )

    @tool(
        name="search_public_evidence",
        min_scope="READ_ONLY",
        idempotent=True,
    )
    def _scoped_search_public_evidence(query: str, limit: int = 5) -> dict[str, Any]:
        """Search curated and dossier-inline public evidence records matching the query string."""
        sources = _merged_evidence_sources(
            fixture_path=resolved_fixture_path,
            dossier=dossier,
        )
        return _search_evidence_records(sources, query, limit=limit)

    @tool(
        name="fetch_source_excerpt",
        min_scope="READ_ONLY",
        idempotent=True,
    )
    def _scoped_fetch_source_excerpt(source_id: str) -> dict[str, Any]:
        """Fetch the full verifiable excerpt and metadata for a public evidence source_id."""
        sources = _merged_evidence_sources(
            fixture_path=resolved_fixture_path,
            dossier=dossier,
        )
        return _fetch_source_from_records(sources, source_id)

    @tool(
        name="fetch_public_url_excerpt",
        min_scope="READ_ONLY",
        idempotent=True,
    )
    def _scoped_fetch_public_url_excerpt(url: str) -> dict[str, Any]:
        """Fetch and extract a clean text excerpt from a public http/https URL (SSRF-guarded)."""
        return _fetch_public_url_excerpt_impl(
            url,
            allow_private_network=allow_private_network,
            timeout_seconds=timeout_seconds,
        )

    return (
        _scoped_load_delphi_market_fixture,
        _scoped_search_public_evidence,
        _scoped_fetch_source_excerpt,
        _scoped_fetch_public_url_excerpt,
    )


READ_ONLY_VERIFIER_TOOLS: tuple[Any, ...] = build_scoped_verifier_tools()
(
    load_delphi_market_fixture,
    search_public_evidence,
    fetch_source_excerpt,
    fetch_public_url_excerpt,
) = READ_ONLY_VERIFIER_TOOLS


def assert_read_only_tools(tools: Iterable[Any]) -> list[Any]:
    """Ensure every configured tool declares READ_ONLY min_scope and is non-dangerous."""
    validated: list[Any] = []
    for item in tools:
        decl = getattr(item, "tool_decl", None)
        if decl is None:
            raise ValueError(
                f"Tool {item!r} must be decorated with @tool(min_scope='READ_ONLY')."
            )
        if decl.min_scope != "READ_ONLY" or decl.dangerous:
            raise ValueError(
                f"Tool {decl.name!r} violates READ_ONLY boundary "
                f"(min_scope={decl.min_scope!r}, dangerous={decl.dangerous!r})."
            )
        validated.append(item)
    return validated


def _append_publication_record(
    *,
    log_path: Path,
    claim_id: str,
    final_verdict: str,
    agreement_score: float,
    mean_confidence: float,
    requires_human_review: bool,
    session_id: str,
    summary: str,
) -> dict[str, Any]:
    record = {
        "claim_id": claim_id,
        "final_verdict": final_verdict,
        "agreement_score": round(float(agreement_score), 6),
        "mean_confidence": round(float(mean_confidence), 6),
        "requires_human_review": bool(requires_human_review),
        "session_id": session_id,
        "summary": summary,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {"published": True, "log_path": str(log_path), **record}


def make_publish_consensus_verdict_tool(log_path: str | Path) -> Any:
    """Create a path-bound dangerous WRITE_SAFE publication tool for Handoff publisher agents."""
    target_path = Path(log_path)

    @tool(
        name="publish_consensus_verdict",
        min_scope="WRITE_SAFE",
        dangerous=True,
        idempotent=False,
    )
    def _bound_publish_consensus_verdict(
        claim_id: str,
        final_verdict: str,
        agreement_score: float,
        mean_confidence: float,
        requires_human_review: bool = False,
        session_id: str = "",
        summary: str = "",
    ) -> dict[str, Any]:
        """Publish a verified ConsensusVerdict to the bound publication log."""
        return _append_publication_record(
            log_path=target_path,
            claim_id=claim_id,
            final_verdict=final_verdict,
            agreement_score=agreement_score,
            mean_confidence=mean_confidence,
            requires_human_review=requires_human_review,
            session_id=session_id,
            summary=summary,
        )

    return _bound_publish_consensus_verdict


publish_consensus_verdict = make_publish_consensus_verdict_tool(
    ".openminion-state/published_verdicts.jsonl"
)
