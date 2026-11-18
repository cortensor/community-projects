"""Automated 8-probe OpenMinion 0.1.23 SDK verification suite."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from openminion import (
    APIRuntime,
    Agent,
    Handoff,
    MemoryBundle,
    __version__ as OPENMINION_VERSION,
    subagent,
    tool,
)
from openminion.api.handoff import build_delegate_tool
from openminion.base.config.core import AgentProfileConfig
from openminion.base.config.providers import CortensorProviderConfig

from sentinel.engine import LoopbackInferenceServer, build_sentinel_config


@dataclass(frozen=True)
class ProbeResult:
    """Single SDK verification probe outcome."""

    probe_id: str
    building_block: str
    passed: bool
    duration_ms: float
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_timed(probe_id: str, building_block: str, fn: Any) -> ProbeResult:
    t0 = time.perf_counter()
    try:
        detail = str(fn())
        return ProbeResult(
            probe_id=probe_id,
            building_block=building_block,
            passed=True,
            duration_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            detail=detail,
        )
    except Exception as exc:
        return ProbeResult(
            probe_id=probe_id,
            building_block=building_block,
            passed=False,
            duration_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            detail=f"{type(exc).__name__}: {exc}",
        )


def run_openminion_probes() -> dict[str, Any]:
    """Execute 8 targeted verification probes against openminion==0.1.23."""
    results: list[ProbeResult] = []
    started = time.perf_counter()

    with TemporaryDirectory(ignore_cleanup_errors=True) as td, LoopbackInferenceServer() as srv:
        root = Path(td)
        cfg = build_sentinel_config(
            storage_db=root / "probes.db",
            provider_mode="openai",
            openai_base_url=srv.openai_base_url,
            cortensor_base_url=srv.cortensor_base_url,
        )
        rt = APIRuntime.from_config(config=cfg, home_root=root / "home", data_root=root / "data")

        try:
            @tool(min_scope="READ_ONLY")
            def probe_echo(value: str) -> str:
                """Read-only probe echo tool."""
                return f"echo:{value}"

            parent = Agent(
                runtime=rt,
                agent_id="sentinel",
                name="sentinel",
                instructions="Primary probe auditor.",
                tools=[probe_echo],
            )
            skeptic_child = subagent(
                parent,
                name="skeptic",
                instructions="Skeptic child verifier.",
                memory_posture="none",
            )
            desk_agent = Agent(
                runtime=rt,
                agent_id="incident_desk",
                name="incident_desk",
                instructions="Receive escalated findings.",
            )

            # P1: Runtime posture & tool inventory introspection
            def p1() -> str:
                posture = rt.runtime_posture(agent_id="sentinel")
                cap = rt.capability_report(agent_id="sentinel")
                inv = rt.tool_inventory_report(readiness=False)
                assert posture.get("agent") == "sentinel", f"posture={posture}"
                assert isinstance(inv, list) and len(inv) > 0
                assert "canonical_turn_path" in posture
                return (
                    f"agent={posture['agent']}, mode={posture.get('runtime_mode')}, "
                    f"brain_bridge={posture.get('brain_bridge_active')}, "
                    f"tools_indexed={len(inv)}, cap_keys={len(cap)}"
                )

            # P2: @tool(min_scope="READ_ONLY") execution inside full Gateway -> Brain turn
            def p2() -> str:
                res = parent.run("RUN_PROBE_TOOL verify structured tool envelope")
                assert res.run_state == "completed", f"unexpected run_state={res.run_state}"
                assert "TOOL_SYNTHESIS_OK" in (res.text or ""), f"unexpected text={res.text}"
                assert "echo:sentinel-ok" in (res.text or ""), f"tool result missing in {res.text}"
                return f"run_state={res.run_state}, run_id={res.run_id}"

            # P3: ChannelAuthenticityConfig & AgentProfileConfig defaults
            def p3() -> str:
                prof = cfg.agents["sentinel"]
                assert prof.default_channel == "console"
                assert cfg.channel_authenticity.mode == "warn"
                assert "console" in cfg.channel_authenticity.trusted_channels
                return f"default_channel={prof.default_channel}, auth_mode={cfg.channel_authenticity.mode}"

            # P4: subagent() isolated lineage & context metadata
            def p4() -> str:
                ctx = skeptic_child.subagent_context
                assert ctx is not None
                assert ctx.parent_agent_id == "sentinel"
                assert ctx.child_agent_id == "skeptic"
                assert ctx.parent_transcript_inherited is False
                cres = skeptic_child.run("SKEPTIC_VERIFY probe-check")
                assert cres.run_state == "completed"
                assert "SKEPTIC_AGREE" in (cres.text or "")
                return f"context_id={ctx.context_id}, trace_parent={ctx.trace_parent_id}"

            # P5: subagent() v1 memory_posture="read_only_bounded" explicit guard verification
            def p5() -> str:
                try:
                    subagent(parent, name="guarded", memory_posture="read_only_bounded")
                except ValueError as exc:
                    assert "not bound in v1" in str(exc)
                    return f"guarded ValueError confirmed: {exc}"
                raise AssertionError("Expected ValueError for unbound read_only_bounded posture")

            # P6: Handoff + build_delegate_tool transfer execution
            def p6() -> str:
                ho = Handoff(
                    target=desk_agent,
                    name="transfer_to_incident_desk",
                    description="Transfer critical alerts to incident desk.",
                )
                tool_decl = build_delegate_tool(ho)
                assert tool_decl.name == "transfer_to_incident_desk"
                out = tool_decl.handler({"message": "INCIDENT_ESCALATION probe-handoff"})
                assert out.get("ok") is True
                assert "INCIDENT_LOGGED" in str(out.get("content", ""))
                return f"tool={tool_decl.name}, run_state={out.get('data', {}).get('run_state')}"

            # P7: MemoryBundle v1 schema & JSON round-trip
            def p7() -> str:
                mb = MemoryBundle(
                    version="memory_bundle.v1",
                    items=[{"target": "0xa354", "tier": "LOW", "score": 15}],
                    metadata={"sentinel_version": "0.1.0"},
                )
                restored = MemoryBundle.from_json(mb.to_json())
                assert restored.version == "memory_bundle.v1"
                assert len(restored.items) == 1
                assert restored.items[0]["tier"] == "LOW"
                return f"version={restored.version}, items={len(restored.items)}"

            # P8: Native CortensorProviderConfig + live Cortensor loopback completion path
            def p8() -> str:
                cort_root = root / "cortensor_rt"
                cort_cfg = build_sentinel_config(
                    storage_db=cort_root / "cortensor.db",
                    provider_mode="cortensor",
                    cortensor_base_url=srv.cortensor_base_url,
                )
                c_prov: CortensorProviderConfig = cort_cfg.providers.cortensor
                assert c_prov.session_pool == "auto"
                assert c_prov.session_id == 1
                assert c_prov.privacy_level == "high"
                os.environ["CORTENSOR_API_KEY"] = "cor-sentinel-probe"
                crt = APIRuntime.from_config(
                    config=cort_cfg,
                    home_root=cort_root / "home",
                    data_root=cort_root / "data",
                )
                try:
                    c_agent = Agent(
                        runtime=crt,
                        agent_id="sentinel",
                        name="sentinel",
                        instructions="Cortensor session verification agent.",
                    )
                    before = len(srv.requests)
                    res = c_agent.run("Verify Cortensor /api/v2/completions session turn.")
                    assert res.run_state == "completed"
                    cor_paths = [r["path"] for r in srv.requests[before:]]
                    assert any("/api/v2/completions" in p for p in cor_paths), f"paths={cor_paths}"
                    return (
                        f"provider=cortensor, paths={cor_paths[0]}, "
                        f"session_id={c_prov.session_id}, run_state={res.run_state}"
                    )
                finally:
                    crt.close()

            specs = [
                ("P1_runtime_bootstrap", "APIRuntime & Posture Reports", p1),
                ("P2_agent_tool_call", "@tool(min_scope='READ_ONLY') Execution", p2),
                ("P3_channel_authenticity", "AgentProfileConfig & ChannelAuthenticity", p3),
                ("P4_subagent_lineage", "subagent() Context Isolation & Consensus", p4),
                ("P5_subagent_memory_guard", "subagent() v1 Memory Posture Guard", p5),
                ("P6_handoff_delegation", "Handoff & build_delegate_tool()", p6),
                ("P7_memory_bundle_v1", "MemoryBundle JSON Serialization", p7),
                ("P8_cortensor_provider", "CortensorProviderConfig (/api/v2/completions)", p8),
            ]
            for pid, block, fn in specs:
                results.append(_run_timed(pid, block, fn))
        finally:
            rt.close()

    passed_count = sum(1 for r in results if r.passed)
    return {
        "openminion_version": OPENMINION_VERSION,
        "total_probes": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "total_duration_ms": round((time.perf_counter() - started) * 1000.0, 2),
        "probes": [r.to_dict() for r in results],
    }
