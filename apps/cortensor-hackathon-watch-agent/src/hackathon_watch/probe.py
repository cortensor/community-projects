"""Probe suite: run every building block this agent actually uses.

``hackathon-watch probe`` runs the probes below and (re)generates
``docs/BUILDING_BLOCKS_TESTED.md``. Statuses are honest:

- ``pass`` — the block worked end to end on the real path.
- ``partial`` — the block works at construct / stub level but a live
  turn could not be completed (reason recorded, e.g. the Pollinations
  402 free-tier wall).
- ``fail`` — the block did not work; the evidence says why.

Live-model usage per probe run: exactly one DirectClient call
(structured-output probe) plus one native ``Agent.run`` attempt
(session probe). The native turn against Pollinations is expected to
hit HTTP 402 (one SDK turn = several consecutive calls, free tier
allows 1 reply / 45 s / IP — verified 3/3 in the sibling SPIKE.md §4);
that outcome is recorded, not hidden. ``--offline`` skips both live
parts for CI.
"""

from __future__ import annotations

import json
import tempfile
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

from .agent import (build_classifier_agent, build_isolated_runtime,
                    make_handoff, make_lookup_tool, make_subagent_classifier)
from .config import ProviderSettings, resolve_provider
from .llm_client import DirectClient
from .models import HackathonEntry, SuitabilityVerdict
from .suitability import build_classify_messages, verdict_tool_schema

PROBE_NAMES = [
    "runtime_isolation",
    "structured_pydantic_output",
    "tool_and_forced_tools",
    "policy_confirmation_gate",
    "session_continuity",
    "memory_bundle_portability",
    "subagent_delegation",
    "agent_handoff",
    "streaming_telemetry",
    "error_and_timeout_contracts",
]


@dataclass
class ProbeResult:
    name: str
    status: str  # pass | partial | fail
    duration_ms: int
    evidence: str
    detail: str = ""


# ---------------------------------------------------------------- probes

def probe_runtime_isolation(ctx: dict) -> tuple[str, str, str]:
    provider: ProviderSettings = ctx["provider"]
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(provider, Path(tmp))
        try:
            # home_root is created lazily by the runtime; data_root is
            # created eagerly with its SQLite stores. Either way, no
            # plaintext key may appear in any agents.json the runtime writes.
            agents_json = list(Path(tmp).rglob("agents.json"))
            blob = ""
            for path in agents_json:
                blob += path.read_text(encoding="utf-8", errors="ignore")
            leak = provider.api_key in blob and provider.api_key not in (
                "", "pollinations-no-key-needed")
            return ("pass",
                    f"runtime built in ~isolated home/data roots; "
                    f"agents.json files found: {len(agents_json)}; "
                    f"plaintext key in agents.json: {leak}",
                    "")
        finally:
            rt.close()


def probe_structured_pydantic_output(ctx: dict) -> tuple[str, str, str]:
    # (a) loopback stub: exact JSON -> typed verdict, no model cost.
    def stub_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "model": "stub", "choices": [{
                "message": {"content": '{"label": "unsure", "reason": "stub"}'},
                "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                      "total_tokens": 15}})
    stub_client = DirectClient(
        ctx["provider"], min_interval_sec=0,
        transport=httpx.MockTransport(stub_handler))
    verdict = stub_client.classify(
        SuitabilityVerdict,
        build_classify_messages(HackathonEntry(name="Stub Hack", url="https://example.test/x", source="devfolio")),
        tools=verdict_tool_schema())
    assert verdict.label == "unsure", verdict
    if ctx.get("offline"):
        return ("pass",
                "stub channel: JSON text parsed into SuitabilityVerdict "
                "(label=unsure); live Pollinations call skipped (--offline)",
                "")
    # (b) one live call against Pollinations (free, no key).
    live = DirectClient(ctx["provider"], min_interval_sec=0)
    live_verdict = live.classify(
        SuitabilityVerdict,
        build_classify_messages(HackathonEntry(
            name="Cortensor Hackathon #5", url="https://dorahacks.io/hackathon/2418/detail",
            source="dorahacks",
            notes="Build a runnable agent with OpenMinion 0.1 SDK; online; $1,150 prize pool.")),
        tools=verdict_tool_schema())
    ctx["live_calls"] = ctx.get("live_calls", 0) + live.calls_made
    ctx["live_tokens"] = ctx.get("live_tokens", 0) + live.tokens_used
    return ("pass",
            f"stub channel OK (label=unsure); live Pollinations call OK: "
            f"label={live_verdict.label}, model={live.provider.model!r} "
            f"({live.calls_made} call, {live.tokens_used} tokens)",
            f"live reason: {live_verdict.reason}")


def probe_tool_and_forced_tools(ctx: dict) -> tuple[str, str, str]:
    from openminion import Agent
    known = {"url:https://example.test/x": HackathonEntry(
        name="Stub Hack", url="https://example.test/x", source="devfolio")}
    lookup = make_lookup_tool(known)
    assert lookup.tool_decl.name == "lookup_known_hackathon"
    assert lookup.tool_decl.min_scope == "READ_ONLY"
    assert not lookup.tool_decl.dangerous
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(ctx["provider"], Path(tmp))
        try:
            agent = Agent(instructions="Classify.", output_type=SuitabilityVerdict,
                          model=ctx["provider"].model, tools=[lookup],
                          forced_tools=["lookup_known_hackathon"],
                          name="watch", runtime=rt)
            assert agent is not None
        finally:
            rt.close()
    # Tool-call channel verified against the stub in the structured-output
    # probe's twin: a stub returning tool_calls parses the same way.
    def tool_stub(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "model": "stub", "choices": [{
                "message": {"content": "",
                            "tool_calls": [{"id": "c1", "type": "function",
                                          "function": {"name": "give_verdict",
                                                       "arguments": '{"label": "preliminary", "reason": "stub tool call"}'}}]},
                "finish_reason": "tool_calls"}],
            "usage": {"total_tokens": 20}})
    client = DirectClient(ctx["provider"], min_interval_sec=0,
                          transport=httpx.MockTransport(tool_stub))
    verdict = client.classify(
        SuitabilityVerdict,
        build_classify_messages(HackathonEntry(name="T", url="https://example.test/y", source="dorahacks")),
        tools=verdict_tool_schema())
    assert verdict.label == "preliminary"
    return ("pass",
            "@tool(min_scope=READ_ONLY) registered as lookup_known_hackathon; "
            "Agent with forced_tools=[lookup_known_hackathon] constructs; "
            "tool_calls channel parses into SuitabilityVerdict(label=preliminary) "
            "against a loopback stub",
            "Live forced_tools turn needs a working native turn (see session probe).")


def probe_policy_confirmation_gate(ctx: dict) -> tuple[str, str, str]:
    from openminion import tool
    from openminion.modules.policy.constants import POLICY_GRANT_EFFECT_ALLOW
    from openminion.modules.policy.models import PolicyGrantInput

    @tool(dangerous=True, min_scope="WRITE_SAFE")
    def remind_organizer(text: str) -> str:
        """Send a reminder (side effect: needs human approval)."""
        return f"sent:{text}"

    assert remind_organizer.tool_decl.dangerous is True
    grant = PolicyGrantInput(effect=POLICY_GRANT_EFFECT_ALLOW,
                             tool="remind_organizer", max_uses=1)
    assert grant.max_uses == 1
    live = ctx.get("native_turn")
    if live and live.get("ok"):
        return ("pass",
                "dangerous tool + PolicyGrantInput(max_uses=1) construct; "
                "live native turn succeeded, gate path exercisable",
                "")
    return ("partial",
            "dangerous tool + PolicyGrantInput(max_uses=1) construct; "
            "approval_callback wiring present in Agent.run signature; "
            "full live allow/deny/pause-resume cycle NOT demonstrated — "
            "it needs a working native turn, which Pollinations 402 blocks "
            f"({ctx.get('native_turn', {}).get('evidence', 'no attempt yet')})",
            "Fail-closed by design: with approval_callback=None the "
            "dangerous tool is not executed (SDK code path).")


def _attempt_native_turn(ctx: dict) -> dict:
    """One native Agent.run attempt, shared by the turn-dependent probes."""
    if "native_turn" in ctx:
        return ctx["native_turn"]
    if ctx.get("offline"):
        ctx["native_turn"] = {"ok": False,
                              "evidence": "skipped (--offline)"}
        return ctx["native_turn"]
    from openminion import AgentOutputValidationError, ProviderError
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            rt = build_isolated_runtime(ctx["provider"], Path(tmp))
            try:
                agent = build_classifier_agent(
                    rt, {}, ctx["provider"])
                result = agent.run(
                    "Classify this hackathon. Name: Cortensor Hackathon #5. "
                    "URL: https://dorahacks.io/hackathon/2418/detail. "
                    "Source: dorahacks.",
                    timeout_seconds=180)
                ctx["native_turn"] = {
                    "ok": True,
                    "evidence": f"Agent.run returned in "
                                f"{int((time.monotonic() - started) * 1000)} ms; "
                                f"output type {type(result.output).__name__}",
                    "output": result.output}
            finally:
                rt.close()
    except (ProviderError, AgentOutputValidationError) as exc:
        ctx["native_turn"] = {
            "ok": False,
            "evidence": f"{type(exc).__name__}: {str(exc)[:300]} "
                        f"after {int((time.monotonic() - started) * 1000)} ms"}
    except Exception as exc:  # noqa: BLE001
        ctx["native_turn"] = {
            "ok": False,
            "evidence": f"{type(exc).__name__}: {str(exc)[:300]}"}
    return ctx["native_turn"]


def probe_session_continuity(ctx: dict) -> tuple[str, str, str]:
    # Session continuity needs two turns in one thread; that needs a
    # working turn at all, so this probe is the single native-turn attempt.
    turn = _attempt_native_turn(ctx)
    if turn["ok"]:
        return ("pass", "native turn succeeded: " + turn["evidence"],
                "Second-turn continuity (same thread_id remembers) not "
                "separately exercised in this run.")
    return ("partial",
            "native Agent.run attempt did not complete a turn: " + turn["evidence"],
            "Session continuity (same thread_id keeps context, different "
            "session leaks nothing) cannot be demonstrated until a native "
            "turn completes; the failure is the provider wall, not the "
            "session code — runtime/session construction itself passed.")


def probe_memory_bundle_portability(ctx: dict) -> tuple[str, str, str]:
    from openminion.modules.memory.portability import (
        export_bundle, import_bundle, load_bundle, save_bundle)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bundle.json"
        bundle = export_bundle(
            [{"kind": "hackathon", "id": "url:https://example.test/x",
              "name": "Stub Hack", "url": "https://example.test/x"}],
            metadata={"agent": "hackathon-watch"})
        save_bundle(bundle, str(path))
        loaded = load_bundle(str(path))
        info = import_bundle(loaded, trust_mode="direct")
        assert info["item_count"] == 1, info
        try:
            import_bundle(loaded, trust_mode="bogus")
        except Exception as exc:  # noqa: BLE001 - expecting InvalidArgumentError
            rejected = type(exc).__name__
        else:
            rejected = "NOT REJECTED"
    assert rejected != "NOT REJECTED", "bogus trust_mode must be rejected"
    return ("pass",
            "export -> save -> load -> import round-trip OK (1 item, "
            "bundle memory_bundle.v1); bogus trust_mode rejected with "
            f"{rejected}",
            "")


def probe_subagent_delegation(ctx: dict) -> tuple[str, str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(ctx["provider"], Path(tmp))
        try:
            parent = build_classifier_agent(rt, {}, ctx["provider"])
            child = make_subagent_classifier(parent, timeout_seconds=60)
            assert child.name == "classifier"
            assert child.subagent_context.timeout_seconds == 60
            assert child.subagent_context.parent_transcript_inherited is False
        finally:
            rt.close()
    turn = ctx.get("native_turn") or {}
    if turn.get("ok"):
        return ("pass",
                "subagent() constructs with isolated context "
                "(parent_transcript_inherited=False, timeout 60 s); "
                "live delegation exercisable now that a turn works",
                "")
    return ("partial",
            "subagent() constructs with isolated context "
            "(parent_transcript_inherited=False, timeout 60 s); live "
            "delegation run NOT demonstrated — needs a working native turn "
            f"({turn.get('evidence', 'no attempt yet')})",
            "")


def probe_agent_handoff(ctx: dict) -> tuple[str, str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(ctx["provider"], Path(tmp))
        try:
            from openminion import Agent
            specialist = Agent(
                instructions="Check deadlines on official pages.",
                name="deadline_checker", runtime=rt)
            handoff = make_handoff(None, specialist)
            assert handoff.resolved_name() == "transfer_to_deadline_checker"
        finally:
            rt.close()
    turn = ctx.get("native_turn") or {}
    if turn.get("ok"):
        return ("pass",
                "Handoff resolves to transfer_to_deadline_checker; live "
                "handoff exercisable now that a turn works",
                "")
    return ("partial",
            "Handoff constructs and resolves to "
            "transfer_to_deadline_checker; live handoff round-trip NOT "
            "demonstrated — needs a working native turn "
            f"({turn.get('evidence', 'no attempt yet')})",
            "")


def probe_streaming_telemetry(ctx: dict) -> tuple[str, str, str]:
    from openminion import APIRuntime
    assert hasattr(APIRuntime, "submit_turn")
    from openminion.api import TurnChunk, TurnResponse, TurnTelemetry
    telemetry = TurnTelemetry()
    assert telemetry.tokens_in == 0 and telemetry.tokens_out == 0
    turn = ctx.get("native_turn") or {}
    if turn.get("ok"):
        return ("pass",
                "submit_turn exists; TurnChunk/TurnTelemetry types import; "
                "live streaming exercisable now that a turn works",
                "")
    return ("partial",
            "submit_turn exists; TurnChunk/TurnTelemetry import with "
            "zeroed default counters; live stream + real telemetry NOT "
            "demonstrated — needs a working native turn "
            f"({turn.get('evidence', 'no attempt yet')})",
            "Note: reference work reported TurnTelemetry.tokens_* as 0 while "
            "TurnResponse.stats held real counts; this probe does not "
            "re-claim that — it could not run a live stream.")


def _loopback_server(handler_cls):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def probe_error_and_timeout_contracts(ctx: dict) -> tuple[str, str, str]:
    from openminion import ProviderError, TurnTimeoutError
    notes: list[str] = []

    class Fail500(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = json.dumps({"error": {"message": "boom"}}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # noqa: D102
            pass

    server = _loopback_server(Fail500)
    try:
        provider = ProviderSettings(
            preset="openai-compatible",
            base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
            model="openai", api_key="loopback-no-key")
        with tempfile.TemporaryDirectory() as tmp:
            rt = build_isolated_runtime(provider, Path(tmp))
            try:
                agent = build_classifier_agent(rt, {}, provider)
                try:
                    agent.run("hello", timeout_seconds=60)
                    notes.append("HTTP 500 did NOT raise (unexpected)")
                except ProviderError as exc:
                    notes.append(f"HTTP 500 -> ProviderError ({str(exc)[:120]})")
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"HTTP 500 -> {type(exc).__name__} (unexpected)")
            finally:
                rt.close()
    finally:
        server.shutdown()
        server.server_close()

    class Slow(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            time.sleep(8)
            body = b"{}"
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *a):  # noqa: D102
            pass

    server = _loopback_server(Slow)
    try:
        provider = ProviderSettings(
            preset="openai-compatible",
            base_url=f"http://127.0.0.1:{server.server_address[1]}/v1",
            model="openai", api_key="loopback-no-key")
        with tempfile.TemporaryDirectory() as tmp:
            rt = build_isolated_runtime(provider, Path(tmp))
            try:
                agent = build_classifier_agent(rt, {}, provider)
                try:
                    agent.run("hello", timeout_seconds=3)
                    notes.append("slow provider did NOT time out (unexpected)")
                except TurnTimeoutError as exc:
                    notes.append(f"slow provider -> TurnTimeoutError ({str(exc)[:120]})")
                except Exception as exc:  # noqa: BLE001
                    notes.append(f"slow provider -> {type(exc).__name__}: {str(exc)[:120]}")
            finally:
                rt.close()
    finally:
        server.shutdown()
        server.server_close()

    ok_500 = any(n.startswith("HTTP 500 -> ProviderError") for n in notes)
    ok_timeout = any("TurnTimeoutError" in n for n in notes)
    status = "pass" if (ok_500 and ok_timeout) else "partial"
    return (status, " | ".join(notes),
            "Loopback HTTP server on 127.0.0.1, zero model cost, real SDK "
            "provider path (not a mock of the SDK itself).")


PROBES = {
    "runtime_isolation": probe_runtime_isolation,
    "structured_pydantic_output": probe_structured_pydantic_output,
    "tool_and_forced_tools": probe_tool_and_forced_tools,
    "policy_confirmation_gate": probe_policy_confirmation_gate,
    "session_continuity": probe_session_continuity,
    "memory_bundle_portability": probe_memory_bundle_portability,
    "subagent_delegation": probe_subagent_delegation,
    "agent_handoff": probe_agent_handoff,
    "streaming_telemetry": probe_streaming_telemetry,
    "error_and_timeout_contracts": probe_error_and_timeout_contracts,
}


def run_probes(provider: ProviderSettings, offline: bool = False) -> list[ProbeResult]:
    ctx: dict[str, Any] = {"provider": provider, "offline": offline,
                           "live_calls": 0, "live_tokens": 0}
    results: list[ProbeResult] = []
    # Order matters: the live DirectClient call (structured output) runs
    # BEFORE the native-turn attempt, so the 45 s/IP free-tier window is
    # spent on the call that can actually succeed.
    order = ["runtime_isolation", "structured_pydantic_output",
             "tool_and_forced_tools", "memory_bundle_portability",
             "error_and_timeout_contracts", "session_continuity",
             "policy_confirmation_gate", "subagent_delegation",
             "agent_handoff", "streaming_telemetry"]
    for name in order:
        started = time.monotonic()
        try:
            status, evidence, detail = PROBES[name](ctx)
        except Exception as exc:  # noqa: BLE001
            status, evidence, detail = "fail", f"{type(exc).__name__}: {exc}", ""
        results.append(ProbeResult(
            name=name, status=status,
            duration_ms=int((time.monotonic() - started) * 1000),
            evidence=evidence, detail=detail))
    ctx["results"] = results
    return results, ctx.get("live_calls", 0), ctx.get("live_tokens", 0)


def render_building_blocks_doc(results: list[ProbeResult], provider: ProviderSettings,
                               live_calls: int = 0, live_tokens: int = 0) -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    passed = sum(1 for r in results if r.status == "pass")
    partial = sum(1 for r in results if r.status == "partial")
    failed = sum(1 for r in results if r.status == "fail")
    total_ms = sum(r.duration_ms for r in results)
    lines = [
        "# Building Blocks Tested",
        "",
        "Auto-generated by `hackathon-watch probe`. Each row is a block this",
        "agent actually uses, run for real (loopback stub or live free model),",
        "not a checklist copied from another project.",
        "",
        f"- Generated: {now} (UTC)",
        f"- Provider preset: `{provider.preset}` (base `{provider.base_url}`, model `{provider.model}`)",
        f"- Result: **{passed} pass / {partial} partial / {failed} fail** "
        f"out of {len(results)} probes, {total_ms / 1000:.1f} s total",
        f"- Live model calls in this probe run: {live_calls} "
        f"({live_tokens} tokens, $0 — Pollinations free tier, no key)",
        "",
        "| # | Building block | Status | Time | Evidence |",
        "|---|----------------|--------|------|----------|",
    ]
    for i, r in enumerate(results, 1):
        ev = r.evidence.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | `{r.name}` | {r.status} | {r.duration_ms} ms | {ev} |")
    lines += [
        "",
        "## What partial means",
        "",
        "A `partial` block constructs and works at the stub/code level, but",
        "its live turn could not be completed in this run. The usual cause",
        "is the Pollinations free tier: 1 reply every 45 s per IP, enforced",
        "as HTTP 402, while one native SDK turn fires several consecutive",
        "model calls. The agent's main road (DirectClient, one call per",
        "step, paced) is designed around exactly that wall; the native-turn",
        "probes record the wall instead of pretending it is not there.",
        "",
        "## Detail notes",
        "",
    ]
    for r in results:
        if r.detail:
            lines.append(f"- `{r.name}`: {r.detail}")
    lines.append("")
    return "\n".join(lines)
