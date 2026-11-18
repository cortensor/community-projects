"""OpenMinion 0.1 + Cortensor multi-agent control-plane security engine."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from openminion import (
    APIRuntime,
    Agent,
    Handoff,
    MemoryBundle,
    OpenMinionConfig,
    subagent,
    tool,
)
from openminion.api.handoff import build_delegate_tool
from openminion.base.config.core import (
    AgentProfileConfig,
    ChannelAuthenticityConfig,
    ProvidersConfig,
    RuntimeConfig,
    StorageConfig,
)
from openminion.base.config.providers import CortensorProviderConfig, OpenAIProviderConfig

from sentinel.rpc_tools import ControlPlaneReport, analyze_control_plane

_TARGET_RE = re.compile(r"chain=([a-zA-Z0-9_-]+)\s+address=(0x[a-fA-F0-9]{40})")


class LoopbackInferenceServer:
    """Deterministic OpenAI + Cortensor Router loopback server for offline/verifiable runs."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        outer = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(raw_body)
                outer.requests.append({"path": self.path, "payload": payload})
                resp = outer._handle_completion(payload)
                encoded = json.dumps(resp).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def do_GET(self) -> None:
                if self.path.rstrip("/").endswith("/models"):
                    data = {"object": "list", "data": [{"id": "gpt-oss-20b", "object": "model"}]}
                else:
                    data = {"status": "ok", "service": "cortensor-openminion-loopback"}
                encoded = json.dumps(data).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args: Any) -> None:
                return

        self._server = HTTPServer(("127.0.0.1", 0), _Handler)
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def openai_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    @property
    def cortensor_base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v2/completions"

    def __enter__(self) -> "LoopbackInferenceServer":
        self._thread.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self._server.shutdown()
        self._server.server_close()

    @staticmethod
    def _extract_last_user(messages: list[dict[str, Any]], prompt_fallback: str) -> str:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
        return prompt_fallback

    def _handle_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages") or []
        prompt_text = str(payload.get("prompt") or "")
        last_user = self._extract_last_user(messages, prompt_text)
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        tools_declared = payload.get("tools") or []
        tool_names = {
            (t.get("function") or {}).get("name", "")
            for t in tools_declared
            if isinstance(t, dict)
        }

        # Stage 1: Emit real tool call when inspect_control_plane_tool is available
        if (
            "AUDIT_CONTROL_PLANE" in last_user
            and "inspect_control_plane_tool" in tool_names
            and not tool_msgs
        ):
            match = _TARGET_RE.search(last_user)
            chain = match.group(1) if match else "ethereum"
            address = (
                match.group(2)
                if match
                else "0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE"
            )
            args = json.dumps({"chain": chain, "address": address})
            return {
                "id": "chatcmpl-sentinel-tool",
                "object": "chat.completion",
                "model": payload.get("model", "gpt-oss-20b"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_inspect_cp",
                                    "type": "function",
                                    "function": {
                                        "name": "inspect_control_plane_tool",
                                        "arguments": args,
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

        # Stage 2: Generic tool probe support (used by SDK verification probes)
        if "RUN_PROBE_TOOL" in last_user and "probe_echo" in tool_names and not tool_msgs:
            return {
                "id": "chatcmpl-probe-tool",
                "object": "chat.completion",
                "model": payload.get("model", "gpt-oss-20b"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_probe",
                                    "type": "function",
                                    "function": {
                                        "name": "probe_echo",
                                        "arguments": json.dumps({"value": "sentinel-ok"}),
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            }

        # Stage 3: Final synthesis responses
        if tool_msgs:
            raw_tool = str(tool_msgs[-1].get("content") or "")
            content = f"TOOL_SYNTHESIS_OK::{raw_tool}"
        elif "SKEPTIC_VERIFY" in last_user:
            if "FORCE_DISAGREE" in last_user:
                content = "SKEPTIC_DISAGREE::independent verification flagged anomaly"
            else:
                content = "SKEPTIC_AGREE::control-plane invariants independently verified"
        elif "INCIDENT_ESCALATION" in last_user:
            content = "INCIDENT_LOGGED::escalated via OpenMinion Handoff to incident_desk"
        else:
            content = f"AUDIT_OK::{last_user[:120]}"

        return {
            "id": "chatcmpl-sentinel-final",
            "object": "chat.completion",
            "model": payload.get("model", "gpt-oss-20b"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "text": content,
                    "finish_reason": "stop",
                }
            ],
        }


@dataclass(frozen=True)
class ConsensusAuditResult:
    """Complete verifiable multi-agent audit output backed by OpenMinion + MemoryBundle."""

    target: dict[str, Any]
    control_plane: dict[str, Any]
    primary_run_id: str
    primary_run_state: str
    primary_output: str
    skeptic_child_id: str
    skeptic_run_state: str
    skeptic_output: str
    consensus_status: str
    final_risk_tier: str
    escalated_via_handoff: bool
    handoff_tool_name: str
    handoff_output: str
    memory_bundle_json: str
    provider_mode: str
    duration_ms: float
    runtime_posture: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_sentinel_config(
    *,
    storage_db: Path,
    provider_mode: str = "openai",
    openai_base_url: str | None = None,
    cortensor_base_url: str | None = None,
    model: str = "gpt-oss-20b",
    cortensor_session_id: int = 1,
) -> OpenMinionConfig:
    """Create a hardened OpenMinionConfig avoiding unconfigured-channel traps."""
    os.environ.setdefault("OPENAI_API_KEY", "sk-sentinel-loopback")
    os.environ.setdefault("CORTENSOR_API_KEY", "cor-sentinel-loopback")

    active_provider = "cortensor" if provider_mode == "cortensor" else "openai"
    openai_cfg = OpenAIProviderConfig(
        model=model,
        base_url=openai_base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key_env="OPENAI_API_KEY",
    )
    cortensor_cfg = CortensorProviderConfig(
        model=model,
        base_url=cortensor_base_url
        or os.environ.get("CORTENSOR_BASE_URL", "http://127.0.0.1:8080/api/v2/completions"),
        api_key_env="CORTENSOR_API_KEY",
        session_id=cortensor_session_id,
        session_pool="auto",
        api_mode="auto",
        tool_call_strategy="hybrid",
        privacy_level="high",
    )

    # IMPORTANT OpenMinion 0.1.23 nuance: profile keys MUST match Agent(name=..., agent_id=...)
    # and default_channel must be set to "console" to pass GatewaySecurity channel authenticity.
    agents = {
        "sentinel": AgentProfileConfig(
            name="sentinel",
            role="Primary DeFi Control-Plane Auditor",
            default_channel="console",
            provider=active_provider,
        ),
        "skeptic": AgentProfileConfig(
            name="skeptic",
            role="Independent Skeptic Verifier",
            default_channel="console",
            provider=active_provider,
        ),
        "incident_desk": AgentProfileConfig(
            name="incident_desk",
            role="Fail-Closed Incident Handoff Desk",
            default_channel="console",
            provider=active_provider,
        ),
    }

    return OpenMinionConfig(
        providers=ProvidersConfig(openai=openai_cfg, cortensor=cortensor_cfg),
        agents=agents,
        default_agent="sentinel",
        enabled_channels=["console"],
        channel_authenticity=ChannelAuthenticityConfig(
            mode="warn",
            trusted_channels=["console"],
        ),
        storage=StorageConfig(path=str(storage_db)),
        runtime=RuntimeConfig(),
    )


def create_sentinel_runtime(
    *,
    work_root: Path,
    provider_mode: str = "openai",
    openai_base_url: str | None = None,
    cortensor_base_url: str | None = None,
    model: str = "gpt-oss-20b",
) -> APIRuntime:
    """Initialize APIRuntime cleanly inside work_root."""
    cfg = build_sentinel_config(
        storage_db=work_root / "state.db",
        provider_mode=provider_mode,
        openai_base_url=openai_base_url,
        cortensor_base_url=cortensor_base_url,
        model=model,
    )
    return APIRuntime.from_config(
        config=cfg,
        home_root=work_root / "home",
        data_root=work_root / "data",
    )


def _execute_audit_on_runtime(
    *,
    runtime: APIRuntime,
    target: dict[str, str],
    offline_rpc: bool,
    force_disagree: bool,
    provider_mode: str,
) -> ConsensusAuditResult:
    started = time.perf_counter()
    captured_reports: list[ControlPlaneReport] = []

    @tool(min_scope="READ_ONLY")
    def inspect_control_plane_tool(chain: str, address: str) -> str:
        """Inspect read-only EVM bytecode, EIP-1967 proxy slots, Safe quorum, and timelock."""
        report = analyze_control_plane(
            chain=chain,
            address=address,
            target_id=target.get("id", "custom"),
            name=target.get("name", "Custom Contract"),
            offline=offline_rpc,
        )
        captured_reports.append(report)
        return json.dumps(report.to_dict())

    auditor = Agent(
        runtime=runtime,
        agent_id="sentinel",
        name="sentinel",
        instructions="Inspect smart-contract control-plane safety using read-only RPC tools.",
        tools=[inspect_control_plane_tool],
    )

    primary_prompt = (
        f"AUDIT_CONTROL_PLANE target={target.get('name', 'Contract')} "
        f"chain={target['chain']} address={target['address']}"
    )
    primary_res = auditor.run(primary_prompt)

    report_obj = (
        captured_reports[-1]
        if captured_reports
        else analyze_control_plane(
            chain=target["chain"],
            address=target["address"],
            target_id=target.get("id", "custom"),
            name=target.get("name", "Custom Contract"),
            offline=offline_rpc,
        )
    )

    # Bounded subagent verifier: note memory_posture="none" per OpenMinion v1 constraint
    skeptic_agent = subagent(
        auditor,
        name="skeptic",
        instructions="Challenge primary control-plane findings before releasing risk verdict.",
        memory_posture="none",
    )
    skeptic_prompt = (
        f"SKEPTIC_VERIFY tier={report_obj.risk_tier} score={report_obj.risk_score} "
        f"gov={report_obj.governance_kind}"
        + (" FORCE_DISAGREE" if force_disagree else "")
    )
    skeptic_res = skeptic_agent.run(skeptic_prompt)

    skeptic_agreed = "SKEPTIC_AGREE" in (skeptic_res.text or "")
    consensus_status = "AGREED" if skeptic_agreed else "DISAGREEMENT_FAIL_CLOSED"

    final_tier = report_obj.risk_tier
    if not skeptic_agreed and final_tier in {"LOW", "MEDIUM"}:
        final_tier = "HIGH"

    incident_desk = Agent(
        runtime=runtime,
        agent_id="incident_desk",
        name="incident_desk",
        instructions="Acknowledge escalated HIGH/CRITICAL control-plane alerts.",
    )
    handoff = Handoff(
        target=incident_desk,
        name="transfer_to_incident_desk",
        description="Escalate HIGH/CRITICAL or consensus-failed control-plane findings.",
    )
    delegate_tool = build_delegate_tool(handoff)

    escalated = final_tier in {"HIGH", "CRITICAL"} or not skeptic_agreed
    handoff_output = ""
    if escalated:
        payload = delegate_tool.handler(
            {
                "message": (
                    f"INCIDENT_ESCALATION target={target['address']} "
                    f"final_tier={final_tier} consensus={consensus_status}"
                )
            }
        )
        handoff_output = str((payload or {}).get("content", ""))

    bundle = MemoryBundle(
        version="memory_bundle.v1",
        items=[
            {
                "target": target,
                "risk_tier": final_tier,
                "risk_score": report_obj.risk_score,
                "consensus_status": consensus_status,
                "primary_run_id": primary_res.run_id or "",
                "skeptic_child_id": (
                    skeptic_agent.subagent_context.child_agent_id
                    if skeptic_agent.subagent_context
                    else "skeptic"
                ),
            }
        ],
        metadata={
            "project": "cortensor-openminion-sentinel",
            "provider_mode": provider_mode,
            "escalated": str(escalated).lower(),
        },
    )
    roundtrip_json = MemoryBundle.from_json(bundle.to_json()).to_json()
    posture = runtime.runtime_posture(agent_id="sentinel")

    return ConsensusAuditResult(
        target=dict(target),
        control_plane=report_obj.to_dict(),
        primary_run_id=primary_res.run_id or "",
        primary_run_state=primary_res.run_state or "unknown",
        primary_output=primary_res.text or "",
        skeptic_child_id=(
            skeptic_agent.subagent_context.child_agent_id
            if skeptic_agent.subagent_context
            else "skeptic"
        ),
        skeptic_run_state=skeptic_res.run_state or "unknown",
        skeptic_output=skeptic_res.text or "",
        consensus_status=consensus_status,
        final_risk_tier=final_tier,
        escalated_via_handoff=escalated,
        handoff_tool_name=handoff.resolved_name(),
        handoff_output=handoff_output,
        memory_bundle_json=roundtrip_json,
        provider_mode=provider_mode,
        duration_ms=round((time.perf_counter() - started) * 1000.0, 2),
        runtime_posture={
            "agent": posture.get("agent", "sentinel"),
            "runtime_mode": posture.get("runtime_mode", "brain"),
            "brain_bridge_active": bool(posture.get("brain_bridge_active", False)),
            "canonical_turn_path": posture.get("canonical_turn_path", []),
        },
    )


def run_consensus_audit(
    *,
    target: dict[str, str],
    offline_rpc: bool = False,
    provider_mode: str = "openai",
    use_loopback: bool = True,
    force_disagree: bool = False,
) -> ConsensusAuditResult:
    """Run one complete Cortensor + OpenMinion consensus audit for a target contract."""
    with TemporaryDirectory(ignore_cleanup_errors=True) as td:
        root = Path(td)
        if use_loopback:
            with LoopbackInferenceServer() as srv:
                rt = create_sentinel_runtime(
                    work_root=root,
                    provider_mode=provider_mode,
                    openai_base_url=srv.openai_base_url,
                    cortensor_base_url=srv.cortensor_base_url,
                )
                try:
                    return _execute_audit_on_runtime(
                        runtime=rt,
                        target=target,
                        offline_rpc=offline_rpc,
                        force_disagree=force_disagree,
                        provider_mode=f"{provider_mode}:loopback",
                    )
                finally:
                    rt.close()
        else:
            rt = create_sentinel_runtime(work_root=root, provider_mode=provider_mode)
            try:
                return _execute_audit_on_runtime(
                    runtime=rt,
                    target=target,
                    offline_rpc=offline_rpc,
                    force_disagree=force_disagree,
                    provider_mode=provider_mode,
                )
            finally:
                rt.close()
