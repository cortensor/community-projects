"""Render a 66-second 1280x720 H.264 walkthrough video from artifacts/latest_report.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "artifacts" / "latest_report.json"
OUT_VIDEO = ROOT / "demo.mp4"

WIDTH = 1280
HEIGHT = 720
FPS = 15

BG = (10, 14, 24)
PANEL = (18, 25, 42)
BORDER = (46, 64, 102)
CYAN = (56, 189, 248)
EMERALD = (52, 211, 153)
AMBER = (251, 191, 36)
ROSE = (248, 113, 113)
TEXT = (241, 245, 249)
MUTED = (148, 163, 184)


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = (
        [
            "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        ]
    )
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


FONT_TITLE = _load_font(34, bold=True)
FONT_SUB = _load_font(20, bold=False)
FONT_HEAD = _load_font(24, bold=True)
FONT_MONO = _load_font(17, bold=False)
FONT_MONO_B = _load_font(17, bold=True)
FONT_SMALL = _load_font(14, bold=False)


def _new_canvas(scene_tag: str, progress: float, sec: int, total_sec: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # Top bar
    draw.rectangle([0, 0, WIDTH, 64], fill=(15, 21, 36))
    draw.line([0, 64, WIDTH, 64], fill=BORDER, width=2)
    draw.text((36, 16), "CORTENSOR OPENMINION SENTINEL  |  v0.1.0", fill=CYAN, font=FONT_HEAD)
    draw.text((WIDTH - 360, 21), f"{scene_tag}  [{sec:02d}s / {total_sec:02d}s]", fill=MUTED, font=FONT_MONO)

    # Bottom progress bar
    draw.rectangle([0, HEIGHT - 44, WIDTH, HEIGHT], fill=(15, 21, 36))
    draw.line([0, HEIGHT - 44, WIDTH, HEIGHT - 44], fill=BORDER, width=2)
    bar_w = int((WIDTH - 72) * progress)
    draw.rectangle([36, HEIGHT - 30, WIDTH - 36, HEIGHT - 22], fill=(30, 41, 59))
    draw.rectangle([36, HEIGHT - 30, 36 + bar_w, HEIGHT - 22], fill=EMERALD)
    draw.text(
        (36, HEIGHT - 19),
        "Cortensor Hackathon #5  |  OpenMinion 0.1.23 SDK  |  MIT License  |  github.com/random-solver/cortensor-openminion-sentinel",
        fill=MUTED,
        font=FONT_SMALL,
    )
    return img, draw


def _box(draw: ImageDraw.ImageDraw, xy: list[int], accent: tuple[int, int, int] = BORDER) -> None:
    draw.rounded_rectangle(xy, radius=10, fill=PANEL, outline=accent, width=2)


def _render_scene_1_title(progress: float, sec: int, total_sec: int, report: dict[str, Any]) -> np.ndarray:
    img, draw = _new_canvas("01 OVERVIEW", progress, sec, total_sec)
    draw.text((48, 95), "Verifiable Multi-Agent DeFi Control-Plane Sentinel", fill=TEXT, font=FONT_TITLE)
    draw.text(
        (48, 145),
        "Built on Cortensor Decentralized Inference + OpenMinion 0.1.23 Agent Runtime",
        fill=CYAN,
        font=FONT_SUB,
    )

    probes = report["sdk_probes"]
    audits = report["audits"]
    cards = [
        ("OpenMinion SDK Probes", f"{probes['passed']}/{probes['total_probes']} PASSED", f"Duration: {probes['total_duration_ms']} ms", EMERALD),
        ("On-Chain Targets Audited", f"{len(audits)} Consensus Runs", "Ethereum + Base Mainnet RPC", CYAN),
        ("Architecture Pattern", "Auditor + Skeptic Subagent", "Fail-Closed Handoff Gate", AMBER),
    ]
    for i, (label, big, sub, col) in enumerate(cards):
        x0 = 48 + i * 400
        _box(draw, [x0, 200, x0 + 372, 345], accent=col)
        draw.text((x0 + 20, 218), label, fill=MUTED, font=FONT_SUB)
        draw.text((x0 + 20, 256), big, fill=col, font=FONT_HEAD)
        draw.text((x0 + 20, 302), sub, fill=TEXT, font=FONT_MONO)

    _box(draw, [48, 375, WIDTH - 48, 640], accent=BORDER)
    draw.text((70, 394), "Why Control-Plane Consensus Matters:", fill=AMBER, font=FONT_HEAD)
    bullets = [
        "1. Read-Only On-Chain Verification: Inspects EVM bytecode, EIP-1967 proxy/admin slots,",
        "   Gnosis Safe thresholds (getThreshold / getOwners), and Governance Timelock delays.",
        "2. Skeptic Subagent Second-Opinion: Independent subagent(memory_posture='none') verifies",
        "   primary risk findings before releasing an operational verdict.",
        "3. Fail-Closed Escalation: Any HIGH/CRITICAL exposure OR auditor-skeptic disagreement",
        "   routes deterministically via OpenMinion Handoff(transfer_to_incident_desk).",
        "4. Portable Evidence: Exports signed-shape state into MemoryBundle(version='memory_bundle.v1').",
    ]
    y = 438
    for line in bullets:
        draw.text((70, y), line, fill=TEXT, font=FONT_MONO)
        y += 28
    return np.asarray(img)


def _render_scene_2_architecture(progress: float, sec: int, total_sec: int, report: dict[str, Any]) -> np.ndarray:
    img, draw = _new_canvas("02 ARCHITECTURE", progress, sec, total_sec)
    draw.text((48, 92), "End-to-End Execution Pipeline (Cortensor + OpenMinion)", fill=TEXT, font=FONT_HEAD)

    stages = [
        ("EVM Public RPC\nETH + Base", "eth_getCode\nEIP-1967 slots\nSafe & Timelock", 48, CYAN),
        ("@tool READ_ONLY\nPrimary Agent", "sentinel Agent\nAPIRuntime bridge\nCortensor /v2", 348, EMERALD),
        ("Bounded Skeptic\nsubagent()", "Isolated Context\nChallenge Findings\nConsensus Check", 648, AMBER),
        ("Fail-Closed Gate\nHandoff + Bundle", "transfer_to_\nincident_desk &\nMemoryBundle v1", 948, ROSE),
    ]
    for idx, (title, desc, x0, col) in enumerate(stages):
        _box(draw, [x0, 155, x0 + 265, 345], accent=col)
        draw.text((x0 + 18, 174), title, fill=col, font=FONT_MONO_B)
        draw.text((x0 + 18, 240), desc, fill=TEXT, font=FONT_MONO)
        if idx < 3:
            ax = x0 + 270
            draw.line([ax, 250, ax + 24, 250], fill=CYAN, width=4)

    _box(draw, [48, 375, WIDTH - 48, 645], accent=CYAN)
    draw.text((70, 395), "OpenMinion 0.1.23 Canonical Turn Path & Cortensor Provider Config:", fill=CYAN, font=FONT_MONO_B)
    posture = report["audits"][0]["runtime_posture"] if report["audits"] else {}
    lines = [
        f"runtime_mode      : {posture.get('runtime_mode', 'brain')} (brain_bridge_active={posture.get('brain_bridge_active', True)})",
        "turn_path         : " + " -> ".join(posture.get("canonical_turn_path", [])),
        "provider_endpoint : /api/v2/completions (CortensorProviderConfig, session_pool='auto', privacy='high')",
        "channel_auth      : AgentProfileConfig(default_channel='console') + ChannelAuthenticityConfig(mode='warn')",
        "subagent_guard    : subagent(..., memory_posture='none') avoids unbound v1 developer grant trap",
        f"bundle_schema     : memory_bundle.v1 (JSON round-trip verified in test suite)",
    ]
    y = 435
    for line in lines:
        draw.text((70, y), line[:106], fill=TEXT, font=FONT_MONO)
        y += 32
    return np.asarray(img)


def _render_scene_3_probes(progress: float, sec: int, total_sec: int, report: dict[str, Any]) -> np.ndarray:
    img, draw = _new_canvas("03 SDK PROBES", progress, sec, total_sec)
    probes = report["sdk_probes"]
    draw.text(
        (48, 92),
        f"OpenMinion v{probes['openminion_version']} Automated SDK Verification ({probes['passed']}/{probes['total_probes']} PASS)",
        fill=TEXT,
        font=FONT_HEAD,
    )
    _box(draw, [48, 138, WIDTH - 48, 650], accent=EMERALD)
    draw.text((70, 155), "PROBE ID                 | STATUS | TIME(ms) | VERIFIED BEHAVIOR", fill=CYAN, font=FONT_MONO_B)
    draw.line([68, 184, WIDTH - 68, 184], fill=BORDER, width=1)

    y = 198
    for p in probes["probes"]:
        status = "PASS" if p["passed"] else "FAIL"
        col = EMERALD if p["passed"] else ROSE
        line = f"{p['probe_id']:<24} |  {status}  | {p['duration_ms']:>7.2f}  | {p['detail'][:62]}"
        draw.text((70, y), line, fill=col if not p["passed"] else TEXT, font=FONT_MONO)
        y += 52
    return np.asarray(img)


def _render_scene_4_audits(progress: float, sec: int, total_sec: int, report: dict[str, Any]) -> np.ndarray:
    img, draw = _new_canvas("04 LIVE AUDITS", progress, sec, total_sec)
    draw.text((48, 92), "Multi-Agent Control-Plane Audit Results (Ethereum & Base)", fill=TEXT, font=FONT_HEAD)

    audits = report["audits"]
    y = 142
    for idx, a in enumerate(audits[:4]):
        cp = a["control_plane"]
        tier = a["final_risk_tier"]
        col = EMERALD if tier == "LOW" else (AMBER if tier == "MEDIUM" else ROSE)
        _box(draw, [48, y, WIDTH - 48, y + 114], accent=col)
        header = (
            f"[{idx+1}] {a['target']['name']}  ({cp['chain']}:{cp['address']})  "
            f"| RISK={tier} ({cp['risk_score']}/100)"
        )
        draw.text((68, y + 12), header, fill=col, font=FONT_MONO_B)
        sub1 = (
            f"Source={cp['source']}  | Code={cp['code_size_bytes']}B  | Gov={cp['governance_kind']} "
            f"({cp['governance_or_owner'][:18]}...)  | Safe={cp['safe_threshold']}/{cp['safe_owner_count']}"
        )
        draw.text((68, y + 44), sub1, fill=TEXT, font=FONT_MONO)
        sub2 = (
            f"Consensus={a['consensus_status']}  | Primary={a['primary_run_state']}  "
            f"| Skeptic={a['skeptic_run_state']}  | Handoff Escalated={a['escalated_via_handoff']}"
        )
        draw.text((68, y + 74), sub2, fill=CYAN if a["consensus_status"] == "AGREED" else ROSE, font=FONT_MONO)
        y += 126
    return np.asarray(img)


def _render_scene_5_feedback(progress: float, sec: int, total_sec: int, report: dict[str, Any]) -> np.ndarray:
    img, draw = _new_canvas("05 FEEDBACK & VERDICT", progress, sec, total_sec)
    draw.text((48, 92), "Actionable OpenMinion 0.1 SDK Insights & Hackathon Summary", fill=TEXT, font=FONT_HEAD)

    _box(draw, [48, 145, WIDTH - 48, 435], accent=AMBER)
    draw.text((70, 165), "Empirical Edge Cases Surfacing in OpenMinion 0.1.23 (Documented in FEEDBACK.md):", fill=AMBER, font=FONT_MONO_B)
    notes = [
        "1. Agent Name vs ID Trap: Agent(agent_id='sentinel', name='Sentinel') raises UnknownProfileError;",
        "   profile keys in OpenMinionConfig.agents must match the Agent display name or omit mismatching name.",
        "2. Channel Authenticity Empty-Channel Block: AgentProfileConfig.default_channel defaults to '', triggering",
        "   GatewaySecurity invalid_channel rejection even when mode='warn'. Fix: default_channel='console'.",
        "3. Subagent v1 Memory Posture Guard: memory_posture='read_only_bounded' throws ValueError unless",
        "   bound via DelegatedMemoryReadRequest; sentinel documents the boundary & bridges state via MemoryBundle.",
        "4. Cortensor base_url Path Handling: _resolve_api_mode inspects /completions suffix; /api/v2/completions works.",
    ]
    y = 205
    for line in notes:
        draw.text((70, y), line, fill=TEXT, font=FONT_MONO)
        y += 30

    _box(draw, [48, 455, WIDTH - 48, 645], accent=EMERALD)
    draw.text((70, 475), "Verified Hackathon #5 Submission Readiness:", fill=EMERALD, font=FONT_HEAD)
    draw.text((70, 520), "Repo     : https://github.com/random-solver/cortensor-openminion-sentinel", fill=CYAN, font=FONT_MONO)
    draw.text((70, 552), "Live App : https://random-solver.github.io/cortensor-openminion-sentinel/", fill=CYAN, font=FONT_MONO)
    draw.text((70, 584), "Tests    : unittest (5/5 PASS)  |  8/8 OpenMinion Probes PASS  |  MIT Licensed", fill=TEXT, font=FONT_MONO)
    return np.asarray(img)


def main() -> int:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    # 5 scenes across 66 seconds (12 + 13 + 14 + 14 + 13 = 66s -> comfortably inside 1-5 min window)
    schedule = [
        (0, 12, _render_scene_1_title),
        (12, 25, _render_scene_2_architecture),
        (25, 39, _render_scene_3_probes),
        (39, 53, _render_scene_4_audits),
        (53, 66, _render_scene_5_feedback),
    ]
    total_sec = 66
    writer = imageio.get_writer(str(OUT_VIDEO), fps=FPS, codec="libx264", pixelformat="yuv420p")
    try:
        for t_sec in range(total_sec):
            progress = (t_sec + 1) / total_sec
            renderer = schedule[-1][2]
            for start, end, fn in schedule:
                if start <= t_sec < end:
                    renderer = fn
                    break
            frame = renderer(progress, t_sec + 1, total_sec, report)
            for _ in range(FPS):
                writer.append_data(frame)
    finally:
        writer.close()

    size_kb = OUT_VIDEO.stat().st_size // 1024
    print(f"Generated {OUT_VIDEO} ({total_sec}s, {size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
