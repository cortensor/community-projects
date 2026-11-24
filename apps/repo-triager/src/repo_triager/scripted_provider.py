"""A scripted OpenAI-compatible provider used by the offline test suite.

The provider speaks the same HTTP protocol as a hosted model, so OpenMinion's
own adapter, tool-call parsing, policy gate, and turn loop all execute for
real.  Only the *model* is replaced: answers come from a JSON script that is
selected by a ``SCENARIO:<name>`` marker in the conversation.

Script shape::

    {
      "issue-859": {
        "steps": [
          {"kind": "tool", "tool": "get_issue", "args": {"issue_number": 859}},
          {"kind": "tool", "tool": "search_similar_issues", "args": {"query": "..."}},
          {"kind": "text", "content": "..."}
        ],
        "output": {"severity": "S2", "...": "..."},
        "fallback_text": "ok"
      }
    }

``output`` is what the provider submits when the runtime asks for the
structured-output tool (``submit_output``).  Runtime bookkeeping requests
(auto fact extraction) are answered with an empty candidate list.

Run standalone::

    python -m repo_triager.scripted_provider --port 8899 --script tests/fixtures/scripts/scripts.json

Every request is appended to ``--request-log`` as one JSON object per line so
tests can inspect exactly what the runtime sent to the model.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

AFE_SCHEMA_TITLES = frozenset({"UserMessageCandidateReport"})

#: Answers for OpenMinion's own internal structured-output calls (freshness
#: classification, closure judgment).  A real model answers these itself; the
#: scripted model just needs to be well-formed so the turn can continue.
INTERNAL_SCHEMA_ANSWERS: dict[str, dict[str, Any]] = {
    "FreshnessContract": {
        "intent": "triage local repository issues",
        "domain": "general",
        "time_sensitive": False,
        "needs_live_data": False,
        "needs_sources": False,
        "needs_exact_date": False,
        "answer_mode": "local_only",
        "reason": "all evidence comes from the local repository snapshot",
        "confidence": 0.9,
    },
    "FinalizationStatus": {
        "status": "final_answer",
        "reasoning": "the task message asked for one answer and it was produced",
        "remaining_work": "",
        "blocking_reason": "",
    },
    "ClosureJudgment": {
        "satisfied": True,
        "reason": "the triage decision was produced",
        "next_action": "close",
    },
}


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                ]
                return "\n".join(parts)
    return ""


def _all_text(messages: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    chunks.append(item["text"])
    return "\n".join(chunks)


SCENARIO_RE = re.compile(r"SCENARIO:([A-Za-z0-9_.-]+)")


def _scenario_name(messages: list[dict[str, Any]]) -> str | None:
    match = SCENARIO_RE.search(_all_text(messages))
    return match.group(1) if match else None


def _last_tool_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "tool":
            content = message.get("content")
            return content if isinstance(content, str) else str(content)
    return ""


def _step_index(messages: list[dict[str, Any]]) -> int:
    """Number of assistant messages already produced for this turn."""

    return sum(1 for message in messages if message.get("role") == "assistant")


def _tool_schema_title(tool: dict[str, Any]) -> str:
    parameters = (tool.get("function") or {}).get("parameters") or {}
    return str(parameters.get("title") or "")


class ScriptedModel:
    def __init__(self, scripts: dict[str, Any], log_path: Path | None = None) -> None:
        self.scripts = scripts
        self.log_path = log_path
        self._lock = threading.Lock()
        self._records: list[dict[str, Any]] = []
        self.dump_payload = bool(os.environ.get("SCRIPTED_DUMP"))
        self.call_counter = 0

    # -- script resolution ---------------------------------------------------
    def response_for(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages") or []
        tools = payload.get("tools") or []
        tool_names = [
            (tool.get("function") or {}).get("name")
            for tool in tools
            if isinstance(tool, dict)
        ]
        scenario = _scenario_name(messages)
        script = self.scripts.get(scenario or "", None)
        step = _step_index(messages)

        # 1. Structured-output request: the runtime exposes only submit_output
        #    and declares the target schema by its pydantic title.
        if tool_names == ["submit_output"]:
            title = _tool_schema_title(tools[0])
            if title in AFE_SCHEMA_TITLES:
                self._log(
                    {
                        "kind": "afe",
                        "scenario": scenario,
                        "schema": title if title else "afe",
                        "step": step,
                    }
                )
                return self._tool_response(
                    payload, "submit_output", {"session_id": "", "agent_id": "", "items": []}
                )
            if title in INTERNAL_SCHEMA_ANSWERS:
                self._log(
                    {"kind": "internal", "scenario": scenario, "schema": title, "step": step}
                )
                return self._tool_response(
                    payload, "submit_output", INTERNAL_SCHEMA_ANSWERS[title]
                )
            output = (script or {}).get("output")
            self._log(
                {
                    "kind": "structured_output",
                    "scenario": scenario,
                    "schema": title,
                    "step": step,
                    "submitted": output is not None,
                }
            )
            if output is None:
                return self._text_response(payload, "{}")
            return self._tool_response(payload, "submit_output", output)

        # 2. A call that offers no tools is runtime bookkeeping; answer in
        #    plain text and do not consume a scripted step.
        if not tool_names:
            self._log({"kind": "no-tools", "scenario": scenario, "step": step})
            return self._text_response(payload, "ok")

        entry: dict[str, Any] = {
            "scenario": scenario,
            "step": step,
            "tool_names": tool_names,
            "model": payload.get("model"),
            "message_count": len(messages),
            "last_user": _last_user_text(messages)[:400],
            "last_tool": _last_tool_text(messages)[:400],
        }
        if self.dump_payload:
            entry["payload"] = payload
        if script is None:
            self._log({**entry, "kind": "unscripted"})
            return self._text_response(payload, "ok")
        steps = script.get("steps", [])
        if step >= len(steps):
            self._log({**entry, "kind": "exhausted"})
            return self._text_response(payload, script.get("fallback_text", "ok"))
        action = steps[step]
        self._log({**entry, "kind": action.get("kind", "tool")})
        if action.get("kind") == "tool":
            tool = action["tool"]
            if tool not in tool_names:
                raise AssertionError(
                    f"script step {step} asks for {tool!r} but the runtime offered "
                    f"{tool_names!r} (scenario {scenario!r})"
                )
            return self._tool_response(payload, tool, action.get("args", {}))
        return self._text_response(payload, action.get("content", ""))

    # -- wire format ---------------------------------------------------------
    def _usage(self, prompt_chars: int, completion_chars: int) -> dict[str, int]:
        prompt_tokens = max(1, prompt_chars // 4)
        completion_tokens = max(1, completion_chars // 4)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def _envelope(
        self,
        payload: dict[str, Any],
        message: dict[str, Any],
        finish_reason: str,
        usage: dict[str, int],
    ) -> dict[str, Any]:
        with self._lock:
            self.call_counter += 1
            serial = self.call_counter
        message = {"id": f"m{serial}", **message}
        return {
            "id": f"chatcmpl-scripted-{serial}",
            "object": "chat.completion",
            "created": 1_750_000_000,
            "model": payload.get("model") or "scripted-1",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", **message},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": usage,
        }

    def _text_response(self, payload: dict[str, Any], text: str) -> dict[str, Any]:
        return self._envelope(
            payload,
            {"content": text},
            "stop",
            self._usage(len(json.dumps(payload.get("messages", []))), len(text)),
        )

    def _tool_response(
        self, payload: dict[str, Any], tool_name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        call_id = f"call_{tool_name}_{_step_index(payload.get('messages') or [])}"
        message = {
            "content": None,
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args, ensure_ascii=False),
                    },
                }
            ],
        }
        return self._envelope(
            payload,
            message,
            "tool_calls",
            self._usage(
                len(json.dumps(payload.get("messages", []))),
                len(json.dumps(args)),
            ),
        )

    def _log(self, record: dict[str, Any]) -> None:
        with self._lock:
            self._records.append(record)
            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    @property
    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records)


def make_handler(model: ScriptedModel):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            if os.environ.get("SCRIPTED_PROVIDER_VERBOSE"):
                super().log_message(fmt, *args)

        def _json(self, status: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.rstrip("/").endswith("/models"):
                self._json(
                    200,
                    {
                        "object": "list",
                        "data": [{"id": "scripted-1", "object": "model"}],
                    },
                )
                return
            self._json(404, {"error": {"message": "not found"}})

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                self._json(400, {"error": {"message": "bad json"}})
                return
            try:
                body = model.response_for(payload)
            except AssertionError as exc:
                self._json(500, {"error": {"message": str(exc)}})
                return
            if payload.get("stream"):
                chunk = {
                    "id": body["id"],
                    "object": "chat.completion.chunk",
                    "created": body["created"],
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": body["choices"][0]["message"],
                            "finish_reason": body["choices"][0]["finish_reason"],
                        }
                    ],
                }
                data = f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n".encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._json(200, body)

    return Handler


class ScriptedProvider:
    """Context manager that serves the scripted provider on localhost."""

    def __init__(
        self,
        scripts_path: str | Path | None = None,
        *,
        port: int = 0,
        log_path: str | Path | None = None,
        scripts: dict[str, Any] | None = None,
    ) -> None:
        self.scripts_path = Path(scripts_path) if scripts_path else None
        self.inline_scripts = scripts
        self.port = port
        self.log_path = Path(log_path) if log_path else None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.model: ScriptedModel | None = None

    def __enter__(self) -> "ScriptedProvider":
        scripts: dict[str, Any] = dict(self.inline_scripts or {})
        if self.scripts_path and self.scripts_path.exists():
            scripts.update(json.loads(self.scripts_path.read_text(encoding="utf-8")))
        self.model = ScriptedModel(scripts, self.log_path)
        self._server = ThreadingHTTPServer(
            ("127.0.0.1", self.port), make_handler(self.model)
        )
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def __exit__(self, *exc: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--script", default="tests/fixtures/scripts/scripts.json")
    parser.add_argument("--request-log", default="artifacts/scripted-requests.jsonl")
    args = parser.parse_args()
    with ScriptedProvider(
        args.script, port=args.port, log_path=args.request_log
    ) as provider:
        print(f"scripted provider listening on {provider.base_url} (ctrl-c to stop)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
