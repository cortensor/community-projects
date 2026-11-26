"""CompactGuardProxy — OpenAI-compatible prompt-compaction & DLP middleware for OpenMinion 0.1.

OpenMinion 0.1.24 injects ~16.7 KB of default runtime grounding into the system prompt even for
minimal SDK Agent() calls, causing HTTP 400 prompt-size rejections on strict/edge endpoints.
CompactGuardProxy preserves the agent's custom instructions, user messages, and custom @tool
definitions while compacting boilerplate under configurable byte ceilings, and forwards live
requests upstream to any OpenAI-compatible endpoint (Cortensor Portal, OpenRouter, Stellarator, etc.).
"""

from __future__ import annotations

import http.server
import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProxyStats:
    requests: int = 0
    total_raw_bytes: int = 0
    total_compacted_bytes: int = 0
    upstream_errors: int = 0
    sample_payloads: list[dict[str, Any]] = field(default_factory=list)


def compact_chat_payload(
    payload: dict[str, Any],
    max_prompt_bytes: int = 8000,
    *,
    strict_roles: bool = False,
) -> dict[str, Any]:
    """Compact OpenMinion's verbose runtime grounding while keeping custom instructions, tool calls & messages intact."""

    out = dict(payload)
    raw_msgs = [dict(m) for m in (payload.get("messages") or [])]

    msgs: list[dict[str, Any]] = []
    for m in raw_msgs:
        role = str(m.get("role") or "user")
        content = m.get("content")
        if isinstance(content, list):
            parts = [str(p.get("text", "")) for p in content if isinstance(p, dict)]
            content = "\n".join(p for p in parts if p)

        if strict_roles:
            if content is None:
                tc = m.get("tool_calls")
                content = json.dumps({"tool_calls": tc}) if tc else "(ack)"
            content_str = str(content).strip() or "(ack)"
            if role not in {"system", "developer", "user", "assistant"}:
                tname = m.get("name") or m.get("tool_call_id") or "tool"
                role = "user"
                content_str = f"[Tool output {tname}]: {content_str}"
            msgs.append({"role": role, "content": content_str})
        else:
            cleaned = dict(m)
            cleaned["role"] = role
            if content is not None:
                cleaned["content"] = str(content)
            elif "tool_calls" not in cleaned:
                cleaned["content"] = ""
            msgs.append(cleaned)

    # Keep only custom security tools when present; strip bloated workspace built-ins
    if "tools" in out and isinstance(out["tools"], list):
        kept_tools = []
        for t in out["tools"]:
            fn_name = ((t.get("function") or {}).get("name") or "") if isinstance(t, dict) else ""
            if fn_name in {
                "scan_agent_tools",
                "inspect_openminion_policy",
                "fetch_untrusted_ticket",
                "export_sensitive_vault",
                "write_attested_report",
            }:
                kept_tools.append(t)
        if kept_tools:
            out["tools"] = kept_tools
        else:
            out.pop("tools", None)
            out.pop("tool_choice", None)

    # Compact massive system prompt while preserving custom instructions & fallback tool schema instructions
    has_tools = bool(out.get("tools"))
    for m in msgs:
        if m.get("role") == "system" and isinstance(m.get("content"), str):
            sys_txt = m["content"]
            if len(sys_txt) > 1200:
                lines = [ln.strip() for ln in sys_txt.splitlines() if ln.strip()]
                base_kws = (
                    "prompt shield",
                    "auditor",
                    "canary",
                    "hardened",
                    "securityauditreport",
                    "overall_grade",
                    "cortensor",
                    "never reveal",
                    "never follow",
                    "untrusted",
                    "return only",
                    "raw json",
                    "session",
                    "concise",
                    "code word",
                    "write_attested_report",
                    "scan_agent_tools",
                    "inspect_openminion_policy",
                    "fetch_untrusted_ticket",
                    "export_sensitive_vault",
                )
                tool_kws = ("tool_call", "tool call", "arguments") if has_tools else ()
                keep: list[str] = []
                for ln in lines:
                    low = ln.lower()
                    if any(kw in low for kw in (*base_kws, *tool_kws)):
                        # Exclude internal runtime planner JSON-wrapper boilerplate
                        if "user_quote" in low or "runtime grounding" in low:
                            continue
                        keep.append(ln)
                compacted = "\n".join(dict.fromkeys(keep))
                if not compacted:
                    compacted = sys_txt[:900]
                m["content"] = compacted[:2000]

    # Enforce hard total prompt char budget cleanly across message history
    def total_msg_bytes() -> int:
        return sum(len(json.dumps(m, ensure_ascii=False).encode("utf-8")) for m in msgs)

    while total_msg_bytes() > max_prompt_bytes and len(msgs) > 2:
        # Drop oldest non-system message first
        drop_idx = 1 if msgs[0].get("role") == "system" else 0
        msgs.pop(drop_idx)

    if total_msg_bytes() > max_prompt_bytes:
        for m in msgs:
            if isinstance(m.get("content"), str) and len(m["content"]) > 2400:
                m["content"] = m["content"][:2400] + "\n...[compacted]"

    out["messages"] = msgs
    out["max_tokens"] = min(int(out.get("max_tokens") or 384), 384)
    return out


class CompactGuardProxy:
    """Context-managed local HTTP proxy forwarding compacted OpenMinion requests upstream."""

    def __init__(
        self,
        upstream_base_url: str,
        api_key: str,
        max_prompt_bytes: int = 8000,
        *,
        strict_roles: bool = False,
    ) -> None:
        self.upstream_base_url = upstream_base_url.rstrip("/")
        self.api_key = api_key
        self.max_prompt_bytes = max_prompt_bytes
        self.strict_roles = strict_roles
        self.stats = ProxyStats()
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.local_base_url = ""

    def __enter__(self) -> "CompactGuardProxy":
        proxy = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length)
                proxy.stats.requests += 1
                proxy.stats.total_raw_bytes += len(raw_body)

                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    self.send_error(400, "Invalid JSON")
                    return

                compacted = compact_chat_payload(
                    payload,
                    max_prompt_bytes=proxy.max_prompt_bytes,
                    strict_roles=proxy.strict_roles,
                )
                out_bytes = json.dumps(compacted).encode("utf-8")
                proxy.stats.total_compacted_bytes += len(out_bytes)
                if len(proxy.stats.sample_payloads) < 5:
                    proxy.stats.sample_payloads.append(
                        {
                            "raw_bytes": len(raw_body),
                            "compacted_bytes": len(out_bytes),
                            "n_msgs": len(compacted.get("messages", [])),
                            "n_tools": len(compacted.get("tools", [])),
                        }
                    )

                # Forward to upstream /chat/completions
                suffix = self.path if self.path.startswith("/chat/") else "/chat/completions"
                upstream_url = f"{proxy.upstream_base_url}{suffix}"
                req = urllib.request.Request(
                    upstream_url,
                    data=out_bytes,
                    headers={
                        "Authorization": f"Bearer {proxy.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "CortensorPromptShield/0.1",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        body = resp.read()
                        self.send_response(resp.status)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                except urllib.error.HTTPError as e:
                    proxy.stats.upstream_errors += 1
                    err_body = e.read()
                    self.send_response(e.code)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(err_body)))
                    self.end_headers()
                    self.wfile.write(err_body)
                except Exception as exc:
                    proxy.stats.upstream_errors += 1
                    err_body = json.dumps({"error": {"message": str(exc)}}).encode("utf-8")
                    self.send_response(502)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(err_body)))
                    self.end_headers()
                    self.wfile.write(err_body)

            def log_message(self, _fmt: str, *_args: object) -> None:
                return

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = self._server.server_address[1]
        self.local_base_url = f"http://127.0.0.1:{port}/v1"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
