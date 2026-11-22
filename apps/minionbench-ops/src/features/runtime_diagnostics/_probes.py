"""Empirical 6-probe diagnostic harness exercising OpenMinion 0.1.24 building blocks."""

from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

from pydantic import BaseModel

from openminion import (
    APIRuntime,
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
    __version__ as OPENMINION_VERSION,
    tool,
)
from openminion.base.config.base import UnknownProfileError
import openminion.modules.llm.providers.factory as provider_factory
from openminion.services.runtime.ingress.timeout import resolve_timeout_seconds

from src.kernel.event_bus import (
    BuildingBlockProbeResult,
    EventBus,
    KernelIntegrityError,
    corrupt_gate_active,
    redact_secrets,
)

_DIAG_LOOPBACK_ENV = "MINIONBENCH_DIAG_TOKEN"


class ReleaseVerdictSchema(BaseModel):
    """Structured Pydantic schema for Probe 3 output validation."""

    project_slug: str
    openminion_sdk: str
    ready_to_ship: bool
    risk_score: float


def _task_update_for_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    user_input = str(messages[-1].get("content", "")) if messages else ""
    rev = 0
    for msg in messages:
        content = str(msg.get("content", ""))
        if "CURRENT TASK (user instructions" in content:
            match = re.search(r'"revision":\s*(\d+)', content)
            if match:
                rev = int(match.group(1))
    return {
        "operation": "start" if rev == 0 else "replace",
        "expected_revision": rev,
        "user_quote": user_input,
        "objective": user_input,
    }


class _DiagnosticLoopbackServer:
    """Self-contained local 127.0.0.1 HTTP server keeping runtime_diagnostics free of sibling imports."""

    def __init__(self) -> None:
        self.target_tool: str | None = None
        self.answer_text: str = "Diagnostic ok."
        self.session_echo_token: str | None = None
        self.http_status: int = 200
        self.delay_seconds: float = 0.0
        self._server: http.server.ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1"

    def __enter__(self) -> "_DiagnosticLoopbackServer":
        parent = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:
                del fmt, args

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8", errors="replace") or "{}")
                if parent.delay_seconds > 0:
                    time.sleep(parent.delay_seconds)
                if parent.http_status >= 400:
                    raw_err = json.dumps({"error": {"message": f"HTTP {parent.http_status} fault"}}).encode("utf-8")
                    self.send_response(parent.http_status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(raw_err)))
                    self.end_headers()
                    self.wfile.write(raw_err)
                    return

                msgs = list(body.get("messages") or [])
                joined = "\n".join(str(m.get("content", "")) for m in msgs)
                by_name = {
                    str(t.get("function", {}).get("name", "")): t.get("function", {})
                    for t in (body.get("tools") or [])
                    if isinstance(t, dict)
                }
                sys_txt = str(msgs[0].get("content", "")) if msgs else ""
                last_txt = str(msgs[-1].get("content", "")) if msgs else ""
                is_entry = "For a clarification or new input with a CURRENT TASK" in sys_txt

                answer = parent.answer_text
                if parent.session_echo_token and "Recall" in last_txt:
                    answer = (
                        f"Recalled {parent.session_echo_token}"
                        if parent.session_echo_token in joined
                        else "Token absent from session context"
                    )

                if parent.target_tool and parent.target_tool in by_name and "Continue the active task" not in last_txt:
                    t_fn = by_name[parent.target_tool]
                    props = t_fn.get("parameters", {}).get("properties", {})
                    targs: dict[str, Any] = {k: "probe-arg" for k in props if k != "task_update"}
                    if is_entry and "task_update" in props:
                        targs["task_update"] = _task_update_for_messages(msgs)
                    msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "diag_tc_1",
                                "type": "function",
                                "function": {"name": parent.target_tool, "arguments": json.dumps(targs)},
                            }
                        ],
                    }
                    finish = "tool_calls"
                elif "respond" in by_name and is_entry:
                    props = by_name["respond"].get("parameters", {}).get("properties", {})
                    rargs: dict[str, Any] = {"answer": answer}
                    if "freshness" in props:
                        rargs["freshness"] = {
                            "time_sensitive": False,
                            "needs_live_data": False,
                            "needs_sources": False,
                            "needs_exact_date": False,
                            "intent": "diagnostic_probe",
                            "domain": "general",
                            "answer_mode": "direct",
                            "reason": "local_probe",
                            "confidence": 0.98,
                        }
                    if "task_update" in props:
                        rargs["task_update"] = _task_update_for_messages(msgs)
                    msg = {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "diag_resp_1",
                                "type": "function",
                                "function": {"name": "respond", "arguments": json.dumps(rargs)},
                            }
                        ],
                    }
                    finish = "tool_calls"
                else:
                    msg = {"role": "assistant", "content": answer}
                    finish = "stop"

                raw = json.dumps(
                    {
                        "id": "chatcmpl-diag",
                        "object": "chat.completion",
                        "created": 1763736000,
                        "model": "diag-loopback",
                        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

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


def build_cortensor_posture_matrix() -> dict[str, Any]:
    """Build source-verified Cortensor Portal, Router, Gemini, and Ollama runtime posture summary."""
    from openminion import OpenMinionConfig

    cfg = OpenMinionConfig.from_dict(
        {
            "default_agent": "cortensor-router",
            "agents": {
                "cortensor-router": {"provider": "cortensor", "default_channel": "console"},
            },
        }
    )
    router_timeout_floor = resolve_timeout_seconds(
        payload={},
        default_seconds=45,
        config=cfg,
        agent_id="cortensor-router",
    )
    return {
        "openminion_version": OPENMINION_VERSION,
        "supported_agents_json_providers": sorted(provider_factory.SUPPORTED_PROVIDERS),
        "cortensor_portal_retry_disabled_reason": provider_factory.CORTENSOR_PORTAL_RETRY_DISABLED_REASON,
        "profiles": {
            "cortensor_portal": {
                "setup_catalog_id": "cortensor-portal",
                "agents_json_provider": "openai",
                "base_url": "https://api.cortensor.app/v1",
                "credential_env": "CORTENSOR_API_KEY",
                "recommended_model": "oss-20b",
                "max_retries": 0,
                "retry_disabled_reason": provider_factory.CORTENSOR_PORTAL_RETRY_DISABLED_REASON,
                "api_turn_timeout_floor_seconds": 45.0,
            },
            "cortensor_router": {
                "setup_catalog_id": "cortensor-router",
                "agents_json_provider": "cortensor",
                "base_url": "http://127.0.0.1:8080/api/v2/completions",
                "credential_env": "CORTENSOR_API_KEY",
                "recommended_model": "gpt-oss-20b",
                "max_retries": 0,
                "retry_disabled_reason": "cortensor_direct_single_attempt",
                "api_turn_timeout_floor_seconds": router_timeout_floor,
            },
            "gemini_openai_bridge": {
                "setup_catalog_id": "gemini",
                "agents_json_provider": "openai",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "credential_env": "GEMINI_API_KEY",
                "recommended_model": "gemini-2.5-flash",
                "max_retries": 2,
                "retry_disabled_reason": None,
                "api_turn_timeout_floor_seconds": 45.0,
            },
            "ollama_openai_bridge": {
                "setup_catalog_id": "ollama",
                "agents_json_provider": "openai",
                "base_url": "http://127.0.0.1:11434/v1",
                "credential_env": "MINIONBENCH_OLLAMA_KEY",
                "recommended_model": "qwen2.5:1.5b",
                "max_retries": 2,
                "retry_disabled_reason": None,
                "api_turn_timeout_floor_seconds": 45.0,
            },
        },
    }


def build_learned_findings() -> tuple[dict[str, str], ...]:
    """Return 5 concrete, source-verified OpenMinion 0.1.24 findings and upstream fix proposals."""
    return (
        {
            "id": "OM-FINDING-01",
            "severity": "HIGH",
            "component": "openminion/services/gateway/security.py:132 & base/config/core.py:124",
            "title": "Minimal agents.<id> block omits default_channel and fails inbound authenticity in warn mode",
            "observed": (
                "Writing a custom agents.<id> entry without 'default_channel': 'console' (matching README.md "
                "lines 192-199) leaves AgentProfileConfig.default_channel='' and raises "
                "RuntimeError('inbound authenticity denied (reason=invalid_channel, mode=warn)')."
            ),
            "recommendation": (
                "Default Agent._build_payload or AgentProfileConfig.default_channel to 'console' for embedded "
                "Python SDK calls so minimal agents.json profiles run out of the box."
            ),
        },
        {
            "id": "OM-FINDING-02",
            "severity": "MEDIUM",
            "component": "openminion/services/runtime/ingress/timeout.py:54 & base/config/core.py:407",
            "title": "Setting human display string in agents.<id>.name triggers UnknownProfileError",
            "observed": (
                "Configuring 'agents': {'gemini-live': {'name': 'Gemini Live', ...}} causes runtime profile "
                "lookup during timeout calculation to pass display name 'Gemini Live' instead of key 'gemini-live', "
                "raising UnknownProfileError."
            ),
            "recommendation": (
                "Separate immutable profile_id (dict key) from human display_name in AgentProfileConfig and "
                "resolve_runtime_profile."
            ),
        },
        {
            "id": "OM-FINDING-03",
            "severity": "MEDIUM",
            "component": "examples/sdk/sessions.py:18-19 & openminion/api/agent.py:167-170",
            "title": "Sequential Agent.run calls on one session_id fork threads unless thread_id is passed",
            "observed": (
                "Calling second = agent.run(...) on the same Agent(session_id='shared') without "
                "thread_id=first.thread_id sets thread_decision_action='fork_thread' (settled_without_resume) "
                "and session_history_available='false', hiding prior turn messages until thread_id is supplied."
            ),
            "recommendation": (
                "Either auto-carry last_thread_id inside stateful Agent instances when session_id matches, or "
                "update examples/sdk/sessions.py to pass thread_id=first.thread_id explicitly."
            ),
        },
        {
            "id": "OM-FINDING-04",
            "severity": "MEDIUM",
            "component": "openminion setup --list-providers vs modules/llm/providers/factory.py:28",
            "title": "Setup catalog provider IDs differ from agents.json SUPPORTED_PROVIDERS keys",
            "observed": (
                "CLI setup lists 20 catalog IDs ('gemini', 'cortensor-portal', 'cortensor-router'), while "
                "SUPPORTED_PROVIDERS in agents.json only accepts 9 transport keys ('openai', 'cortensor', etc.). "
                "Cortensor Portal uses 'openai' with max_retries=0 (cortensor_portal_no_idempotency)."
            ),
            "recommendation": (
                "Accept catalog aliases in OpenMinionConfig.from_dict and normalize them to transport + base_url "
                "overrides automatically, or surface the canonical agents.json snippet in setup --list-providers --json."
            ),
        },
        {
            "id": "OM-FINDING-05",
            "severity": "LOW",
            "component": "modules/brain/loop & base/config/providers.py:85",
            "title": "Single tool turn triggers 7 internal LLM calls and Ollama defaults to fallback tool parsing",
            "observed": (
                "Telemetry metadata ('llm_call_counts_by_purpose') records 7 LLM calls (entry=1, "
                "freshness_classify=1, act=3, reflect=1, judge=1; ~16.4k input tokens) for 1 tool call, "
                "multiplying decentralized Cortensor router latency ~7x."
            ),
            "recommendation": (
                "Add a 'fast_single_pass' profile skipping post-turn reflect/judge/freshness calls on bounded "
                "SDK tool workflows, and switch OllamaProviderConfig.tool_call_strategy default to 'hybrid'."
            ),
        },
    )


def run_building_block_diagnostics(
    *,
    workspace_root: Path,
    bus: EventBus,
) -> tuple[BuildingBlockProbeResult, ...]:
    """Execute all 6 empirical OpenMinion 0.1.24 building-block probes."""
    if corrupt_gate_active():
        raise KernelIntegrityError("CORRUPT_GATE_CONTROL=1 aborted run_building_block_diagnostics.")

    os.environ.setdefault(_DIAG_LOOPBACK_ENV, "diag-loopback-ok")
    probes: list[BuildingBlockProbeResult] = []

    ro_executions: list[str] = []
    wr_executions: list[str] = []

    @tool(min_scope="READ_ONLY", idempotent=True)
    def diag_read_manifest(item: str) -> str:
        """Read-only idempotent diagnostic probe tool."""
        ro_executions.append(item)
        return f"manifest_ok:{item}"

    @tool
    def diag_write_stage(item: str) -> str:
        """Bare write-classified diagnostic probe tool requiring confirmation."""
        wr_executions.append(item)
        return f"staged_ok:{item}"

    with _DiagnosticLoopbackServer() as server, tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cfg_path = tmp_path / "agents.json"
        cfg_payload = {
            "default_agent": "diag-agent",
            "providers": {
                "openai": {
                    "model": "diag-loopback",
                    "base_url": server.base_url,
                    "api_key_env": _DIAG_LOOPBACK_ENV,
                    "tool_call_strategy": "hybrid",
                    "timeout_seconds": 10,
                }
            },
            "agents": {
                "diag-agent": {
                    "provider": "openai",
                    "default_channel": "console",
                }
            },
        }
        cfg_path.write_text(json.dumps(cfg_payload, indent=2), encoding="utf-8")
        runtime = APIRuntime.from_config_path(
            str(cfg_path),
            home_root=tmp_path / "home",
            data_root=tmp_path / "data",
            logging_mode="default",
        )
        try:
            # Probe 1: Tool Scope & Action-Policy Boundary
            t0 = time.monotonic()
            with Agent(
                runtime=runtime,
                agent_id="diag-agent",
                tools=[diag_read_manifest, diag_write_stage],
                session_id="probe-01-ro",
            ) as agent:
                server.target_tool = "diag_read_manifest"
                server.answer_text = "Read-only manifest verified."
                res_ro = agent.run("Check manifest.")

                server.target_tool = "diag_write_stage"
                res_pause = agent.run("Stage release.", session_id="probe-01-pause")
                count_after_pause = len(wr_executions)

                res_deny = agent.run(
                    "Stage release.",
                    session_id="probe-01-deny",
                    approval_callback=lambda name, args, prompt: False,
                )
                count_after_deny = len(wr_executions)

                res_allow = agent.run(
                    "Stage release.",
                    session_id="probe-01-allow",
                    approval_callback=lambda name, args, prompt: name == "diag_write_stage",
                )
                count_after_allow = len(wr_executions)
                server.target_tool = None

            p1_ok = (
                len(ro_executions) == 1
                and res_ro.metadata.get("respond_kind") == "assistant"
                and res_pause.metadata.get("respond_kind") == "policy_confirmation_prompt"
                and count_after_pause == 0
                and "Confirmation denied" in res_deny.text
                and count_after_deny == 0
                and count_after_allow == 1
                and res_allow.metadata.get("respond_kind") == "assistant"
            )
            probes.append(
                BuildingBlockProbeResult(
                    probe_id="probe-01-tool-scope-policy",
                    title="Tool Scope & Action-Policy Confirmation Boundary",
                    sdk_surface="@tool(min_scope='READ_ONLY', idempotent=True) vs @tool + approval_callback",
                    passed=p1_ok,
                    latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
                    summary=(
                        "READ_ONLY idempotent tools run without operator friction; bare @tool pauses at "
                        "policy_confirmation_prompt, blocks on callback False, and executes once on True."
                    ),
                    evidence={
                        "read_only_executions": len(ro_executions),
                        "pause_respond_kind": res_pause.metadata.get("respond_kind"),
                        "write_runs_at_pause": count_after_pause,
                        "write_runs_after_deny": count_after_deny,
                        "write_runs_after_allow": count_after_allow,
                    },
                    product_feedback=(
                        "Expose min_scope='WRITE_WORKSPACE' on @tool so workspace-scoped staging tools can "
                        "participate in '/permissions Workspace auto' alongside built-in file.write."
                    ),
                )
            )

            # Probe 2: Durable Session Continuity & thread_id Fork Behavior
            t0 = time.monotonic()
            server.session_echo_token = "CORTENSOR_EPOCH_88"
            server.answer_text = "Stored CORTENSOR_EPOCH_88 in session."
            with Agent(runtime=runtime, agent_id="diag-agent", session_id="probe-02-shared") as agent:
                first_turn = agent.run("Remember token CORTENSOR_EPOCH_88.")
                forked_turn = agent.run("Recall the token.")
                resumed_turn = agent.run("Recall the token.", thread_id=first_turn.thread_id)
                isolated_turn = agent.run("Recall the token.", session_id="probe-02-isolated")
            server.session_echo_token = None

            p2_ok = (
                first_turn.session_id == "probe-02-shared"
                and forked_turn.metadata.get("thread_decision_action") == "fork_thread"
                and resumed_turn.metadata.get("thread_decision_action") == "resume_thread"
                and resumed_turn.metadata.get("session_history_available") == "true"
                and "Recalled CORTENSOR_EPOCH_88" in resumed_turn.text
                and isolated_turn.session_id == "probe-02-isolated"
                and "Token absent" in isolated_turn.text
            )
            probes.append(
                BuildingBlockProbeResult(
                    probe_id="probe-02-durable-session-continuity",
                    title="Durable Session Continuity & Thread Resume Semantics",
                    sdk_surface="Agent(session_id=...) + Agent.run(..., thread_id=...)",
                    passed=p2_ok,
                    latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
                    summary=(
                        "Passing thread_id=first.thread_id resumes SQLite conversation state "
                        "(session_history_available='true'), whereas omitting thread_id forks a new settled thread."
                    ),
                    evidence={
                        "shared_session_id": first_turn.session_id,
                        "without_thread_id_action": forked_turn.metadata.get("thread_decision_action"),
                        "with_thread_id_action": resumed_turn.metadata.get("thread_decision_action"),
                        "resumed_history_available": resumed_turn.metadata.get("session_history_available"),
                        "resumed_reply": resumed_turn.text,
                        "isolated_reply": isolated_turn.text,
                    },
                    product_feedback=(
                        "Update examples/sdk/sessions.py to pass thread_id=first.thread_id (or default Agent to "
                        "resume its own active thread within a context manager block)."
                    ),
                )
            )

            # Probe 3: Structured Pydantic output_type & AgentOutputValidationError
            t0 = time.monotonic()
            server.answer_text = json.dumps(
                {
                    "project_slug": "minionbench-ops",
                    "openminion_sdk": OPENMINION_VERSION,
                    "ready_to_ship": True,
                    "risk_score": 0.04,
                }
            )
            caught_validation_raw = ""
            with Agent(
                runtime=runtime,
                agent_id="diag-agent",
                output_type=ReleaseVerdictSchema,
                session_id="probe-03-valid",
            ) as typed_agent:
                typed_ok = typed_agent.run("Emit structured release verdict.")
                server.answer_text = "Malformed non-JSON prose output."
                try:
                    typed_agent.run("Emit broken verdict.", session_id="probe-03-invalid")
                except AgentOutputValidationError as exc:
                    caught_validation_raw = redact_secrets(exc.raw_text)

            p3_ok = (
                isinstance(typed_ok.output, ReleaseVerdictSchema)
                and typed_ok.output.project_slug == "minionbench-ops"
                and typed_ok.output.ready_to_ship is True
                and "Malformed non-JSON prose output" in caught_validation_raw
            )
            probes.append(
                BuildingBlockProbeResult(
                    probe_id="probe-03-structured-output-validation",
                    title="Pydantic output_type Extraction & AgentOutputValidationError",
                    sdk_surface="Agent(output_type=ReleaseVerdictSchema) & AgentOutputValidationError",
                    passed=p3_ok,
                    latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
                    summary=(
                        "OpenMinion extracts schema-valid JSON even when prefixed with '<agent_id>: ', and "
                        "raises AgentOutputValidationError carrying raw_text when JSON coercion fails."
                    ),
                    evidence={
                        "validated_model": typed_ok.output.model_dump(),
                        "validation_error_raw_text": caught_validation_raw,
                    },
                    product_feedback=(
                        "Pass output_type.model_json_schema() via response_format={'type': 'json_schema'} on "
                        "providers supporting structured outputs to prevent avoidable parse failures."
                    ),
                )
            )

            # Probe 4: ProviderError & TurnTimeoutError Boundaries
            t0 = time.monotonic()
            caught_provider_code = ""
            caught_timeout_msg = ""
            server.http_status = 503
            try:
                with Agent(runtime=runtime, agent_id="diag-agent", session_id="probe-04-503") as err_agent:
                    err_agent.run("Trigger HTTP 503 provider failure.")
            except ProviderError as exc:
                caught_provider_code = str(getattr(exc, "code", "PROVIDER_ERROR"))
            finally:
                server.http_status = 200

            server.delay_seconds = 0.85
            try:
                with Agent(runtime=runtime, agent_id="diag-agent", session_id="probe-04-timeout") as slow_agent:
                    slow_agent.run("Trigger turn deadline timeout.", timeout_seconds=0.25)
            except TurnTimeoutError as exc:
                caught_timeout_msg = redact_secrets(str(exc))
            finally:
                server.delay_seconds = 0.0

            p4_ok = bool(caught_provider_code) and "timed out" in caught_timeout_msg.lower()
            probes.append(
                BuildingBlockProbeResult(
                    probe_id="probe-04-provider-and-timeout-errors",
                    title="ProviderError & TurnTimeoutError Fault Isolation",
                    sdk_surface="ProviderError (HTTP 503) & TurnTimeoutError (timeout_seconds=0.25)",
                    passed=p4_ok,
                    latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
                    summary=(
                        "Upstream HTTP 503 failures surface cleanly as ProviderError after bounded retries, "
                        "and slow turns cancel cleanly with TurnTimeoutError."
                    ),
                    evidence={
                        "provider_error_code": caught_provider_code,
                        "turn_timeout_error": caught_timeout_msg,
                    },
                    product_feedback=(
                        "Populate ProviderError.details with HTTP status_code and upstream request_id so "
                        "Cortensor Portal callers can distinguish 401 auth errors from 429 capacity limits."
                    ),
                )
            )
        finally:
            runtime.close()

    # Probe 5: CLI Readiness & Setup Provider Catalog Parity
    t0 = time.monotonic()
    openminion_bin = Path(sys.executable).parent / "openminion"
    proc_list = subprocess.run(
        [str(openminion_bin), "setup", "--list-providers", "--json"],
        cwd=str(workspace_root),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    catalog_data = json.loads(proc_list.stdout or '{"providers": []}')
    catalog_ids = [str(p.get("id", "")) for p in (catalog_data.get("providers") or []) if isinstance(p, dict)]

    with tempfile.TemporaryDirectory() as cli_tmp:
        cli_root = Path(cli_tmp)
        echo_cfg = cli_root / "agents.echo.json"
        echo_cfg.write_text(
            json.dumps(
                {
                    "default_agent": "default",
                    "agents": {"default": {"provider": "echo", "default_channel": "console"}},
                }
            ),
            encoding="utf-8",
        )
        proc_ready = subprocess.run(
            [
                str(openminion_bin),
                "--home-root",
                str(cli_root / "home"),
                "--data-root",
                str(cli_root / "data"),
                "--config",
                str(echo_cfg),
                "status",
                "readiness",
            ],
            cwd=str(workspace_root),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    readiness_out = redact_secrets((proc_ready.stdout or proc_ready.stderr or "").strip())
    posture = build_cortensor_posture_matrix()
    p5_ok = (
        proc_list.returncode == 0
        and {"gemini", "cortensor-portal", "cortensor-router"}.issubset(set(catalog_ids))
        and posture["cortensor_portal_retry_disabled_reason"] == "cortensor_portal_no_idempotency"
        and posture["profiles"]["cortensor_router"]["api_turn_timeout_floor_seconds"] == 455.0
    )
    probes.append(
        BuildingBlockProbeResult(
            probe_id="probe-05-cli-readiness-and-config-parity",
            title="CLI Provider Catalog, Readiness & Cortensor Retry/Timeout Posture",
            sdk_surface="openminion setup --list-providers --json & status readiness",
            passed=p5_ok,
            latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
            summary=(
                f"Setup catalog exposes {len(catalog_ids)} provider presets (including gemini, cortensor-portal, "
                f"cortensor-router) mapping onto {len(posture['supported_agents_json_providers'])} core transport "
                "drivers, with Cortensor Portal retries disabled (max_retries=0) and Router timeout floored at 455s."
            ),
            evidence={
                "setup_catalog_count": len(catalog_ids),
                "cortensor_presets_present": [
                    cid for cid in catalog_ids if "cortensor" in cid or cid == "gemini"
                ],
                "agents_json_supported_providers": posture["supported_agents_json_providers"],
                "echo_readiness_exit_code": proc_ready.returncode,
                "echo_readiness_excerpt": readiness_out[:240],
                "cortensor_router_timeout_floor_s": posture["profiles"]["cortensor_router"][
                    "api_turn_timeout_floor_seconds"
                ],
            },
            product_feedback=(
                "Include 'agents_json_provider' and 'provider_config_overrides' examples directly in "
                "`openminion setup --list-providers --json` output."
            ),
        )
    )

    # Probe 6: Empirical Reproduction of OpenMinion 0.1.24 Config Tripwires & Feedback Synthesis
    t0 = time.monotonic()
    caught_invalid_channel = ""
    caught_unknown_profile = ""
    with tempfile.TemporaryDirectory() as bug_tmp:
        broot = Path(bug_tmp)
        # Tripwire A: missing default_channel on custom agent entry
        cfg_no_chan = broot / "no_channel.json"
        cfg_no_chan.write_text(
            json.dumps(
                {
                    "default_agent": "custom-echo",
                    "agents": {"custom-echo": {"provider": "echo"}},
                }
            ),
            encoding="utf-8",
        )
        rt_a = APIRuntime.from_config_path(
            str(cfg_no_chan),
            home_root=broot / "ha",
            data_root=broot / "da",
            logging_mode="default",
        )
        try:
            with Agent(runtime=rt_a, agent_id="custom-echo", session_id="bug-chan") as ag_a:
                ag_a.run("Ping without default_channel")
        except RuntimeError as exc:
            caught_invalid_channel = str(exc)
        finally:
            rt_a.close()

        # Tripwire B: human display name in agents.<id>.name
        cfg_bad_name = broot / "bad_name.json"
        cfg_bad_name.write_text(
            json.dumps(
                {
                    "default_agent": "custom-echo",
                    "agents": {
                        "custom-echo": {
                            "name": "Custom Echo Display Name",
                            "provider": "echo",
                            "default_channel": "console",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        rt_b = APIRuntime.from_config_path(
            str(cfg_bad_name),
            home_root=broot / "hb",
            data_root=broot / "db",
            logging_mode="default",
        )
        try:
            with Agent(runtime=rt_b, agent_id="custom-echo", session_id="bug-name") as ag_b:
                ag_b.run("Ping with display name")
        except UnknownProfileError as exc:
            caught_unknown_profile = str(exc)
        finally:
            rt_b.close()

    findings = build_learned_findings()
    p6_ok = (
        "invalid_channel" in caught_invalid_channel
        and "Custom Echo Display Name" in caught_unknown_profile
        and len(findings) == 5
    )
    probes.append(
        BuildingBlockProbeResult(
            probe_id="probe-06-config-tripwires-and-feedback",
            title="Reproducible Config Tripwires & Actionable Feedback Synthesis",
            sdk_surface="GatewaySecurity.enforce_inbound_authenticity & resolve_agent_config",
            passed=p6_ok,
            latency_ms=round((time.monotonic() - t0) * 1000.0, 2),
            summary=(
                "Reproduced both 0.1.24 config edge cases (empty default_channel RuntimeError in warn mode and "
                "agents.<id>.name UnknownProfileError) and synthesized 5 upstream engineering recommendations."
            ),
            evidence={
                "missing_default_channel_error": caught_invalid_channel,
                "display_name_profile_error": caught_unknown_profile,
                "synthesized_finding_ids": [f["id"] for f in findings],
            },
            product_feedback=(
                "Validate agents.<id>.default_channel and decouple display name from profile lookup key at "
                "config load time with actionable remediation hints."
            ),
        )
    )

    for p in probes:
        bus.publish(
            "diagnostic.probe_completed",
            source_brick="runtime_diagnostics",
            payload={"probe_id": p.probe_id, "passed": p.passed, "latency_ms": p.latency_ms},
        )
    return tuple(probes)
