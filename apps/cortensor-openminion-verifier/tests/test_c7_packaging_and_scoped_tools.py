"""Tests for C7: MIT relicensing, SDK pin, upstream metadata, scoped evidence tools, and calibration metadata."""

from __future__ import annotations

import datetime
import json
import re
import socket
import sys
import threading
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from openminion.tools import tool

import tests.conftest as test_conftest
from cortensor_verifier.auditor import ConsensusAuditor
from cortensor_verifier.cli import main as cli_main
from cortensor_verifier.models import AuditRunBundle, ClaimDossier
from cortensor_verifier.runtime_factory import create_isolated_runtime
from cortensor_verifier.tools import (
    READ_ONLY_VERIFIER_TOOLS,
    build_scoped_verifier_tools,
    fetch_public_url_excerpt,
    load_claim_dossier,
)
from tests.conftest import LoopbackLLMServer, json_step, tool_calls_step


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mit_license_pyproject_pin_and_upstream_metadata_files() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Copyright (c) 2026 Cortensor OpenMinion Verifier Contributors" in license_text
    assert "Apache License" not in license_text

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    assert project["version"] == "0.1.2"
    assert project["license"] == {"text": "MIT"}
    assert "openminion==0.1.21" in project["dependencies"]
    assert not any(dep.startswith("openminion>=") for dep in project["dependencies"])

    projects_data = yaml.safe_load((REPO_ROOT / "PROJECTS.yml").read_text(encoding="utf-8"))
    assert isinstance(projects_data, list) and len(projects_data) == 1
    entry = projects_data[0]
    assert entry["name"] == "cortensor-openminion-verifier"
    assert entry["category"] == "apps"
    assert entry["owner"] == "@huadeng408"
    assert entry["collaborators"] == ["@huadeng408"]
    assert entry["status"] == "active"
    assert entry["created"] in ("2026-11-14", datetime.date(2026, 11, 14))
    assert entry["version"] == "v0.1.2"
    assert entry["tags"] == [
        "python",
        "openminion",
        "cortensor",
        "consensus",
        "verification",
        "agent",
    ]

    status_text = (REPO_ROOT / "STATUS.md").read_text(encoding="utf-8")
    assert "# PROJECT STATUS" in status_text
    assert "**Date:** 2026-11-15" in status_text
    assert "## Current Status" in status_text
    assert "## Known Issues" in status_text

    release_text = (REPO_ROOT / "RELEASE.md").read_text(encoding="utf-8")
    assert "# Release Notes" in release_text
    assert "## [v0.1.2] - 2026-11-15" in release_text
    assert "## [v0.1.1]" in release_text
    assert "## [v0.1.0]" in release_text


def test_fetch_public_url_excerpt_blocks_ssrf_and_extracts_html_when_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hits: list[str] = []
    long_paragraph = "Verified SEC filing detail. " * 140

    class _HtmlHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            hits.append(self.path)
            if self.path == "/article":
                body = (
                    "<html><head>"
                    "<title>SEC Filing Summary</title>"
                    "<style>.hidden { display: none; }</style>"
                    "<script>window.leak = 'SECRET_SCRIPT_PAYLOAD';</script>"
                    "</head><body>"
                    "<h1>Spot Bitcoin ETP Order</h1>"
                    "<p>Approved on January 10, 2024.</p>"
                    "</body></html>"
                ).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
                return
            if self.path == "/long":
                body = (
                    f"<html><head><title>Long Doc</title></head>"
                    f"<body><p>{long_paragraph}</p></body></html>"
                ).encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
                return
            if self.path == "/redirect-to-article":
                self.send_response(302)
                self.send_header("Location", "/article")
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                return
            self._send(404, b"Not Found", "text/plain")

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), _HtmlHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = int(server.server_address[1])
        assert fetch_public_url_excerpt in READ_ONLY_VERIFIER_TOOLS
        assert fetch_public_url_excerpt.tool_decl.min_scope == "READ_ONLY"
        assert fetch_public_url_excerpt.tool_decl.idempotent is True
        assert fetch_public_url_excerpt.tool_decl.dangerous is False

        # Default allow_private_network=False MUST block loopback, metadata, private, non-HTTP schemes
        for blocked_url in (
            f"http://127.0.0.1:{port}/article",
            f"http://localhost:{port}/article",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/admin",
            "http://[::1]:8000/local",
            "file:///etc/passwd",
        ):
            blocked = fetch_public_url_excerpt(blocked_url)
            assert blocked["ok"] is False
            assert blocked["url"] == blocked_url
            assert blocked.get("error")
        assert hits == []

        # DNS resolution to private/loopback IPs MUST also be blocked
        real_getaddrinfo = socket.getaddrinfo

        def _fake_getaddrinfo(
            host: Any,
            port_arg: Any,
            family: int = 0,
            type: int = 0,  # noqa: A002
            proto: int = 0,
            flags: int = 0,
        ) -> list[Any]:
            if host == "rebind.example.test":
                return [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        6,
                        "",
                        ("169.254.169.254", int(port_arg or 80)),
                    )
                ]
            if host == "public.example.test":
                return [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        6,
                        "",
                        ("93.184.216.34", int(port_arg or 443)),
                    )
                ]
            return real_getaddrinfo(host, port_arg, family, type, proto, flags)

        monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)
        dns_blocked = fetch_public_url_excerpt("https://rebind.example.test/secret")
        assert dns_blocked["ok"] is False
        assert dns_blocked.get("error")

        # HTTP redirect from public host to 169.254.169.254 or 127.0.0.1 MUST be blocked
        redirect_targets_visited: list[str] = []

        def _mock_transport_handler(request: httpx.Request) -> httpx.Response:
            redirect_targets_visited.append(str(request.url))
            if request.url.host == "public.example.test":
                return httpx.Response(
                    302,
                    headers={"Location": "http://169.254.169.254/latest/meta-data/"},
                )
            return httpx.Response(200, text="SHOULD_NOT_BE_FETCHED")

        real_client_cls = httpx.Client
        transport = httpx.MockTransport(_mock_transport_handler)
        monkeypatch.setattr(
            httpx,
            "Client",
            lambda **kwargs: real_client_cls(
                transport=transport,
                **{k: v for k, v in kwargs.items() if k != "transport"},
            ),
        )
        redir_blocked = fetch_public_url_excerpt("https://public.example.test/start")
        assert redir_blocked["ok"] is False
        assert redir_blocked.get("error")
        assert redirect_targets_visited == ["https://public.example.test/start"]

        # Restore real httpx.Client & test DNS-rebinding TOCTOU pinning at TCP dial time
        monkeypatch.undo()
        from cortensor_verifier.tools import _SSRFBlockingNetworkBackend
        import httpcore

        rebind_calls = {"count": 0}
        dialed_hosts: list[str] = []

        def _rebinding_getaddrinfo(
            host: Any,
            port_arg: Any,
            family: int = 0,
            type: int = 0,  # noqa: A002
            proto: int = 0,
            flags: int = 0,
        ) -> list[Any]:
            if host == "toctou.example.test":
                rebind_calls["count"] += 1
                resolved_ip = "93.184.216.34" if rebind_calls["count"] == 1 else "169.254.169.254"
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (resolved_ip, int(port_arg or 443)))]
            if host == "public.example.test":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", int(port_arg or 443)))]
            return real_getaddrinfo(host, port_arg, family, type, proto, flags)

        monkeypatch.setattr(socket, "getaddrinfo", _rebinding_getaddrinfo)
        monkeypatch.setattr(
            httpcore.SyncBackend,
            "connect_tcp",
            lambda self, host, port, timeout=None, local_address=None, socket_options=None: (
                dialed_hosts.append(str(host)) or "DUMMY_STREAM"
            ),
        )
        backend = _SSRFBlockingNetworkBackend(allow_private_network=False)
        # Normal public host must pin & dial the literal resolved IP (never pass hostname downstream)
        assert backend.connect_tcp("public.example.test", 443) == "DUMMY_STREAM"
        assert dialed_hosts == ["93.184.216.34"]
        # First lookup returns public IP; second lookup right at TCP dial time rebinds -> MUST block!
        from cortensor_verifier.tools import _validate_public_url

        _validate_public_url("https://toctou.example.test/doc", allow_private_network=False)
        with pytest.raises(ValueError, match="non-public"):
            backend.connect_tcp("toctou.example.test", 443)

        # Restore real getaddrinfo/SyncBackend to verify allow_private_network=True HTML reading
        monkeypatch.undo()
        scoped_tools = build_scoped_verifier_tools(allow_private_network=True)
        by_name = {fn.tool_decl.name: fn for fn in scoped_tools}
        scoped_fetch_url = by_name["fetch_public_url_excerpt"]

        ok_res = scoped_fetch_url(f"http://127.0.0.1:{port}/redirect-to-article")
        assert ok_res["ok"] is True
        assert ok_res["url"] == f"http://127.0.0.1:{port}/article"
        assert ok_res["title"] == "SEC Filing Summary"
        assert "Spot Bitcoin ETP Order" in ok_res["excerpt"]
        assert "Approved on January 10, 2024." in ok_res["excerpt"]
        assert "SECRET_SCRIPT_PAYLOAD" not in ok_res["excerpt"]
        assert "display: none" not in ok_res["excerpt"]

        long_res = scoped_fetch_url(f"http://127.0.0.1:{port}/long")
        assert long_res["ok"] is True
        assert len(long_res["excerpt"]) <= 2000

        err_res = scoped_fetch_url(f"http://127.0.0.1:{port}/not-found")
        assert err_res["ok"] is False
        assert "404" in err_res["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


_ACTION_SUMMARY_RE = re.compile(
    r"(?:^|\n)action_summary:\s*(.*?)(?=\n(?:closure_action_outputs|sub_intents|intent_outcomes|success_criteria):|\n\[|\Z)",
    re.DOTALL,
)


def _extract_closure_action_summary(request_body: dict[str, Any]) -> str:
    for msg in request_body.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        content = str(msg.get("content") or "")
        match = _ACTION_SUMMARY_RE.search(content)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return "Action completed."


@pytest.fixture(autouse=True)
def _handle_closure_judgment_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extend LoopbackLLMServer's internal classifier stub to also handle ClosureJudgment."""
    targets = []
    for mod_name in ("conftest", "tests.conftest"):
        mod = sys.modules.get(mod_name)
        if mod is not None and mod not in targets:
            targets.append(mod)
    if test_conftest not in targets:
        targets.append(test_conftest)
    original = targets[0]._maybe_internal_classifier_step

    def _wrapped(request_body: dict[str, Any]) -> dict[str, Any] | None:
        base = original(request_body)
        if base is not None:
            return base
        tool_choice = request_body.get("tool_choice")
        if not isinstance(tool_choice, dict):
            return None
        fn = tool_choice.get("function")
        if not isinstance(fn, dict) or fn.get("name") != "submit_output":
            return None
        tools = request_body.get("tools") or []
        schema_title = ""
        if tools and isinstance(tools[0], dict):
            schema_title = str(
                tools[0].get("function", {}).get("parameters", {}).get("title", "")
            )
        if schema_title == "ClosureJudgment":
            return {
                "type": "tool_calls",
                "calls": [
                    {
                        "id": "call_closure_1",
                        "name": "submit_output",
                        "arguments": {
                            "satisfied": True,
                            "reason": "Tool execution completed cleanly.",
                            "next_action": "close",
                            "final_answer": _extract_closure_action_summary(request_body),
                        },
                    }
                ],
            }
        return None

    for mod in targets:
        monkeypatch.setattr(mod, "_maybe_internal_classifier_step", _wrapped)


def _collect_tool_outputs(server: LoopbackLLMServer, start_idx: int = 0) -> list[str]:
    outputs: list[str] = []
    seen_ids: set[str] = set()
    for req in server.requests[start_idx:]:
        for msg in req.body.get("messages", []):
            if not isinstance(msg, dict) or msg.get("role") != "tool":
                continue
            call_id = str(msg.get("tool_call_id") or "")
            if call_id and call_id in seen_ids:
                continue
            if call_id:
                seen_ids.add(call_id)
            outputs.append(str(msg.get("content", "")))
    return outputs


def test_cli_and_auditor_custom_fixtures_catalog_scopes_all_evidence_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-c7-openai-key")
    custom_fixtures_path = tmp_path / "custom_fixtures.json"
    custom_fixtures_path.write_text(
        json.dumps(
            {
                "dossiers": [
                    {
                        "claim_id": "custom-fixture-claim-2026",
                        "title": "Custom Catalog Market Claim",
                        "claim": "Protocol X activated v2 on November 10, 2026.",
                        "market_question": "Did Protocol X activate v2?",
                        "resolution_criteria": "Verify from custom fixture catalog.",
                        "source_hints": ["custom-src-2026"],
                    }
                ],
                "evidence_sources": [
                    {
                        "source_id": "custom-src-2026",
                        "title": "Protocol X v2 Release",
                        "url": "https://example.org/protocol-x-v2",
                        "published_at": "2026-11-10",
                        "keywords": ["protocol", "CUSTOM_CATALOG_EXCERPT_XYZ"],
                        "excerpt": "CUSTOM_CATALOG_EXCERPT_XYZ activated cleanly on 2026-11-10.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_custom_1",
                "name": "load_delphi_market_fixture",
                "arguments": {"claim_id": "custom-fixture-claim-2026"},
            }
        ),
        tool_calls_step(
            {
                "id": "call_default_miss",
                "name": "load_delphi_market_fixture",
                "arguments": {"claim_id": "delphi-btc-etf-2024"},
            }
        ),
        tool_calls_step(
            {
                "id": "call_custom_search",
                "name": "search_public_evidence",
                "arguments": {"query": "CUSTOM_CATALOG_EXCERPT_XYZ", "limit": 5},
            }
        ),
        tool_calls_step(
            {
                "id": "call_custom_fetch",
                "name": "fetch_source_excerpt",
                "arguments": {"source_id": "custom-src-2026"},
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.95,
                "rationale": "Custom catalog confirmed Protocol X v2 activation.",
                "citations": [
                    {
                        "source_id": "custom-src-2026",
                        "title": "Protocol X v2 Release",
                        "excerpt": "CUSTOM_CATALOG_EXCERPT_XYZ activated cleanly on 2026-11-10.",
                    }
                ],
                "pass_role": "primary",
            }
        ),
    )

    rc = cli_main(
        [
            "audit",
            "--claim-id",
            "custom-fixture-claim-2026",
            "--fixtures",
            str(custom_fixtures_path),
            "--base-url",
            loopback_server.base_url,
            "--model",
            "stub-c7-model",
            "--single-pass",
            "--home-root",
            str(tmp_path / "cli-home"),
            "--data-root",
            str(tmp_path / "cli-state"),
        ]
    )
    assert rc == 0
    bundle = AuditRunBundle.model_validate_json(capsys.readouterr().out)
    assert bundle.claim_id == "custom-fixture-claim-2026"
    assert bundle.consensus.final_verdict == "SUPPORTED"

    tool_outputs = _collect_tool_outputs(loopback_server)
    joined = "\n".join(tool_outputs)
    assert '"found": true' in joined and "custom-fixture-claim-2026" in joined, f"outputs={tool_outputs!r}"
    assert '"found": false' in joined and "delphi-btc-etf-2024" in joined, f"outputs={tool_outputs!r}"
    assert "custom-src-2026" in joined and "CUSTOM_CATALOG_EXCERPT_XYZ" in joined, f"outputs={tool_outputs!r}"


def test_standalone_dossier_inline_evidence_sources_via_auditor_and_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-c7-openai-key")
    dossier_path = tmp_path / "standalone_dossier.json"
    dossier_path.write_text(
        json.dumps(
            {
                "claim_id": "standalone-inline-001",
                "title": "Standalone Inline Evidence Claim",
                "claim": "Standalone claim carries inline evidence sources.",
                "market_question": "Are inline evidence sources searchable?",
                "resolution_criteria": "Verify inline metadata.evidence_sources.",
                "source_hints": ["inline-src-1"],
                "metadata": {
                    "evidence_sources": [
                        {
                            "source_id": "inline-src-1",
                            "title": "Inline Spec Filing",
                            "url": "https://example.org/inline",
                            "published_at": "2026-11-15",
                            "keywords": ["inline", "INLINE_EVIDENCE_TOKEN_9988"],
                            "excerpt": "INLINE_EVIDENCE_TOKEN_9988 confirmed by audit.",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_inline_dossier",
                "name": "load_delphi_market_fixture",
                "arguments": {"claim_id": "standalone-inline-001"},
            }
        ),
        tool_calls_step(
            {
                "id": "call_inline_search",
                "name": "search_public_evidence",
                "arguments": {"query": "INLINE_EVIDENCE_TOKEN_9988", "limit": 5},
            }
        ),
        tool_calls_step(
            {
                "id": "call_inline_fetch",
                "name": "fetch_source_excerpt",
                "arguments": {"source_id": "inline-src-1"},
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.93,
                "rationale": "Inline metadata.evidence_sources verified.",
                "citations": [
                    {
                        "source_id": "inline-src-1",
                        "title": "Inline Spec Filing",
                        "excerpt": "INLINE_EVIDENCE_TOKEN_9988 confirmed by audit.",
                    }
                ],
                "pass_role": "primary",
            }
        ),
    )

    rc = cli_main(
        [
            "audit",
            "--dossier",
            str(dossier_path),
            "--base-url",
            loopback_server.base_url,
            "--model",
            "stub-c7-model",
            "--single-pass",
            "--home-root",
            str(tmp_path / "inline-home"),
            "--data-root",
            str(tmp_path / "inline-state"),
        ]
    )
    assert rc == 0
    bundle = AuditRunBundle.model_validate_json(capsys.readouterr().out)
    assert bundle.claim_id == "standalone-inline-001"
    assert bundle.consensus.final_verdict == "SUPPORTED"

    tool_outputs = _collect_tool_outputs(loopback_server)
    joined = "\n".join(tool_outputs)
    assert '"found": true' in joined and "standalone-inline-001" in joined, f"outputs={tool_outputs!r}"
    assert "inline-src-1" in joined and "INLINE_EVIDENCE_TOKEN_9988" in joined, f"outputs={tool_outputs!r}"


def test_auditor_explicit_tools_preserved_and_dual_pass_allows_private_url_when_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-c7-openai-key")
    dossier = load_claim_dossier("delphi-btc-etf-2024")

    @tool(min_scope="READ_ONLY", idempotent=True)
    def custom_ping_tool(token: str) -> dict[str, Any]:
        """Custom read-only ping tool."""
        return {"pong": token}

    loopback_server.enqueue(
        tool_calls_step(
            {
                "id": "call_ping",
                "name": "custom_ping_tool",
                "arguments": {"token": "EXPLICIT_KEEP"},
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.9,
                "rationale": "Explicit custom tool preserved.",
                "citations": [],
                "pass_role": "primary",
            }
        ),
    )

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        model="stub-c7-model",
        home_root=tmp_path / "exp-home",
        data_root=tmp_path / "exp-state",
        tools=[custom_ping_tool],
        provider_retry_max_attempts=1,
    ) as explicit_auditor:
        assert explicit_auditor._explicit_tools is True
        explicit_bundle = explicit_auditor.audit_claim(dossier, single_pass=True)
        assert explicit_bundle.tool_calls == ["custom_ping_tool"]
        assert explicit_auditor._allowed_tool_names == {"custom_ping_tool"}

    class _LocalPageHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            body = b"<html><head><title>Local Mirror</title></head><body><p>DUAL_PASS_HTML_EVIDENCE</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)

    page_server = ThreadingHTTPServer(("127.0.0.1", 0), _LocalPageHandler)
    page_thread = threading.Thread(target=page_server.serve_forever, daemon=True)
    page_thread.start()
    try:
        page_url = f"http://127.0.0.1:{page_server.server_address[1]}/evidence"
        req_start = len(loopback_server.requests)
        loopback_server.enqueue(
            tool_calls_step(
                {
                    "id": "call_dual_url",
                    "name": "fetch_public_url_excerpt",
                    "arguments": {"url": page_url},
                }
            ),
            json_step(
                {
                    "verdict": "SUPPORTED",
                    "confidence": 0.94,
                    "rationale": "Corroborator verified URL excerpt.",
                    "citations": [
                        {
                            "source_id": "url-mirror",
                            "title": "Local Mirror",
                            "url": page_url,
                            "excerpt": "DUAL_PASS_HTML_EVIDENCE",
                        }
                    ],
                    "pass_role": "corroborator",
                }
            ),
            json_step(
                {
                    "verdict": "SUPPORTED",
                    "confidence": 0.90,
                    "rationale": "Skeptic confirmed URL excerpt.",
                    "citations": [
                        {
                            "source_id": "url-mirror",
                            "title": "Local Mirror",
                            "url": page_url,
                            "excerpt": "DUAL_PASS_HTML_EVIDENCE",
                        }
                    ],
                    "pass_role": "skeptic",
                }
            ),
        )

        with ConsensusAuditor(
            preset="openai-compatible",
            base_url=loopback_server.base_url,
            model="stub-c7-model",
            home_root=tmp_path / "dual-home",
            data_root=tmp_path / "dual-state",
            allow_private_network=True,
            provider_retry_max_attempts=1,
        ) as dual_auditor:
            dual_bundle = dual_auditor.audit_claim(dossier, single_pass=False)

        assert dual_bundle.consensus.final_verdict == "SUPPORTED"
        assert "fetch_public_url_excerpt" in dual_bundle.tool_calls
        dual_outputs = _collect_tool_outputs(loopback_server, start_idx=req_start)
        dual_joined = "\n".join(dual_outputs)
        assert '"ok": true' in dual_joined and "DUAL_PASS_HTML_EVIDENCE" in dual_joined, f"outputs={dual_outputs!r}"
    finally:
        page_server.shutdown()
        page_server.server_close()
        page_thread.join(timeout=5)


def test_audit_run_bundle_records_calibration_metadata_in_audit_and_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loopback_server: LoopbackLLMServer,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-c7-cal-key")
    dossier = load_claim_dossier("delphi-btc-etf-2024")
    pub_log = tmp_path / "cal_pub.jsonl"

    # 1. Loopback dual-pass pause -> resume pause -> resume allow_once -> replay deny
    loopback_server.enqueue(
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.94,
                "rationale": "Corroborator confirmed.",
                "citations": [],
                "pass_role": "corroborator",
            }
        ),
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.91,
                "rationale": "Skeptic confirmed.",
                "citations": [],
                "pass_role": "skeptic",
            }
        ),
        tool_calls_step(
            {
                "id": "call_cal_handoff",
                "name": "transfer_to_publisher",
                "arguments": {"message": "Publish delphi-btc-etf-2024"},
            }
        ),
    )

    with ConsensusAuditor(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        model="stub-cal-model",
        home_root=tmp_path / "cal-home",
        data_root=tmp_path / "cal-state",
        provider_retry_max_attempts=1,
    ) as auditor:
        paused = auditor.audit_claim(
            dossier,
            single_pass=False,
            session_id="sess-cal",
            publish=True,
            approval_mode="pause",
            publication_log_path=pub_log,
        )
        assert (
            paused.metadata["calibration_status"]
            == "[Loopback Stub Baseline — awaiting C4 live LLM calibration]"
        )
        assert paused.metadata["calibrated_model"] == "stub-cal-model"
        assert paused.metadata["endpoint_host"] == loopback_server.base_url
        tid = paused.publication.thread_id
        assert tid

        still_paused = auditor.resume_publication(
            thread_id=tid,
            approval_mode="pause",
            publication_log_path=pub_log,
        )
        assert still_paused.metadata["calibration_status"] == paused.metadata["calibration_status"]
        assert still_paused.metadata["calibrated_model"] == "stub-cal-model"
        assert still_paused.metadata["endpoint_host"] == loopback_server.base_url

        loopback_server.enqueue(
            tool_calls_step(
                {
                    "id": "call_cal_pub",
                    "name": "publish_consensus_verdict",
                    "arguments": {
                        "claim_id": dossier.claim_id,
                        "final_verdict": "SUPPORTED",
                        "agreement_score": paused.consensus.agreement_score,
                        "mean_confidence": paused.consensus.mean_confidence,
                        "requires_human_review": False,
                        "session_id": "sess-cal",
                        "summary": "Calibrated publish.",
                    },
                }
            ),
            json_step("Published cleanly."),
        )
        resumed = auditor.resume_publication(
            thread_id=tid,
            approval_mode="allow_once",
            publication_log_path=pub_log,
        )
        assert resumed.metadata["calibration_status"] == paused.metadata["calibration_status"]
        assert resumed.metadata["calibrated_model"] == "stub-cal-model"
        assert resumed.metadata["endpoint_host"] == loopback_server.base_url

        replay_denied = auditor.resume_publication(
            thread_id=tid,
            approval_mode="allow_once",
            publication_log_path=pub_log,
        )
        assert replay_denied.metadata["calibration_status"] == paused.metadata["calibration_status"]
        assert replay_denied.metadata["calibrated_model"] == "stub-cal-model"
        assert replay_denied.metadata["endpoint_host"] == loopback_server.base_url

    # 2. Non-loopback private relay URL is sanitized & marked [Live LLM Calibrated]
    loopback_server.enqueue(
        json_step(
            {
                "verdict": "SUPPORTED",
                "confidence": 0.96,
                "rationale": "Live relay calibration check.",
                "citations": [],
                "pass_role": "primary",
            }
        )
    )
    runtime = create_isolated_runtime(
        preset="openai-compatible",
        base_url=loopback_server.base_url,
        model="grok-4.6",
        home_root=tmp_path / "relay-home",
        data_root=tmp_path / "relay-state",
        provider_retry_max_attempts=1,
    )
    try:
        with ConsensusAuditor(
            runtime=runtime,
            preset="openai-compatible",
            base_url="https://secret-relay.example.org:8443/v1?api_key=leak-token",
            model="grok-4.6",
            home_root=tmp_path / "relay-home",
            data_root=tmp_path / "relay-state",
        ) as relay_auditor:
            live_bundle = relay_auditor.audit_claim(dossier, single_pass=True)
    finally:
        runtime.close()

    assert live_bundle.metadata["calibration_status"] == "[Live LLM Calibrated]"
    assert live_bundle.metadata["calibrated_model"] == "grok-4.6"
    assert (
        live_bundle.metadata["endpoint_host"]
        == "https://<configured-openai-compatible-relay>/v1"
    )
    serialized_meta = json.dumps(live_bundle.metadata)
    assert "secret-relay.example.org" not in serialized_meta
    assert "leak-token" not in serialized_meta
