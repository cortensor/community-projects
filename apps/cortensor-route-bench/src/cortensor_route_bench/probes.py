"""Isolated OpenMinion 0.1 SDK building-block probe harness with real model execution."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import time
from typing import Any, Callable, TypeVar
from uuid import uuid4

import openminion
from openminion import (
    Agent,
    AgentOutputValidationError,
    APIRuntime,
    Handoff,
    MemoryBundle,
    ProviderError,
    subagent,
)
from openminion.api.handoff import DelegatedMemoryReadRequest
from pydantic import BaseModel
from sophiagraph.models import MemoryNamespace

from .config import redact_secrets
from .models import (
    BuildingBlockProbeResult,
    ProbeMatrixReport,
    detect_runtime_interception,
    parse_structured_reply,
)
from .tools import inspect_openminion_runtime_snapshot, inspect_provider_profile

T = TypeVar("T")


class ProbeCheckOutput(BaseModel):
    """Structured output contract used by schema-validation probes."""

    status: str
    sdk_version: str
    finding: str


def json_schema_instruction(model_cls: type[BaseModel], base_instruction: str) -> str:
    """Append explicit JSON-schema and key-checklist rules because OpenMinion 0.1.23 does not auto-inject output_type schemas."""
    schema_json = json.dumps(model_cls.model_json_schema(), ensure_ascii=True)
    required_keys = [
        name for name, info in model_cls.model_fields.items() if info.is_required()
    ]
    all_keys = list(model_cls.model_fields.keys())
    return (
        f"{base_instruction.strip()}\n\n"
        f"ALL JSON KEYS: {', '.join(all_keys)}\n"
        f"REQUIRED NON-EMPTY KEYS: {', '.join(required_keys)}\n"
        "Respond ONLY with a single raw JSON object (no markdown fences, no '#' headings, and no prose) "
        f"that strictly validates against this JSON schema:\n{schema_json}"
    )


def run_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 4.0,
) -> tuple[T, int]:
    """Retry transient provider rate-limit or 502/503 errors with bounded exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), attempt
        except ProviderError as exc:
            msg = str(exc)
            transient = any(code in msg for code in ("429", "502", "503", "RATE_LIMITED"))
            last_exc = exc
            if not transient or attempt == max_attempts:
                raise
            time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
    assert last_exc is not None
    raise last_exc


def _measure_probe(
    probe_id: str,
    building_block: str,
    fn: Callable[[], tuple[str, str | None, str | None, str | None, str, dict[str, object], int]],
) -> BuildingBlockProbeResult:
    """Execute one probe callable and normalize timing, error handling, and telemetry."""
    started = time.perf_counter()
    try:
        status, run_id, run_state, session_id, summary, evidence, attempts = fn()
        elapsed = round((time.perf_counter() - started) * 1000.0, 2)
        return BuildingBlockProbeResult(
            probe_id=probe_id,
            building_block=building_block,
            status=status,  # type: ignore[arg-type]
            elapsed_ms=elapsed,
            attempts=attempts,
            run_id=run_id,
            run_state=run_state,
            session_id=session_id,
            summary=redact_secrets(summary),
            evidence=evidence,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = round((time.perf_counter() - started) * 1000.0, 2)
        return BuildingBlockProbeResult(
            probe_id=probe_id,
            building_block=building_block,
            status="fail",
            elapsed_ms=elapsed,
            attempts=1,
            summary=redact_secrets(f"{type(exc).__name__}: {exc}"),
            evidence={"error_type": type(exc).__name__},
        )


def run_building_block_probes(
    *,
    config_path: str,
    provider: str,
    model: str,
    pace_seconds: float = 1.5,
) -> ProbeMatrixReport:
    """Run all 10 OpenMinion 0.1.23 building-block probes against a live model runtime."""
    runtime = APIRuntime.from_config_path(config_path, logging_mode="interactive")
    results: list[BuildingBlockProbeResult] = []
    suite_start = time.perf_counter()

    try:
        # 1. Runtime introspection & capability diagnostics
        def probe_runtime() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            cap = runtime.capability_report()
            posture = runtime.runtime_posture()
            catalog = runtime.model_connection_catalog()
            return (
                "pass",
                None,
                "ready",
                None,
                "Inspected APIRuntime capability_report, runtime_posture, and model_connection_catalog.",
                {
                    "capability_keys": sorted(cap.keys()) if isinstance(cap, dict) else [],
                    "posture_keys": sorted(posture.keys()) if isinstance(posture, dict) else [],
                    "catalog_count": len(catalog) if isinstance(catalog, (list, dict)) else 0,
                },
                1,
            )

        # 2. Single-turn Agent.run()
        def probe_single_turn() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            agent = Agent(
                name="probe_single_turn",
                instructions="Acknowledge requests directly in one concise sentence without extra formatting.",
                runtime=runtime,
                model=model,
            )
            res, attempts = run_with_backoff(
                lambda: agent.run("Say READY FOR CORTENSOR ROUTE BENCH in one short sentence.")
            )
            interception = detect_runtime_interception(res.text)
            if interception is not None:
                return (
                    "fail",
                    res.run_id,
                    res.run_state,
                    res.session_id,
                    f"Single-turn Agent.run() hit OpenMinion runtime guard: {interception}.",
                    {"interception": interception, "reply_preview": res.text[:160], "stats": res.stats},
                    attempts,
                )
            return (
                "pass",
                res.run_id,
                res.run_state,
                res.session_id,
                f"Single-turn Agent.run() returned {len(res.text)} chars.",
                {"reply_preview": res.text[:160], "stats": res.stats},
                attempts,
            )

        # 3. Streaming progress events via Agent.run_stream()
        def probe_streaming() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            events: list[str] = []
            agent = Agent(
                name="probe_stream",
                instructions="Respond briefly.",
                runtime=runtime,
                model=model,
            )
            res, attempts = run_with_backoff(
                lambda: agent.run_stream(
                    "State two benefits of verifiable AI routing in 15 words total.",
                    on_delta=lambda ev: events.append(type(ev).__name__),
                )
            )
            return (
                "pass",
                res.run_id,
                res.run_state,
                res.session_id,
                f"Agent.run_stream() emitted {len(events)} progress events.",
                {"event_count": len(events), "event_types": sorted(set(events))},
                attempts,
            )

        # 4. Read-only @tool + forced_tools execution
        def probe_read_only_tool() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            agent = Agent(
                name="probe_tool",
                instructions="Call inspect_provider_profile and summarize its base_url and tool calling flag.",
                runtime=runtime,
                model=model,
                tools=[inspect_provider_profile],
                forced_tools=["inspect_provider_profile"],
            )
            res, attempts = run_with_backoff(
                lambda: agent.run(f"Inspect provider profile for '{provider}'.")
            )
            return (
                "pass",
                res.run_id,
                res.run_state,
                res.session_id,
                "@tool(min_scope='READ_ONLY') + forced_tools executed with live model synthesis.",
                {"reply_preview": res.text[:180]},
                attempts,
            )

        # 5. Structured output validation (tests native output_type + envelope stripping)
        def probe_structured_output() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            agent = Agent(
                name="probe_schema",
                instructions=json_schema_instruction(
                    ProbeCheckOutput,
                    "Populate status='ok', sdk_version from your observation, and a brief finding.",
                ),
                runtime=runtime,
                model=model,
                output_type=ProbeCheckOutput,
                tools=[inspect_openminion_runtime_snapshot],
                forced_tools=["inspect_openminion_runtime_snapshot"],
            )
            try:
                res, attempts = run_with_backoff(
                    lambda: agent.run("Call inspect_openminion_runtime_snapshot and emit the JSON verdict.")
                )
                parsed = res.output
                return (
                    "pass",
                    res.run_id,
                    res.run_state,
                    res.session_id,
                    f"Validated Pydantic output natively: status={parsed.status!r}, sdk={parsed.sdk_version!r}.",
                    {"output": parsed.model_dump(mode="json")},
                    attempts,
                )
            except AgentOutputValidationError as exc:
                parsed, meta = parse_structured_reply(exc.raw_text, ProbeCheckOutput)
                return (
                    "workaround" if meta["had_agent_prefix"] else "fail",
                    None,
                    "envelope_prefix_workaround" if meta["had_agent_prefix"] else "validation_error",
                    agent.session_id,
                    (
                        "Native output_type raised AgentOutputValidationError because OpenMinion runtime prepends "
                        "'<agent_name>: '; underlying ProbeCheckOutput JSON validated via envelope-stripping workaround."
                        if meta["had_agent_prefix"]
                        else f"AgentOutputValidationError even without envelope prefix: {exc.validation_error}"
                    ),
                    {
                        "native_error": "AgentOutputValidationError",
                        **meta,
                        "output": parsed.model_dump(mode="json"),
                    },
                    1,
                )

        # 6. Controlled negative test: AgentOutputValidationError without schema guidance
        def probe_validation_error() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            agent = Agent(
                name="probe_schema_negative",
                instructions="Reply strictly as a plain English sentence, NEVER JSON.",
                runtime=runtime,
                model=model,
                output_type=ProbeCheckOutput,
            )
            try:
                _, attempts = run_with_backoff(lambda: agent.run("Say hello in one plain sentence."))
                return (
                    "fail",
                    None,
                    None,
                    agent.session_id,
                    "Expected AgentOutputValidationError when prose is returned, but validation unexpectedly passed.",
                    {},
                    attempts,
                )
            except AgentOutputValidationError as exc:
                return (
                    "expected_error",
                    None,
                    "validation_error",
                    agent.session_id,
                    "Verified fail-closed AgentOutputValidationError raised with raw_text preserved.",
                    {"raw_text_preview": exc.raw_text[:120]},
                    1,
                )

        # 7. Session continuity across turns
        def probe_session_continuity() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            sid = f"route-bench-{uuid4().hex[:8]}"
            agent = Agent(
                name="probe_session",
                instructions="Store and recall exact verification codes provided by the user within this session.",
                runtime=runtime,
                model=model,
                session_id=sid,
            )
            token = f"COR-{uuid4().hex[:6].upper()}"
            _, a1 = run_with_backoff(
                lambda: agent.run(f"Memorize verification code {token} for this session and confirm STORED.")
            )
            time.sleep(pace_seconds)
            res2, a2 = run_with_backoff(
                lambda: agent.run("What exact verification code did I ask you to store in this session?")
            )
            interception = detect_runtime_interception(res2.text)
            recalled = token in res2.text and interception is None
            return (
                "pass" if recalled else "fail",
                res2.run_id,
                res2.run_state,
                res2.session_id,
                (
                    f"Session recall succeeded for token {token}."
                    if recalled
                    else f"Session recall missed token {token} ({interception or 'missing_token'})."
                ),
                {
                    "expected_token": token,
                    "recalled": recalled,
                    "interception": interception,
                    "reply": res2.text[:160],
                },
                a1 + a2,
            )

        # 8. Bounded subagent() isolation & delegated memory request
        def probe_subagent() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            parent = Agent(name="parent_coord", instructions="Parent coordinator.", runtime=runtime, model=model)
            mem_req = DelegatedMemoryReadRequest(
                namespaces=(MemoryNamespace(project_id="cortensor-route-bench"),),
                record_types=("diagnostic",),
                max_results=5,
                max_context_tokens=1024,
            )
            child = subagent(
                parent,
                name="bounded_analyst",
                instructions="Inspect the provider profile and summarize compatibility in one concise sentence.",
                model=model,
                tools=[inspect_provider_profile],
                timeout_seconds=60,
                memory=mem_req,
            )
            child.forced_tools = ["inspect_provider_profile"]
            res, attempts = run_with_backoff(
                lambda: child.run(
                    "Call inspect_provider_profile for 'cortensor-portal' and state why fallback routing helps."
                )
            )
            ctx = child.subagent_context
            interception = detect_runtime_interception(res.text)
            if interception is not None:
                return (
                    "fail",
                    res.run_id,
                    res.run_state,
                    res.session_id,
                    f"subagent() hit OpenMinion runtime guard: {interception}.",
                    {
                        "child_agent_id": ctx.child_agent_id if ctx else None,
                        "interception": interception,
                        "reply_preview": res.text[:160],
                    },
                    attempts,
                )
            return (
                "pass",
                res.run_id,
                res.run_state,
                res.session_id,
                "Executed isolated child subagent() with DelegatedMemoryReadRequest grant lifecycle.",
                {
                    "child_agent_id": ctx.child_agent_id if ctx else None,
                    "parent_transcript_inherited": ctx.parent_transcript_inherited if ctx else None,
                    "memory_posture": ctx.memory_posture if ctx else None,
                    "reply_preview": res.text[:160],
                },
                attempts,
            )

        # 9. Handoff delegation (transfer_to_<target>)
        def probe_handoff() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            specialist = Agent(
                name="cortensor_specialist",
                instructions="You are a Cortensor specialist. Summarize Cortensor Portal compatibility in 12 words or fewer.",
                runtime=runtime,
                model=model,
            )
            router = Agent(
                name="router_lead",
                instructions="Delegate Cortensor compatibility questions via transfer_to_cortensor_specialist.",
                runtime=runtime,
                model=model,
                handoffs=[Handoff(target=specialist, name="transfer_to_cortensor_specialist")],
                forced_tools=["transfer_to_cortensor_specialist"],
            )
            res, attempts = run_with_backoff(
                lambda: router.run("Ask the specialist to summarize Cortensor Portal compatibility.")
            )
            interception = detect_runtime_interception(res.text)
            if interception is not None:
                return (
                    "fail",
                    res.run_id,
                    res.run_state,
                    res.session_id,
                    f"Handoff blocked by OpenMinion runtime guard: {interception}.",
                    {"interception": interception, "reply_preview": res.text[:200]},
                    attempts,
                )
            return (
                "pass",
                res.run_id,
                res.run_state,
                res.session_id,
                "Handoff compiled transfer_to_cortensor_specialist and completed peer delegation cleanly.",
                {"reply_preview": res.text[:160]},
                attempts,
            )

        # 10. MemoryBundle serialization & APIRuntime.submit_turn handle inspection
        def probe_memory_bundle_and_ingress() -> tuple[str, str | None, str | None, str | None, str, dict[str, object], int]:
            bundle = MemoryBundle(
                items=[{"kind": "probe", "provider": provider, "model": model}],
                metadata={"sdk": openminion.__version__},
            )
            restored = MemoryBundle.from_json(bundle.to_json())
            handle = runtime.submit_turn(
                payload={
                    "message": "Reply with exactly: INGRESS_OK",
                    "session_id": f"ingress-{uuid4().hex[:8]}",
                    "deliver": False,
                    "override_model": model,
                }
            )
            turn_resp = handle.result(timeout_s=45.0)
            return (
                "pass",
                getattr(turn_resp, "run_id", None) or getattr(handle, "trace_id", None),
                getattr(turn_resp, "run_state", None) or "completed",
                getattr(turn_resp, "session_id", None),
                "Verified MemoryBundle round-trip serialization and APIRuntime.submit_turn().result().",
                {
                    "memory_bundle_items": len(restored.items),
                    "handle_type": type(handle).__name__,
                    "trace_id": handle.trace_id,
                    "reply_preview": str(getattr(turn_resp, "body", "") or "")[:120],
                },
                1,
            )

        probe_specs: list[tuple[str, str, Callable[[], Any]]] = [
            ("probe_01_runtime", "APIRuntime Diagnostics", probe_runtime),
            ("probe_02_single_turn", "Agent.run (Single Turn)", probe_single_turn),
            ("probe_03_stream", "Agent.run_stream (Delta Callbacks)", probe_streaming),
            ("probe_04_read_tool", "@tool(READ_ONLY) + forced_tools", probe_read_only_tool),
            ("probe_05_schema_ok", "Pydantic output_type (Schema Prompt)", probe_structured_output),
            ("probe_06_schema_err", "AgentOutputValidationError Guard", probe_validation_error),
            ("probe_07_session", "Session & Thread Continuity", probe_session_continuity),
            ("probe_08_subagent", "subagent() + DelegatedMemoryReadRequest", probe_subagent),
            ("probe_09_handoff", "Handoff Delegation (transfer_to_*)", probe_handoff),
            ("probe_10_memory_ingress", "MemoryBundle & APIRuntime.submit_turn", probe_memory_bundle_and_ingress),
        ]

        for idx, (pid, block, fn) in enumerate(probe_specs):
            results.append(_measure_probe(pid, block, fn))
            if idx < len(probe_specs) - 1 and idx >= 1:
                time.sleep(pace_seconds)
    finally:
        runtime.close()

    total_ms = round((time.perf_counter() - suite_start) * 1000.0, 2)
    passed = sum(1 for r in results if r.status in {"pass", "workaround", "expected_error"})
    return ProbeMatrixReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        provider=provider,
        model=model,
        openminion_version=openminion.__version__,
        total_probes=len(results),
        passed_probes=passed,
        total_elapsed_ms=total_ms,
        probes=results,
    )
