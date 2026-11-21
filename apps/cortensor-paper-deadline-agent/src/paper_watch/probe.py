"""Probe harness: exercise only the building blocks this agent really uses.

Probes (each writes evidence into the generated doc):
1.  runtime_isolation            — isolated runtime, no key material on disk
2.  structured_output            — Agent reply parsed to a Pydantic model
3.  tool_and_forced_tools        — @tool lookup + forced_tools dispatch
4.  session_continuity           — same thread remembers a marker; a fresh
                                   session does not leak it
5.  memory_bundle_portability    — MemoryBundle export/import round-trip
6.  subagent_delegation          — subagent() runs in an isolated context
7.  agent_handoff                — Handoff to a second agent completes a turn
8.  submit_turn_streaming_telemetry — run_stream yields chunks + stats
9.  error_and_timeout_contracts  — unreachable provider -> ProviderError
10. verification_honesty         — deterministic: no rendered date lacks its
                                   verification status; unverified dates are
                                   never labelled verified

Run with ``paper-watch probe``. ``--skip-model`` runs only the probes
that need no model (1, 5, 9, 10). ``--export-docs`` writes
``docs/BUILDING_BLOCKS_TESTED.md``. Model probes are paced for the free
tier (see config.pace_model_call).
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .agent import (
    build_runtime,
    extract_json_object,
    run_agent_stream_with_retry,
    run_agent_with_retry,
)
from .brief import build_template_brief, check_honesty, render_brief
from .config import ProviderSettings, pace_model_call, resolve_preset
from .store import VenueStore

__all__ = ["PROBE_NAMES", "ProbeResult", "run_probes", "render_probes_doc"]

PROBE_NAMES = [
    "runtime_isolation",
    "structured_output",
    "tool_and_forced_tools",
    "session_continuity",
    "memory_bundle_portability",
    "subagent_delegation",
    "agent_handoff",
    "submit_turn_streaming_telemetry",
    "error_and_timeout_contracts",
    "verification_honesty",
]

MODEL_PROBES = {
    "structured_output",
    "tool_and_forced_tools",
    "session_continuity",
    "subagent_delegation",
    "agent_handoff",
    "submit_turn_streaming_telemetry",
}


@dataclass
class ProbeResult:
    name: str
    status: str  # pass | partial | fail
    duration_ms: int
    evidence: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "evidence": self.evidence,
            "detail": self.detail,
        }


def _timed(name: str, fn):
    started = time.monotonic()
    try:
        result = fn()
        if isinstance(result, ProbeResult):
            result.duration_ms = int((time.monotonic() - started) * 1000)
            return result
        raise RuntimeError(f"probe returned {result!r}")
    except Exception as exc:
        return ProbeResult(
            name=name,
            status="fail",
            duration_ms=int((time.monotonic() - started) * 1000),
            evidence=f"raised {type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------- probes

def probe_runtime_isolation(provider: ProviderSettings) -> ProbeResult:
    with tempfile.TemporaryDirectory(prefix="pw-probe-") as tmp:
        tmp_path = Path(tmp)
        rt = build_runtime(provider, tmp_path / "home", tmp_path / "data")
        try:
            blob = ""
            for candidate in (tmp_path / "home").rglob("agents.json"):
                blob += candidate.read_text(encoding="utf-8", errors="replace")
            leak = bool(provider.api_key) and provider.api_key not in (
                "",
                "pollinations-no-key-needed",
            ) and provider.api_key in blob
            return ProbeResult(
                name="runtime_isolation", status="fail" if leak else "pass",
                duration_ms=0,
                evidence=(
                    f"APIRuntime.from_config in isolated temp dirs; "
                    f"agents.json present={bool(blob)}; api key in file={leak}"
                ),
            )
        finally:
            rt.close()


def probe_memory_bundle_portability(provider: ProviderSettings) -> ProbeResult:
    from openminion import MemoryBundle

    bundle = MemoryBundle(
        items=[{"key": "CVPR|2026-12-01|full", "reminded_at": "2026-11-17T00:00:00+00:00"}],
        metadata={"format": "paper-watch-reminded-v1"},
    )
    dumped = bundle.to_json()
    restored = MemoryBundle.from_json(dumped)
    ok = restored.items == bundle.items and restored.metadata == bundle.metadata
    tamper = ""
    try:
        MemoryBundle.from_json(json.dumps({"version": "bogus.v9", "items": []}))
        tamper = "tampered version accepted (no rejection observed)"
    except Exception as exc:
        tamper = f"tampered version rejected with {type(exc).__name__}"
    return ProbeResult(
        name="memory_bundle_portability",
        status="pass" if ok else "fail",
        duration_ms=0,
        evidence=f"export->to_json->from_json round-trip identical={ok}; {tamper}",
    )


def probe_error_and_timeout_contracts(provider: ProviderSettings) -> ProbeResult:
    from openminion import Agent, ProviderError, TurnTimeoutError

    from .config import ProviderSettings as PS

    bad = PS(
        preset=provider.preset, base_url="http://127.0.0.1:9/v1",
        model=provider.model, api_key=provider.api_key,
        api_key_env=provider.api_key_env, timeout_seconds=10,
    )
    with tempfile.TemporaryDirectory(prefix="pw-probe-") as tmp:
        tmp_path = Path(tmp)
        rt = build_runtime(bad, tmp_path / "home", tmp_path / "data")
        try:
            agent = Agent(instructions="Say ok.", runtime=rt, name="error-probe")
            try:
                agent.run("Say ok.", timeout_seconds=30)
                return ProbeResult(
                    name="error_and_timeout_contracts", status="fail", duration_ms=0,
                    evidence="unreachable provider unexpectedly answered",
                )
            except (ProviderError, TurnTimeoutError) as exc:
                return ProbeResult(
                    name="error_and_timeout_contracts", status="pass", duration_ms=0,
                    evidence=f"unreachable provider raised {type(exc).__name__}: {str(exc)[:200]}",
                )
        finally:
            rt.close()


def probe_verification_honesty(provider: ProviderSettings, store: VenueStore, today: date) -> ProbeResult:
    """Deterministic: every rendered date carries its status; nothing is upgraded."""
    from .brief import _line_identity

    rows = store.upcoming(120, today)
    brief = build_template_brief("人工智能", rows)
    text = render_brief(brief)
    problems = check_honesty(text, rows)
    # No date_unclear venue may appear as a dated deadline line.
    # Identity is (abbreviation, full_name): FSE/CC/WWW each name two
    # different venues, one dated and one unclear.
    unclear_identities = {(d.abbreviation, d.full_name) for d in store.unclear}
    for line in text.splitlines():
        ident = _line_identity(line)
        if ident[0] and ident in unclear_identities:
            problems.append(f"unclear venue {ident[0]} rendered as dated: {line}")
    return ProbeResult(
        name="verification_honesty",
        status="pass" if not problems else "fail",
        duration_ms=0,
        evidence=(
            f"rendered {len(rows)} upcoming deadlines + honesty check: "
            f"{'0 violations' if not problems else '; '.join(problems[:3])}"
        ),
    )


# Model probes share one runtime + one agent where possible.
class _ModelProbes:
    def __init__(self, provider: ProviderSettings, store: VenueStore):
        self.provider = provider
        self.store = store
        self.tmp = tempfile.TemporaryDirectory(prefix="pw-probe-model-")
        self.tmp_path = Path(self.tmp.name)
        self.runtime = build_runtime(provider, self.tmp_path / "home", self.tmp_path / "data")

    def close(self):
        try:
            self.runtime.close()
        finally:
            self.tmp.cleanup()

    def _agent(self, instructions, **kw):
        from openminion import Agent

        return Agent(instructions=instructions, runtime=self.runtime, **kw)

    def structured_output(self) -> ProbeResult:
        from pydantic import BaseModel, Field

        class Tiny(BaseModel):
            answer: str = Field(description="one short sentence")
            confidence: float = Field(description="0-1")

        agent = self._agent(
            "Reply with ONLY one JSON object: {\"answer\": \"...\", \"confidence\": 0.9}. No other text.",
            name="probe-structured",
        )
        pace_model_call()
        res = run_agent_with_retry(agent, "What is 2+2? Answer in one short sentence.", timeout_seconds=240)
        obj = extract_json_object(res.text)
        ok = obj is not None
        parsed = None
        if ok:
            try:
                parsed = Tiny.model_validate(obj)
            except Exception:
                ok = False
        return ProbeResult(
            name="structured_output",
            status="pass" if ok else "partial",
            duration_ms=0,
            evidence=(
                f"raw reply: {res.text[:160]!r}; JSON extracted={obj is not None}; "
                f"Pydantic valid={parsed is not None}"
            ),
        )

    def tool_and_forced_tools(self) -> ProbeResult:
        from .agent import _tools_for

        tools = _tools_for(self.store, date(2026, 11, 17))
        agent = self._agent(
            "Call lookup_deadlines for topic 'vision' and report how many rows it returned. "
            "Reply with ONLY one JSON object: {\"rows\": <int>}.",
            name="probe-tools",
            tools=tools,
            forced_tools=["lookup_deadlines"],
        )
        pace_model_call()
        res = run_agent_with_retry(agent, "How many vision deadlines are upcoming?", timeout_seconds=240)
        obj = extract_json_object(res.text)
        rows = obj.get("rows") if isinstance(obj, dict) else None
        return ProbeResult(
            name="tool_and_forced_tools",
            status="pass" if isinstance(rows, int) else "partial",
            duration_ms=0,
            evidence=f"forced lookup_deadlines ran; model reported rows={rows}; raw reply: {res.text[:200]!r}",
        )

    def session_continuity(self) -> ProbeResult:
        marker = "paper-watch-marker-7F3A"
        agent = self._agent(
            "Remember what the user tells you in this session. Reply briefly.",
            name="probe-session",
        )
        pace_model_call()
        run_agent_with_retry(agent, f"Remember this marker: {marker}.", session_id="probe-session-1",
                             thread_id="probe-thread-1", timeout_seconds=240)
        pace_model_call()
        res2 = run_agent_with_retry(agent, "What marker did I ask you to remember? Reply with the marker only.",
                                    session_id="probe-session-1", thread_id="probe-thread-1",
                                    timeout_seconds=240)
        remembered = marker in res2.text
        pace_model_call()
        res3 = run_agent_with_retry(agent, "What marker did I ask you to remember?",
                                    session_id="probe-session-2", thread_id="probe-thread-2",
                                    timeout_seconds=240)
        leaked = marker in res3.text
        status = "pass" if remembered and not leaked else "partial"
        return ProbeResult(
            name="session_continuity", status=status, duration_ms=0,
            evidence=f"same thread recalled marker={remembered}; fresh session leaked={leaked}",
        )

    def subagent_delegation(self) -> ProbeResult:
        from openminion import subagent

        parent = self._agent("You coordinate brief summaries.", name="probe-parent")
        pace_model_call()
        child = subagent(
            parent,
            instructions="Reply with exactly this sentence: subagent ran ok.",
            name="probe-child",
            timeout_seconds=240,
        )
        res = run_agent_with_retry(child, "Go.", timeout_seconds=240)
        ok = "subagent ran ok" in res.text
        return ProbeResult(
            name="subagent_delegation",
            status="pass" if ok else "partial",
            duration_ms=0,
            evidence=f"child reply: {res.text[:160]!r}",
        )

    def agent_handoff(self) -> ProbeResult:
        from openminion import Handoff

        specialist = self._agent(
            "You are the formatter. Reply with exactly: formatted by specialist.",
            name="probe-specialist",
        )
        coordinator = self._agent(
            "You coordinate. Transfer to the formatter using format_reminder, then stop.",
            name="probe-coordinator",
            handoffs=[Handoff(target=specialist, name="format_reminder",
                              description="Format the result")],
        )
        pace_model_call()
        res = run_agent_with_retry(coordinator, "Please format this: test.", timeout_seconds=240)
        took = "formatted by specialist" in res.text
        return ProbeResult(
            name="agent_handoff",
            status="pass" if took else "partial",
            duration_ms=0,
            evidence=f"handoff reply: {res.text[:200]!r}; specialist text present={took}",
        )

    def submit_turn_streaming_telemetry(self) -> ProbeResult:
        agent = self._agent("Reply with one short sentence.", name="probe-stream")
        chunks: list = []

        def on_delta(chunk):
            chunks.append(chunk)

        pace_model_call()
        res = run_agent_stream_with_retry(agent, "Say hello in one sentence.", on_delta=on_delta,
                                          timeout_seconds=240)
        stats = dict(getattr(res, "stats", {}) or {})
        return ProbeResult(
            name="submit_turn_streaming_telemetry",
            status="pass" if chunks else "partial",
            duration_ms=0,
            evidence=(
                f"run_stream yielded {len(chunks)} chunks; text={res.text[:120]!r}; "
                f"stats={stats}"
            ),
        )


def run_probes(
    preset: str | None = None,
    *,
    skip_model: bool = False,
    data_dir: str | Path | None = None,
    today: date | None = None,
) -> list[ProbeResult]:
    """Run the probe suite in a fixed order; model probes are paced."""
    from .config import sanitize_no_proxy

    sanitize_no_proxy()
    today = today or date.today()
    provider = resolve_preset(preset)
    store = VenueStore.load(data_dir or _default_data_dir(), today=today)
    results: list[ProbeResult] = []
    results.append(_timed("runtime_isolation", lambda: probe_runtime_isolation(provider)))
    if not skip_model:
        mp = _ModelProbes(provider, store)
        try:
            for name in ("structured_output", "tool_and_forced_tools",
                         "session_continuity", "subagent_delegation",
                         "agent_handoff", "submit_turn_streaming_telemetry"):
                results.append(_timed(name, getattr(mp, name)))
        finally:
            mp.close()
    results.append(_timed("memory_bundle_portability", lambda: probe_memory_bundle_portability(provider)))
    results.append(_timed("error_and_timeout_contracts", lambda: probe_error_and_timeout_contracts(provider)))
    results.append(_timed("verification_honesty", lambda: probe_verification_honesty(provider, store, today)))
    return results


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


def render_probes_doc(results: list[ProbeResult], provider: ProviderSettings) -> str:
    passed = sum(1 for r in results if r.status == "pass")
    partial = sum(1 for r in results if r.status == "partial")
    failed = sum(1 for r in results if r.status == "fail")
    total_ms = sum(r.duration_ms for r in results)
    lines = [
        "# Building Blocks Tested",
        "",
        "Auto-generated by `paper-watch probe`. Only the blocks this agent "
        "actually uses are probed — nothing is claimed for blocks the agent "
        "does not touch.",
        "",
        f"- Preset: `{provider.preset}` — model `{provider.model}` "
        f"at `{provider.base_url}` (free tier, $0)",
        f"- Result: **{passed} pass / {partial} partial / {failed} fail** "
        f"out of {len(results)} probes, {total_ms / 1000:.1f}s total",
        f"- Generated: {date.today().isoformat()}",
        "",
        "| # | Building block | Status | Time | Evidence |",
        "|---|----------------|--------|------|----------|",
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"| {i} | `{r.name}` | {r.status} | {r.duration_ms / 1000:.1f}s | {r.evidence} |"
        )
    lines += [
        "",
        "## Probe catalogue",
        "",
        "All blocks this agent uses (a probe not run in this invocation is "
        "marked `skipped`, never `pass`):",
        "",
    ]
    ran = {r.name for r in results}
    for name in PROBE_NAMES:
        lines.append(f"- `{name}` — {'ran (see table above)' if name in ran else 'skipped in this run'}")
    lines += [
        "",
        "## How to reproduce",
        "",
        "```bash",
        "python -m venv .venv && .venv/bin/pip install -e .",
        "paper-watch probe --export-docs docs/BUILDING_BLOCKS_TESTED.md",
        "```",
        "",
        "`--skip-model` runs only the four model-free probes "
        "(runtime isolation, memory bundle, error/timeout, verification honesty).",
        "",
        "## Notes",
        "",
        "- `partial` means the block ran but the free model did not fully "
        "cooperate (e.g. prose instead of JSON, handoff not taken). The "
        "agent treats those paths as degraded, never as passed.",
        "- The `verification_honesty` probe is deterministic and specific to "
        "this project: any rendered date must carry its verification status, "
        "and an unverified date must never appear as verified.",
    ]
    return "\n".join(lines) + "\n"
