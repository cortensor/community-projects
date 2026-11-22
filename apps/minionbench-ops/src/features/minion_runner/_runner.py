"""OpenMinion 0.1.24 runtime runner with live model execution and TCP loopback server."""

from __future__ import annotations

from dataclasses import dataclass
import http.server
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable
import urllib.error
import urllib.request

from openminion import (
    APIRuntime,
    Agent,
    AgentRunResult,
    OpenMinionConfig,
    ProviderError,
    TurnTimeoutError,
    __version__ as OPENMINION_VERSION,
)

from src.kernel.event_bus import (
    EventBus,
    KernelIntegrityError,
    MinionTurnReceipt,
    ToolCallRecord,
    corrupt_gate_active,
    redact_secrets,
    utc_now_iso,
)

LOOPBACK_ENV_KEY = "MINIONBENCH_LOOPBACK_TOKEN"
OLLAMA_BRIDGE_ENV_KEY = "MINIONBENCH_OLLAMA_KEY"


def _build_entry_task_update(messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_input = str(messages[-1].get("content", "")) if messages else ""
    revision = 0
    for msg in messages:
        content = str(msg.get("content", ""))
        if "CURRENT TASK (user instructions" in content:
            match = re.search(r'"revision":\s*(\d+)', content)
            if match:
                revision = int(match.group(1))
    return {
        "operation": "start" if revision == 0 else "replace",
        "expected_revision": revision,
        "user_quote": user_input,
        "objective": user_input,
    }


@dataclass
class LoopbackBehavior:
    """Configurable deterministic behavior for the local 127.0.0.1 OpenAI-compatible server."""

    tool_queue: list[tuple[str, dict[str, Any]]]
    final_answer: str = "Cortensor release triage completed with zero blocking defects."
    http_status: int = 200
    delay_seconds: float = 0.0


class LoopbackOpenAIServer:
    """Real TCP 127.0.0.1 OpenAI-compatible HTTP server for deterministic offline tests."""

    def __init__(self, behavior: LoopbackBehavior | None = None) -> None:
        self.behavior = behavior or LoopbackBehavior(tool_queue=[])
        self.requests_seen: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("LoopbackOpenAIServer is not running.")
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}/v1"

    def __enter__(self) -> "LoopbackOpenAIServer":
        parent = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:
                del fmt, args

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8", errors="replace")
                body = json.loads(raw_body) if raw_body else {}
                with parent._lock:
                    parent.requests_seen.append(body)
                    delay = parent.behavior.delay_seconds
                    status = parent.behavior.http_status

                if delay > 0:
                    time.sleep(delay)

                if status >= 400:
                    err_bytes = json.dumps(
                        {"error": {"message": f"Injected HTTP {status} fault", "type": "server_error"}}
                    ).encode("utf-8")
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(err_bytes)))
                    self.end_headers()
                    self.wfile.write(err_bytes)
                    return

                messages = list(body.get("messages") or [])
                tools = list(body.get("tools") or [])
                by_name = {
                    str(t.get("function", {}).get("name", "")): t.get("function", {})
                    for t in tools
                    if isinstance(t, dict)
                }
                sys_txt = str(messages[0].get("content", "")) if messages else ""
                last_txt = str(messages[-1].get("content", "")) if messages else ""
                is_entry = "For a clarification or new input with a CURRENT TASK" in sys_txt

                next_tool: tuple[str, dict[str, Any]] | None = None
                with parent._lock:
                    if parent.behavior.tool_queue and "Continue the active task" not in last_txt:
                        cand_name, cand_args = parent.behavior.tool_queue[0]
                        if cand_name in by_name:
                            next_tool = parent.behavior.tool_queue.pop(0)

                if next_tool is not None:
                    t_name, t_args = next_tool
                    call_args = dict(t_args)
                    props = by_name[t_name].get("parameters", {}).get("properties", {})
                    if is_entry and "task_update" in props:
                        call_args["task_update"] = _build_entry_task_update(messages)
                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": f"call_{len(parent.requests_seen)}",
                                "type": "function",
                                "function": {
                                    "name": t_name,
                                    "arguments": json.dumps(call_args),
                                },
                            }
                        ],
                    }
                    finish_reason = "tool_calls"
                elif "respond" in by_name and is_entry:
                    props = by_name["respond"].get("parameters", {}).get("properties", {})
                    rargs: dict[str, Any] = {"answer": parent.behavior.final_answer}
                    if "freshness" in props:
                        rargs["freshness"] = {
                            "time_sensitive": False,
                            "needs_live_data": False,
                            "needs_sources": False,
                            "needs_exact_date": False,
                            "intent": "release_triage",
                            "domain": "general",
                            "answer_mode": "direct",
                            "reason": "local_workspace_evidence",
                            "confidence": 0.96,
                        }
                    if "task_update" in props:
                        rargs["task_update"] = _build_entry_task_update(messages)
                    assistant_msg = {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": f"call_resp_{len(parent.requests_seen)}",
                                "type": "function",
                                "function": {
                                    "name": "respond",
                                    "arguments": json.dumps(rargs),
                                },
                            }
                        ],
                    }
                    finish_reason = "tool_calls"
                else:
                    assistant_msg = {
                        "role": "assistant",
                        "content": parent.behavior.final_answer,
                    }
                    finish_reason = "stop"

                payload = {
                    "id": f"chatcmpl-lb-{len(parent.requests_seen)}",
                    "object": "chat.completion",
                    "created": 1763736000,
                    "model": str(body.get("model") or "loopback-minionbench-v1"),
                    "choices": [
                        {
                            "index": 0,
                            "message": assistant_msg,
                            "finish_reason": finish_reason,
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 32,
                        "completion_tokens": 16,
                        "total_tokens": 48,
                    },
                }
                encoded = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        del exc_type, exc, tb
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


def build_runtime_agents_config(
    *,
    gemini_model: str = "gemini-2.5-flash",
    ollama_model: str = "qwen2.5:1.5b",
    loopback_base_url: str | None = None,
    active_default_agent: str = "ollama-live",
) -> dict[str, Any]:
    """Construct validated OpenMinion 0.1.24 agents.json payload with zero secret literals."""
    raw: dict[str, Any] = {
        "default_agent": active_default_agent,
        "providers": {
            "openai": {
                "model": ollama_model,
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key_env": OLLAMA_BRIDGE_ENV_KEY,
                "tool_call_strategy": "hybrid",
                "timeout_seconds": 90,
            },
            "cortensor": {
                "model": "gpt-oss-20b",
                "base_url": "http://127.0.0.1:8080/api/v2/completions",
                "api_key_env": "CORTENSOR_API_KEY",
                "tool_call_strategy": "hybrid",
                "timeout_seconds": 420,
                "precommit_timeout_seconds": 300,
                "transport_timeout_buffer_seconds": 30,
            },
            "ollama": {
                "model": ollama_model,
                "base_url": "http://127.0.0.1:11434",
                "tool_call_strategy": "hybrid",
                "timeout_seconds": 90,
            },
        },
        "agents": {
            "gemini-live": {
                "provider": "openai",
                "default_channel": "console",
                "tool_schema_shortlisting_enabled": True,
                "provider_config_overrides": {
                    "model": gemini_model,
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                    "api_key_env": "GEMINI_API_KEY",
                    "tool_call_strategy": "hybrid",
                    "timeout_seconds": 45,
                },
            },
            "cortensor-portal": {
                "provider": "openai",
                "default_channel": "console",
                "tool_schema_shortlisting_enabled": True,
                "provider_config_overrides": {
                    "model": "oss-20b",
                    "base_url": "https://api.cortensor.app/v1",
                    "api_key_env": "CORTENSOR_API_KEY",
                    "tool_call_strategy": "hybrid",
                    "timeout_seconds": 90,
                },
            },
            "cortensor-router": {
                "provider": "cortensor",
                "default_channel": "console",
                "tool_schema_shortlisting_enabled": True,
            },
            "ollama-live": {
                "provider": "openai",
                "default_channel": "console",
                "tool_schema_shortlisting_enabled": True,
                "provider_config_overrides": {
                    "model": ollama_model,
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key_env": OLLAMA_BRIDGE_ENV_KEY,
                    "tool_call_strategy": "hybrid",
                    "temperature": 0.0,
                    "timeout_seconds": 90,
                },
            },
        },
    }
    if loopback_base_url:
        raw["agents"]["loopback-test"] = {
            "provider": "openai",
            "default_channel": "console",
            "tool_schema_shortlisting_enabled": True,
            "provider_config_overrides": {
                "model": "loopback-minionbench-v1",
                "base_url": loopback_base_url,
                "api_key_env": LOOPBACK_ENV_KEY,
                "tool_call_strategy": "hybrid",
                "timeout_seconds": 15,
            },
        }
    # Validate directly through OpenMinion's typed config parser
    OpenMinionConfig.from_dict(raw)
    return raw


def _discover_gemini_flash_model() -> tuple[str, str | None]:
    """Query Gemini OpenAI-compatible models endpoint in memory without logging secrets."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return ("gemini-2.5-flash", "GEMINI_API_KEY not set in environment.")
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/openai/models",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        models = [
            str(item.get("id", "")).replace("models/", "")
            for item in (payload.get("data") or [])
            if isinstance(item, dict) and "flash" in str(item.get("id", "")).lower()
        ]
        if models:
            return (models[0], None)
        return ("gemini-2.5-flash", None)
    except urllib.error.HTTPError as exc:
        return ("gemini-2.5-flash", f"Gemini models endpoint returned HTTP {exc.code}; probing turn boundary.")
    except Exception as exc:  # noqa: BLE001
        return ("gemini-2.5-flash", redact_secrets(f"Gemini models probe error: {type(exc).__name__}"))


def _discover_local_ollama_model() -> str:
    """Select fastest installed local Ollama model supporting OpenAI /v1 tool calls."""
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        installed = [str(m.get("name", "")) for m in (payload.get("models") or []) if isinstance(m, dict)]
        for preferred in ("qwen2.5:1.5b", "qwen2.5:0.5b", "llama3.2:latest"):
            if preferred in installed:
                return preferred
        if installed:
            return installed[0]
    except Exception:  # noqa: BLE001
        pass
    return "qwen2.5:1.5b"


def execute_triage_workflow(
    *,
    workspace_root: Path,
    tools: list[Callable[..., Any]],
    bus: EventBus,
    mode: str = "live",
    session_id: str = "cortensor-release-triage-01",
) -> MinionTurnReceipt:
    """Run the Cortensor builder release-and-triage workflow through OpenMinion 0.1.24."""
    if corrupt_gate_active():
        raise KernelIntegrityError("CORRUPT_GATE_CONTROL=1 aborted execute_triage_workflow.")

    resolved_root = workspace_root.resolve()
    runtime_dir = resolved_root / ".openminion_runtime" / mode
    home_root = runtime_dir / "home"
    data_root = runtime_dir / "data"
    config_dir = runtime_dir / "config"
    for d in (home_root, data_root, config_dir):
        d.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault(OLLAMA_BRIDGE_ENV_KEY, "ollama-local-bridge")
    os.environ.setdefault(LOOPBACK_ENV_KEY, "loopback-local-ok")

    if mode == "loopback":
        behavior = LoopbackBehavior(
            tool_queue=[
                ("inspect_workspace_manifest", {"workspace_rel_dir": "."}),
                ("audit_python_module_risks", {"target_subpath": "src"}),
                ("check_cortensor_config_posture", {"profile_mode": "cortensor-portal"}),
            ],
            final_answer=(
                "Workspace manifest, AST sibling isolation, and Cortensor Portal posture verified "
                "with zero secret leaks."
            ),
        )
        with LoopbackOpenAIServer(behavior) as server:
            cfg_dict = build_runtime_agents_config(
                loopback_base_url=server.base_url,
                active_default_agent="loopback-test",
            )
            cfg_path = config_dir / "agents.loopback.json"
            cfg_path.write_text(json.dumps(cfg_dict, indent=2), encoding="utf-8")
            t0 = time.monotonic()
            runtime = APIRuntime.from_config_path(
                str(cfg_path),
                home_root=home_root,
                data_root=data_root,
                logging_mode="default",
            )
            try:
                ro_tools = [
                    t for t in tools if getattr(getattr(t, "tool_decl", None), "name", "") != "stage_release_brief"
                ]
                loopback_steps = (
                    ("inspect_workspace_manifest", "Run inspect_workspace_manifest on the current workspace."),
                    ("audit_python_module_risks", "Run audit_python_module_risks on src."),
                    (
                        "check_cortensor_config_posture",
                        "Verify cortensor-portal posture and summarize release readiness.",
                    ),
                )
                r3: AgentRunResult[Any] | None = None
                for forced_name, step_prompt in loopback_steps:
                    step_tools = [
                        t for t in ro_tools if getattr(getattr(t, "tool_decl", None), "name", "") == forced_name
                    ]
                    with Agent(
                        runtime=runtime,
                        agent_id="loopback-test",
                        instructions=(
                            "Audit workspace manifest, Python AST module risks, and Cortensor config posture."
                        ),
                        tools=step_tools or ro_tools,
                        forced_tools=[forced_name] if step_tools else None,
                        session_id=f"{session_id}-loopback",
                    ) as agent:
                        r3 = agent.run(step_prompt)
            finally:
                runtime.close()
            assert r3 is not None
            latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
            records = bus.tool_call_records()
            receipt = MinionTurnReceipt(
                session_id=str(r3.session_id or session_id),
                run_id=str(r3.run_id or "loopback-run"),
                run_state=str(r3.run_state or "completed"),
                agent_id="loopback-test",
                provider_transport="openai-loopback-http",
                model_id="loopback-minionbench-v1",
                endpoint_base_url="http://127.0.0.1/v1",
                openminion_version=OPENMINION_VERSION,
                latency_ms=latency_ms,
                live_neural_model=False,
                tool_invocations=records,
                final_text=redact_secrets(r3.text),
                hosted_probe_note="Deterministic local TCP HTTP loopback verification mode.",
                sanitized=True,
                recorded_at_utc=utc_now_iso(),
            )
            receipt.verify_invariants()
            return receipt

    # Live model-backed mode: attempt Gemini OpenAI-compatible endpoint first, then fallback to live Ollama /v1
    gemini_model, preflight_note = _discover_gemini_flash_model()
    ollama_model = _discover_local_ollama_model()
    hosted_probe_note = preflight_note or "Gemini endpoint reachable."

    if os.environ.get("GEMINI_API_KEY", "").strip():
        gemini_cfg = build_runtime_agents_config(
            gemini_model=gemini_model,
            ollama_model=ollama_model,
            active_default_agent="gemini-live",
        )
        gemini_cfg_path = config_dir / "agents.gemini.json"
        gemini_cfg_path.write_text(json.dumps(gemini_cfg, indent=2), encoding="utf-8")
        t0 = time.monotonic()
        rt_gemini = APIRuntime.from_config_path(
            str(gemini_cfg_path),
            home_root=home_root,
            data_root=data_root,
            logging_mode="default",
        )
        try:
            with Agent(
                runtime=rt_gemini,
                agent_id="gemini-live",
                instructions=(
                    "You are Minionbench Ops, a Cortensor release triage guard. "
                    "Execute the requested read-only workspace audit tools and summarize findings concisely."
                ),
                tools=tools,
                forced_tools=["inspect_workspace_manifest"],
                session_id=f"{session_id}-gemini",
            ) as gemini_agent:
                g_res: AgentRunResult[Any] = gemini_agent.run(
                    "Audit workspace manifest, Python AST risks in src, and cortensor-portal config posture.",
                    timeout_seconds=60.0,
                )
                if len(bus.tool_call_records()) < 2:
                    g_res = gemini_agent.run(
                        "Now call audit_python_module_risks for src and check_cortensor_config_posture for cortensor-portal.",
                        thread_id=g_res.thread_id,
                        timeout_seconds=60.0,
                    )
                latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
                receipt = MinionTurnReceipt(
                    session_id=str(g_res.session_id or session_id),
                    run_id=str(g_res.run_id or "gemini-live-run"),
                    run_state=str(g_res.run_state or "completed"),
                    agent_id="gemini-live",
                    provider_transport="openai (Gemini v1beta/openai)",
                    model_id=gemini_model,
                    endpoint_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                    openminion_version=OPENMINION_VERSION,
                    latency_ms=latency_ms,
                    live_neural_model=True,
                    tool_invocations=bus.tool_call_records(),
                    final_text=redact_secrets(g_res.text),
                    hosted_probe_note="Hosted Gemini OpenAI-compatible live run succeeded.",
                    sanitized=True,
                    recorded_at_utc=utc_now_iso(),
                )
                receipt.verify_invariants()
                return receipt
        except (ProviderError, TurnTimeoutError) as exc:
            err_code = getattr(exc, "code", type(exc).__name__)
            hosted_probe_note = redact_secrets(
                f"Gemini preflight caught {err_code} ({str(exc)[:140]}); "
                f"executed live neural fallback on local Ollama {ollama_model} via /v1 OpenAI transport."
            )
            bus.publish(
                "provider.fallback",
                source_brick="minion_runner",
                payload={"failed_agent": "gemini-live", "error_code": str(err_code), "fallback_model": ollama_model},
            )
        finally:
            rt_gemini.close()

    # Live local neural-model run via Ollama OpenAI-compatible /v1 endpoint
    ollama_cfg = build_runtime_agents_config(
        gemini_model=gemini_model,
        ollama_model=ollama_model,
        active_default_agent="ollama-live",
    )
    ollama_cfg_path = config_dir / "agents.json"
    ollama_cfg_path.write_text(json.dumps(ollama_cfg, indent=2), encoding="utf-8")

    t0 = time.monotonic()
    rt_ollama = APIRuntime.from_config_path(
        str(ollama_cfg_path),
        home_root=home_root,
        data_root=data_root,
        logging_mode="default",
    )
    try:
        ro_tools = [t for t in tools if getattr(getattr(t, "tool_decl", None), "name", "") != "stage_release_brief"]
        step_plan = (
            (
                "inspect_workspace_manifest",
                "Call inspect_workspace_manifest with workspace_rel_dir='.' and report the package name and secret_hygiene_ok.",
            ),
            (
                "audit_python_module_risks",
                "Call audit_python_module_risks with target_subpath='src' and report python_files_scanned and architecture_clean.",
            ),
            (
                "check_cortensor_config_posture",
                "Call check_cortensor_config_posture with profile_mode='cortensor-portal' and report max_retries and endpoint.",
            ),
        )
        last_result: AgentRunResult[Any] | None = None
        step_summaries: list[str] = []
        for idx, (forced_name, prompt) in enumerate(step_plan, start=1):
            matching_tool = [
                t for t in ro_tools if getattr(getattr(t, "tool_decl", None), "name", "") == forced_name
            ]
            for attempt in range(1, 3):
                already_called = {rec.tool_name for rec in bus.tool_call_records()}
                if forced_name in already_called:
                    break
                step_sid = f"{session_id}-ollama-s{idx}a{attempt}"
                with Agent(
                    runtime=rt_ollama,
                    agent_id="ollama-live",
                    instructions=(
                        f"You MUST invoke the {forced_name} tool immediately to answer the user request, "
                        "then summarize the returned JSON concisely."
                    ),
                    tools=matching_tool or ro_tools,
                    forced_tools=[forced_name] if matching_tool else None,
                    session_id=step_sid,
                ) as step_agent:
                    last_result = step_agent.run(
                        prompt,
                        timeout_seconds=110.0,
                    )
                if forced_name in {rec.tool_name for rec in bus.tool_call_records()}:
                    step_summaries.append(redact_secrets(last_result.text.strip()))
                    break
    finally:
        rt_ollama.close()

    if last_result is None:
        raise KernelIntegrityError("Live OpenMinion run produced no AgentRunResult.")

    latency_ms = round((time.monotonic() - t0) * 1000.0, 2)
    records: tuple[ToolCallRecord, ...] = bus.tool_call_records()
    combined_text = "\n\n".join(step_summaries) if step_summaries else redact_secrets(last_result.text)
    receipt = MinionTurnReceipt(
        session_id=str(last_result.session_id or f"{session_id}-ollama"),
        run_id=str(last_result.run_id or "ollama-live-run"),
        run_state=str(last_result.run_state or "completed"),
        agent_id="ollama-live",
        provider_transport="openai (Ollama /v1 neural runtime)",
        model_id=ollama_model,
        endpoint_base_url="http://127.0.0.1:11434/v1",
        openminion_version=OPENMINION_VERSION,
        latency_ms=latency_ms,
        live_neural_model=True,
        tool_invocations=records,
        final_text=combined_text,
        hosted_probe_note=hosted_probe_note,
        sanitized=True,
        recorded_at_utc=utc_now_iso(),
    )
    receipt.verify_invariants()
    return receipt
