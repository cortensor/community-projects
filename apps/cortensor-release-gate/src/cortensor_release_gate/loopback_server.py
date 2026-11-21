"""Deterministic local HTTP loopback server for OpenAI-chat and Cortensor completions."""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

TARGET_PATH_PATTERN = re.compile(r"TARGET_DIR=([^\s]+)")
OUTPUT_PATH_PATTERN = re.compile(r"OUTPUT_DIR=([^\s]+)")


def _combined_user_text(messages: list[dict[str, Any]]) -> str:
    parts = [
        str(msg.get("content") or "")
        for msg in messages
        if msg.get("role") == "user"
    ]
    return "\n".join(parts)


def _tool_results(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        raw = msg.get("content")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    outputs = parsed.get("outputs")
                    if isinstance(outputs, dict):
                        results.append(outputs)
                    else:
                        results.append(parsed)
                    continue
            except json.JSONDecodeError:
                pass
        results.append({"raw": str(raw)})
    return results


def _submit_output_tool_call(tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    for entry in tools:
        fn = entry.get("function") if isinstance(entry, dict) else None
        if not isinstance(fn, dict) or fn.get("name") != "submit_output":
            continue
        raw_params = fn.get("parameters")
        params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
        title = str(params.get("title") or "")
        args: dict[str, Any]
        if title == "FinalizationStatus":
            args = {
                "status": "final_answer",
                "reasoning": "Tool outputs collected and verified.",
            }
        elif title == "ClosureJudgment":
            args = {
                "satisfied": True,
                "next_action": "close",
                "reason": "Structured response already produced.",
            }
        else:
            args = {"status": "final_answer"}
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_submit_output_{title or 'default'}",
                    "type": "function",
                    "function": {
                        "name": "submit_output",
                        "arguments": json.dumps(args),
                    },
                }
            ],
        }
    return None


def _tool_names(tools: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for entry in tools:
        fn = entry.get("function") if isinstance(entry, dict) else None
        if isinstance(fn, dict) and fn.get("name"):
            names.append(str(fn["name"]))
    return names


def _build_assistant_reply(payload: dict[str, Any]) -> dict[str, Any]:
    messages = list(payload.get("messages") or [])
    tools = list(payload.get("tools") or [])
    names = _tool_names(tools)
    if "submit_output" in names:
        submit_reply = _submit_output_tool_call(tools)
        if submit_reply is not None:
            return submit_reply
    user_text = _combined_user_text(messages)
    tool_outputs = _tool_results(messages)
    target_match = TARGET_PATH_PATTERN.search(user_text)
    target_dir = target_match.group(1) if target_match else "."
    output_match = OUTPUT_PATH_PATTERN.search(user_text)
    output_dir = output_match.group(1) if output_match else target_dir

    # Step 1: call available READ_ONLY audit tools first before returning final JSON.
    if not tool_outputs:
        for preferred in (
            "scan_security_tool",
            "scan_docs_tool",
            "scan_cortensor_wiring_tool",
        ):
            if preferred in names:
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{preferred}",
                            "type": "function",
                            "function": {
                                "name": preferred,
                                "arguments": json.dumps({"target_dir": target_dir}),
                            },
                        }
                    ],
                }

        if "transfer_to_triage_planner" in names:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_handoff_triage",
                        "type": "function",
                        "function": {
                            "name": "transfer_to_triage_planner",
                            "arguments": json.dumps(
                                {"message": f"TRIAGE_PLAN TARGET_DIR={target_dir}\n{user_text}"}
                            ),
                        },
                    }
                ],
            }

        if "write_release_gate_report" in names and "WRITE_REPORT=1" in user_text:
            summary_obj = {
                "target_path": target_dir,
                "generated_by": "cortensor-release-gate",
            }
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_write_report",
                        "type": "function",
                        "function": {
                            "name": "write_release_gate_report",
                            "arguments": json.dumps(
                                {
                                    "output_dir": output_dir,
                                    "markdown_report": (
                                        f"# Release Gate Report\n\nTarget: `{target_dir}`\n"
                                    ),
                                    "summary_json": json.dumps(summary_obj),
                                }
                            ),
                        },
                    }
                ],
            }

    # Step 2: synthesize structured JSON matching the caller's Pydantic contract.
    if "SECURITY_AUDIT" in user_text and tool_outputs:
        data = tool_outputs[-1]
        if "files_scanned" in data:
            return {"role": "assistant", "content": json.dumps(data)}

    if "DOCS_AUDIT" in user_text and tool_outputs:
        data = tool_outputs[-1]
        if "present_files" in data:
            return {"role": "assistant", "content": json.dumps(data)}

    if "WIRING_AUDIT" in user_text and tool_outputs:
        data = tool_outputs[-1]
        if "uses_openminion" in data:
            return {"role": "assistant", "content": json.dumps(data)}

    if "TRIAGE_PLAN" in user_text:
        triage = {
            "decision": "CHANGES_REQUIRED" if "BLOCKED" not in user_text else "BLOCKED",
            "actions": [
                {
                    "priority": 1,
                    "check_id": "TRIAGE-REVIEW",
                    "owner_area": "maintainer",
                    "action": "Resolve reported blockers and re-run cortensor-release-gate audit.",
                }
            ],
            "summary": "Prioritized remediation plan generated via OpenMinion Handoff.",
        }
        return {"role": "assistant", "content": json.dumps(triage)}

    if "RELEASE_GATE_SYNTHESIS" in user_text:
        written = any(
            isinstance(item, dict) and item.get("written") is True
            for item in tool_outputs
        )
        verdict: dict[str, Any] = {
            "target_path": target_dir,
            "decision": "READY" if "HAS_BLOCKERS=0" in user_text else "BLOCKED",
            "blockers": [],
            "warnings": [],
            "resolved_since_last_run": [],
            "persistent_from_last_run": [],
            "triage_plan": None,
            "report_written": written,
            "report_path": (
                str(tool_outputs[-1].get("markdown_path"))
                if written and isinstance(tool_outputs[-1], dict)
                else None
            ),
            "summary": "Release gate synthesis completed via OpenMinion runtime.",
        }
        return {"role": "assistant", "content": json.dumps(verdict)}

    return {
        "role": "assistant",
        "content": json.dumps(
            {
                "status": "ok",
                "tool_results_count": len(tool_outputs),
                "echo": user_text[:120],
            }
        ),
    }


class LoopbackLLMServer:
    """Thread-backed local HTTP server mimicking Cortensor Portal and Router V2."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", errors="replace")
                payload = json.loads(raw) if raw else {}
                server_ref.requests.append({"path": self.path, "payload": payload})

                if self.path.endswith("/chat/completions"):
                    message = _build_assistant_reply(payload)
                    finish = "tool_calls" if message.get("tool_calls") else "stop"
                    body = {
                        "id": f"chatcmpl-local-{len(server_ref.requests)}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": payload.get("model") or "gpt-oss-20b",
                        "choices": [
                            {"index": 0, "message": message, "finish_reason": finish}
                        ],
                        "usage": {
                            "prompt_tokens": 32,
                            "completion_tokens": 24,
                            "total_tokens": 56,
                        },
                    }
                elif self.path.endswith("/completions"):
                    prompt = str(payload.get("prompt") or "")
                    body = {
                        "id": f"cmpl-local-{len(server_ref.requests)}",
                        "model": payload.get("model") or "gpt-oss-20b",
                        "choices": [
                            {
                                "index": 0,
                                "text": json.dumps(
                                    {
                                        "mode": "cortensor_completion",
                                        "ok": True,
                                        "prompt_chars": len(prompt),
                                    }
                                ),
                                "finish_reason": "stop",
                            }
                        ],
                    }
                else:
                    self.send_response(404)
                    self.end_headers()
                    return

                encoded = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self._httpd.server_address[:2]
        host_str = host.decode("utf-8") if isinstance(host, bytes) else str(host)
        return f"http://{host_str}:{port}/v1"

    @property
    def completion_url(self) -> str:
        host, port = self._httpd.server_address[:2]
        host_str = host.decode("utf-8") if isinstance(host, bytes) else str(host)
        return f"http://{host_str}:{port}/api/v2/completions"

    def start(self) -> LoopbackLLMServer:
        self._thread.start()
        return self

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2.0)


@contextmanager
def running_loopback_server() -> Iterator[LoopbackLLMServer]:
    """Start and cleanly stop a local OpenAI/Cortensor loopback HTTP server."""
    server = LoopbackLLMServer().start()
    try:
        yield server
    finally:
        server.close()
