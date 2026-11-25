"""OpenMinion 0.1.24 runtime bootstrap, declarative Agent, submit_turn, and Handoff wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import threading
import time
from typing import Any, Callable, Literal

from openminion import (
    APIRuntime,
    Agent,
    AgentOutputValidationError,
    AgentRunResult,
    Handoff,
    OpenMinionConfig,
    ProviderError,
    TurnTimeoutError,
    subagent,
)
from openminion.base.config.core import (
    ActionPolicyConfig,
    AgentProfileConfig,
    StorageConfig,
)
from openminion.base.config.providers import (
    CortensorProviderConfig,
    OllamaProviderConfig,
    OpenAIProviderConfig,
    ProvidersConfig,
)
from openminion.base.config.runtime import RuntimeConfig
from openminion.modules.runtime.contracts import TurnChunk, TurnResponse

from cortensor_router_doctor.models import (
    QuarantineAction,
    RouterAuditReport,
    SLAPolicyEvaluation,
    verify_report_against_evidence,
)
from cortensor_router_doctor.tools import (
    apply_router_quarantine,
    evaluate_sla_policy,
    probe_cortensor_router,
    start_evidence_ledger,
    stop_evidence_ledger,
)

ProviderPreset = Literal["ollama", "cortensor-portal", "cortensor-router", "echo"]
ApprovalCallback = Callable[[str, dict[str, Any], str], bool]


@dataclass
class AuditExecutionResult:
    """Structured result returned by `run_audit`, including telemetry and approval trace."""

    run_result: AgentRunResult[RouterAuditReport] | None
    report: RouterAuditReport
    deltas: list[dict[str, Any]] = field(default_factory=list)
    approval_events: list[dict[str, Any]] = field(default_factory=list)
    verified_against_evidence: bool = False
    tool_trace: list[str] = field(default_factory=list)
    reconciled_from_tool_ledger: bool = False
    raw_model_reply: str = ""


@dataclass
class SubmitTurnAuditResult:
    """Structured result returned by `run_audit_via_submit_turn`."""

    trace_id: str
    response: TurnResponse
    chunks: list[dict[str, Any]] = field(default_factory=list)
    approval_resolutions: list[dict[str, Any]] = field(default_factory=list)


def build_isolated_config(
    root_dir: Path,
    *,
    provider: ProviderPreset = "ollama",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str = "",
    session_id: int = 1,
    agent_id: str = "router-doctor",
    chat_turn_timeout_seconds: float | None = None,
) -> OpenMinionConfig:
    """Build an isolated, reproducible `OpenMinionConfig` for OpenMinion 0.1.24.

    Workarounds encoded by default:
    - Sets `AgentProfileConfig.default_channel='console'` to prevent `invalid_channel` errors.
    - Sets `OllamaProviderConfig.tool_call_strategy='native'` to work around OpenMinion 0.1.24
      Bug #1 where Ollama's default `'fallback'` strategy drops standard tool calls.
    - Uses `openai` adapter + `chat_turn_timeout_seconds=480.0` for `cortensor-portal`.
    - Disables unrelated plugins (`enabled_plugins=[]`), reactions, and telemetry.
    """
    resolved_root = Path(root_dir).expanduser().resolve()
    providers = ProvidersConfig()

    if provider == "ollama":
        agent_provider = "ollama"
        providers = ProvidersConfig(
            ollama=OllamaProviderConfig(
                model=model or "qwen2.5:1.5b",
                base_url=base_url or "http://127.0.0.1:11434",
                timeout_seconds=120,
                temperature=0.0,
                api_key=api_key,
                tool_call_strategy="native",
            )
        )
        effective_timeout = (
            float(chat_turn_timeout_seconds)
            if chat_turn_timeout_seconds is not None
            else 180.0
        )
    elif provider == "cortensor-portal":
        agent_provider = "openai"
        providers = ProvidersConfig(
            openai=OpenAIProviderConfig(
                model=model or "gpt-oss-20b",
                base_url=base_url or "https://portal.cortensor.network/v1",
                api_key=api_key,
                api_key_env="CORTENSOR_API_KEY",
                timeout_seconds=420,
                temperature=0.0,
                tool_call_strategy="hybrid",
            )
        )
        effective_timeout = (
            float(chat_turn_timeout_seconds)
            if chat_turn_timeout_seconds is not None
            else 480.0
        )
    elif provider == "cortensor-router":
        agent_provider = "cortensor"
        providers = ProvidersConfig(
            cortensor=CortensorProviderConfig(
                model=model or "gpt-oss-20b",
                base_url=base_url or "http://127.0.0.1:8080/api/v2/completions",
                api_key=api_key,
                api_key_env="CORTENSOR_API_KEY",
                session_id=int(session_id),
                timeout_seconds=420,
                temperature=0.0,
                tool_call_strategy="hybrid",
            )
        )
        effective_timeout = (
            float(chat_turn_timeout_seconds)
            if chat_turn_timeout_seconds is not None
            else 480.0
        )
    elif provider == "echo":
        agent_provider = "echo"
        effective_timeout = (
            float(chat_turn_timeout_seconds)
            if chat_turn_timeout_seconds is not None
            else 30.0
        )
    else:
        raise ValueError(f"Unsupported provider preset: {provider!r}")

    profile = AgentProfileConfig(
        name=agent_id,
        role="Cortensor Router SLA & PoI Consensus Auditor",
        default_channel="console",
        provider=agent_provider,
        action_policy=ActionPolicyConfig(
            mode="auto",
            default_action="require_confirm",
            allow_read_only_without_prompt=True,
        ),
    )

    return OpenMinionConfig(
        agents={agent_id: profile},
        default_agent=agent_id,
        providers=providers,
        enabled_channels=["console"],
        enabled_plugins=[],
        storage=StorageConfig(path=str(resolved_root / "state" / "openminion.db")),
        runtime=RuntimeConfig(
            reactions_enabled=False,
            telemetry_enabled=False,
            chat_turn_timeout_seconds=effective_timeout,
            memory_root_path=str(resolved_root / "memory"),
            tool_workspace_root=str(resolved_root / "workspace"),
        ),
        action_policy=ActionPolicyConfig(
            mode="auto",
            default_action="require_confirm",
            allow_read_only_without_prompt=True,
        ),
    )


def create_isolated_runtime(
    root_dir: Path,
    *,
    provider: ProviderPreset = "ollama",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str = "",
    session_id: int = 1,
    agent_id: str = "router-doctor",
    chat_turn_timeout_seconds: float | None = None,
) -> APIRuntime:
    """Create a fully isolated `APIRuntime` backed by `root_dir`."""
    resolved_root = Path(root_dir).expanduser().resolve()
    home_root = resolved_root / "home"
    data_root = resolved_root / "data"
    home_root.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)

    config = build_isolated_config(
        resolved_root,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        session_id=session_id,
        agent_id=agent_id,
        chat_turn_timeout_seconds=chat_turn_timeout_seconds,
    )
    return APIRuntime.from_config(
        config=config,
        home_root=home_root,
        data_root=data_root,
    )


def build_audit_instructions(
    *,
    max_p95_ms: float = 500.0,
    min_poi_agreement: float = 0.85,
    min_success_rate: float = 0.95,
) -> str:
    """Build concise, explicit system instructions with a compact `RouterAuditReport` JSON template.

    OpenMinion 0.1.24's `Agent(output_type=...)` validates replies post-hoc without injecting
    the Pydantic schema into the system prompt, so we provide a compact schema template that
    even small local models (1.5B-3B) follow reliably.
    """
    return (
        "You are Cortensor Router Doctor, an SRE and Proof-of-Inference (PoI) consensus auditor.\n"
        "Execute these steps in order using ONLY the provided tools:\n"
        "1. Call `probe_cortensor_router` on the target endpoint URL.\n"
        "2. Call `evaluate_sla_policy` with the exact JSON from step 1 "
        f"(max_p95_ms={max_p95_ms}, min_poi_agreement={min_poi_agreement}, "
        f"min_success_rate={min_success_rate}).\n"
        "3. ONLY if `evaluate_sla_policy` returns recommended_action='QUARANTINE', call "
        "`apply_router_quarantine` with the given `quarantine_file`, severity "
        "('CRITICAL' for CRITICAL_DRIFT, 'HIGH' for DEGRADED), and reason.\n"
        "4. Reply with ONLY one raw RouterAuditReport JSON object (no markdown fences) matching:\n"
        '{"endpoint_url":"...","verdict":"HEALTHY|DEGRADED|CRITICAL_DRIFT",'
        '"summary":"...","recommended_action":"NONE|MONITOR|QUARANTINE",'
        '"measured_p95_ms":0.0,"measured_poi_agreement":1.0,"measured_success_rate":1.0,'
        '"quarantine_applied":false,"quarantine_file":null,"violations":[]}'
    )


def build_audit_agent(
    runtime: APIRuntime,
    *,
    agent_id: str = "router-doctor",
    name: str = "router-doctor",
    model: str | None = None,
    max_p95_ms: float = 500.0,
    min_poi_agreement: float = 0.85,
    min_success_rate: float = 0.95,
    handoffs: list[Handoff] | None = None,
) -> Agent[str, RouterAuditReport]:
    """Construct the declarative `Agent` with explicit 3-tool allowlisting.

    Passing `tools=[probe_cortensor_router, evaluate_sla_policy, apply_router_quarantine]`
    populates `allowed_tools` and suppresses ~179 unrelated built-in OpenMinion tools.
    """
    return Agent[str, RouterAuditReport](
        name=name,
        agent_id=agent_id,
        runtime=runtime,
        model=model,
        instructions=build_audit_instructions(
            max_p95_ms=max_p95_ms,
            min_poi_agreement=min_poi_agreement,
            min_success_rate=min_success_rate,
        ),
        output_type=RouterAuditReport,
        tools=[
            probe_cortensor_router,
            evaluate_sla_policy,
            apply_router_quarantine,
        ],
        handoffs=handoffs,
    )


def build_forensics_handoff(
    parent: Agent[Any, Any],
    *,
    timeout_seconds: int = 60,
    model: str | None = None,
) -> tuple[Agent[Any, Any], Handoff]:
    """Construct a bounded child forensics subagent and `Handoff` transfer tool.

    Workaround for OpenMinion 0.1.24 Bug #7:
    Passes tool NAME strings (`"probe_cortensor_router"`, `"evaluate_sla_policy"`) rather than
    the `@tool`-decorated callables so the child does not collide with the parent's active
    temporary registration in the shared `ToolRegistry`.
    """
    child = subagent(
        parent,
        name="poi-forensics",
        model=model,
        instructions=(
            "Perform read-only Proof-of-Inference (PoI) consensus drift forensics "
            "on a suspect Cortensor Router endpoint and summarize root causes."
        ),
        tools=["probe_cortensor_router", "evaluate_sla_policy"],
        timeout_seconds=timeout_seconds,
    )
    handoff = Handoff(
        target=child,
        name="transfer_to_poi_forensics",
        description=(
            "Delegate read-only Proof-of-Inference drift forensics to the "
            "isolated poi-forensics subagent."
        ),
    )
    return child, handoff


def _serialize_delta_event(event: object) -> dict[str, Any]:
    if isinstance(event, dict):
        return dict(event)
    payload: dict[str, Any] = {"type": type(event).__name__}
    for attr in ("phase", "stage", "status", "message", "tool_name", "kind", "data"):
        if hasattr(event, attr):
            val = getattr(event, attr)
            if val is not None:
                payload[attr] = val if isinstance(val, (str, int, float, bool, dict, list)) else str(val)
    if len(payload) == 1:
        payload["repr"] = repr(event)
    return payload


def run_audit(
    runtime: APIRuntime,
    *,
    endpoint_url: str,
    quarantine_file: str | Path,
    prompt: str = "Compute deterministic PoI test vector alpha-01.",
    rounds: int = 3,
    session_id: int = 1,
    max_p95_ms: float = 500.0,
    min_poi_agreement: float = 0.85,
    min_success_rate: float = 0.95,
    approval_callback: ApprovalCallback | None = None,
    on_delta: Callable[[object], None] | None = None,
    timeout_seconds: float = 180.0,
    expected_evaluation: SLAPolicyEvaluation | None = None,
    expected_quarantine: QuarantineAction | None = None,
) -> AuditExecutionResult:
    """Execute an end-to-end Cortensor Router audit via `Agent.run_stream(...)`."""
    agent = build_audit_agent(
        runtime,
        max_p95_ms=max_p95_ms,
        min_poi_agreement=min_poi_agreement,
        min_success_rate=min_success_rate,
    )
    agent.forced_tools = ["probe_cortensor_router"]
    deltas: list[dict[str, Any]] = []
    approval_events: list[dict[str, Any]] = []

    def _capture_delta(event: object) -> None:
        deltas.append(_serialize_delta_event(event))
        if on_delta is not None:
            on_delta(event)

    def _wrapped_approval(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
        decision = (
            bool(approval_callback(tool_name, args, approval_id))
            if approval_callback is not None
            else False
        )
        approval_events.append(
            {
                "approval_id": approval_id,
                "tool_name": tool_name,
                "args": dict(args),
                "approved": decision,
            }
        )
        return decision

    task_prompt = (
        f"Run `probe_cortensor_router` with endpoint_url={endpoint_url!r}, "
        f"prompt={prompt!r}, rounds={rounds}, session_id={session_id}. "
        f"Then run `evaluate_sla_policy` on the returned JSON with "
        f"max_p95_ms={max_p95_ms}, min_poi_agreement={min_poi_agreement}, "
        f"min_success_rate={min_success_rate}. "
        f"If `recommended_action` is `QUARANTINE`, call `apply_router_quarantine` "
        f"with endpoint_url={endpoint_url!r}, quarantine_file={str(Path(quarantine_file).expanduser().resolve())!r}. "
        "Finally reply with ONLY the `RouterAuditReport` JSON object."
    )

    ledger = start_evidence_ledger()
    run_result: AgentRunResult[RouterAuditReport] | None = None
    reconciled = False
    raw_reply = ""
    try:
        try:
            run_result = agent.run_stream(
                task_prompt,
                on_delta=_capture_delta,
                approval_callback=_wrapped_approval,
                timeout_seconds=timeout_seconds,
            )
            report = run_result.output
            raw_reply = run_result.text
        except AgentOutputValidationError as exc:
            raw_reply = exc.raw_text or str(exc)
            if not ledger.probes:
                raise
            # Deterministic reconciliation from genuine OpenMinion @tool executions:
            # prevents small local models (1.5B-3B) from failing certification on JSON prose
            # wrapping while guaranteeing every metric comes directly from tool telemetry.
            probe = ledger.probes[-1]
            if ledger.evaluations:
                ev = ledger.evaluations[-1]
            else:
                ev = SLAPolicyEvaluation.model_validate_json(
                    evaluate_sla_policy(
                        probe.model_dump_json(),
                        max_p95_ms=max_p95_ms,
                        min_poi_agreement=min_poi_agreement,
                        min_success_rate=min_success_rate,
                    )
                )
            quarantine_rec = ledger.quarantines[-1] if ledger.quarantines else None
            narrative = (raw_reply.strip()[:240] if raw_reply else "").replace("\n", " ")
            summary = (
                f"Deterministic tool-ledger verdict ({ev.grade}, action={ev.recommended_action}) "
                f"over {probe.rounds} PoI rounds on {probe.endpoint_url}. "
                f"Model note: {narrative or 'completed tool execution'}."
            )
            report = RouterAuditReport(
                endpoint_url=probe.endpoint_url,
                verdict=ev.grade,
                summary=summary,
                recommended_action=ev.recommended_action,
                measured_p95_ms=probe.p95_latency_ms,
                measured_poi_agreement=probe.poi_analysis.poi_agreement_score,
                measured_success_rate=probe.success_rate,
                quarantine_applied=bool(quarantine_rec and quarantine_rec.applied),
                quarantine_file=quarantine_rec.quarantine_file if quarantine_rec else None,
                violations=list(ev.violations),
            )
            reconciled = True
        except (ProviderError, TurnTimeoutError):
            raise
    finally:
        stop_evidence_ledger()

    verified = False
    if expected_evaluation is not None:
        verify_report_against_evidence(
            report,
            expected_evaluation,
            quarantine=expected_quarantine,
        )
        verified = True

    return AuditExecutionResult(
        run_result=run_result,
        report=report,
        deltas=deltas,
        approval_events=approval_events,
        verified_against_evidence=verified,
        tool_trace=list(ledger.tool_trace),
        reconciled_from_tool_ledger=reconciled,
        raw_model_reply=raw_reply,
    )


def run_audit_via_submit_turn(
    runtime: APIRuntime,
    *,
    message: str,
    agent_id: str = "router-doctor",
    session_id: str = "submit-turn-audit",
    allowed_tools: list[str] | None = None,
    approval_decider: Callable[[dict[str, Any]], Literal["allow_once", "deny"]] | None = None,
    timeout_seconds: float = 30.0,
) -> SubmitTurnAuditResult:
    """Run a turn via `APIRuntime.submit_turn` + `RuntimeTurnHandle.stream()` + `resolve_approval()`.

    Note on OpenMinion 0.1.24 Bug #2:
    `TurnHandle.stream(timeout_s=...)` loops indefinitely when `Condition.wait()` times out.
    We consume the stream in a daemon watcher thread bounded by `handle.result(timeout_s=...)`
    and resolve any incoming approval chunks interactively via `handle.resolve_approval(...)`.
    """
    payload: dict[str, object] = {
        "agent_id": agent_id,
        "session_id": session_id,
        "message": message,
        "deliver": False,
        "timeout_seconds": float(timeout_seconds),
    }
    if allowed_tools is not None:
        payload["allowed_tools"] = list(allowed_tools)

    handle = runtime.submit_turn(payload=payload)
    chunks: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    stream_done = threading.Event()

    def _consume_stream() -> None:
        try:
            for chunk in handle.stream():
                if not isinstance(chunk, TurnChunk):
                    continue
                chunk_record = {
                    "sequence": chunk.sequence,
                    "kind": chunk.kind,
                    "data": dict(chunk.data) if isinstance(chunk.data, dict) else chunk.data,
                }
                chunks.append(chunk_record)
                if (
                    chunk.kind == "approval"
                    and isinstance(chunk.data, dict)
                    and chunk.data.get("phase") == "requested"
                ):
                    approval_id = str(chunk.data.get("approval_id") or "")
                    decision: Literal["allow_once", "deny"] = (
                        approval_decider(dict(chunk.data))
                        if approval_decider is not None
                        else "deny"
                    )
                    resolved = handle.resolve_approval(
                        approval_id=approval_id,
                        decision=decision,
                    )
                    resolutions.append(
                        {
                            "approval_id": approval_id,
                            "tool_name": chunk.data.get("tool_name"),
                            "decision": decision,
                            "resolved": resolved,
                        }
                    )
        finally:
            stream_done.set()

    watcher = threading.Thread(
        target=_consume_stream,
        name=f"submit-turn-stream-{handle.trace_id[:8]}",
        daemon=True,
    )
    watcher.start()

    try:
        response = handle.result(timeout_s=timeout_seconds)
    except TimeoutError as exc:
        handle.cancel()
        raise TurnTimeoutError(
            f"submit_turn timed out after {timeout_seconds}s (trace_id={handle.trace_id})"
        ) from exc

    # Allow the stream consumer brief time to drain final chunks after result is ready.
    deadline = time.monotonic() + 1.0
    while not stream_done.is_set() and time.monotonic() < deadline:
        stream_done.wait(timeout=0.05)

    return SubmitTurnAuditResult(
        trace_id=handle.trace_id,
        response=response,
        chunks=chunks,
        approval_resolutions=resolutions,
    )
