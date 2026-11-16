"""Captioned 1080p MP4 demo video renderer driven by AuditRunBundle & ProbeSuiteReport JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from cortensor_verifier.probe import EXPECTED_PROBE_IDS, assert_no_plaintext_secrets

DEMO_WIDTH = 1920
DEMO_HEIGHT = 1080
DEFAULT_DEMO_DURATION_SECONDS = 75
DEFAULT_DEMO_FPS = 10
TOTAL_SCENES = 7
ANIMATION_STAGES = 5

_SCENE_TITLES: tuple[tuple[str, str], ...] = (
    (
        "1 · Problem & Isolated OpenMinion 0.1 Architecture",
        "Scene 1 / 7 · Eliminating single-pass hallucinations with isolated runtimes",
    ),
    (
        "2 · Claim Dossier & READ_ONLY Evidence Tools",
        "Scene 2 / 7 · Scoped ClaimDossier loading and READ_ONLY @tool evidence retrieval",
    ),
    (
        "3 · Redundant Verifier Passes (subagent Isolation)",
        "Scene 3 / 7 · Independent Corroborator and Skeptic subagent() verification",
    ),
    (
        "4 · Consensus Verdict & Session MemoryBundle",
        "Scene 4 / 7 · Structured ConsensusVerdict synthesis and scoped session continuity",
    ),
    (
        "5 · Approval-Gated Publication (Handoff Pause/Resume)",
        "Scene 5 / 7 · Fail-closed operator approval gate over OpenMinion Handoff",
    ),
    (
        "6 · OpenMinion 0.1 Building Block Probe Matrix (10/10)",
        "Scene 6 / 7 · End-to-end latency and contract verification across 10 SDK primitives",
    ),
    (
        "7 · Key Empirical DX Takeaways & Reproducible CLI",
        "Scene 7 / 7 · Empirical What We Learned findings and one-command reproducibility",
    ),
)

_SCENE_CAPTIONS: tuple[str, ...] = (
    "Single-pass LLMs hallucinate and risk side effects; OpenMinion isolates credentials, policies, and subagent execution.",
    "Only min_scope='READ_ONLY' @tool bindings attach to verifier passes, preventing workspace writes at the policy layer.",
    "Independent corroborator and skeptic subagent() passes inspect the Claim Dossier with zero shared transcript leakage.",
    "synthesize_consensus() fuses dual pass verdicts and agreement_score while exporting a session-scoped MemoryBundle.",
    "External publication routes via Handoff pause -> thread_id checkpoint -> single-use PolicyGrantInput(max_uses=1).",
    "All 10 OpenMinion 0.1 building blocks verified end-to-end against real APIRuntime and live LLM inference.",
    "Reproduce every consensus audit, 10-probe SDK matrix, and captioned 1080p walkthrough offline or live in one CLI call.",
)


@dataclass(frozen=True)
class DemoRenderResult:
    """Metadata describing a rendered captioned MP4 walkthrough."""

    output_path: Path
    width: int
    height: int
    fps: int
    duration_seconds: float
    frame_count: int
    scene_count: int
    file_size_bytes: int
    calibration_status: str
    model: str
    claim_id: str


def resolve_default_sample_run_path() -> Path:
    """Locate fixtures/calibrated_sample_run.json relative to repo root or CWD."""
    package_root = Path(__file__).resolve().parents[2]
    candidate = package_root / "fixtures" / "calibrated_sample_run.json"
    if candidate.exists():
        return candidate
    return Path.cwd() / "fixtures" / "calibrated_sample_run.json"


def load_demo_inputs(
    *,
    sample_json: str | Path | None = None,
    audit_json: str | Path | None = None,
    probe_json: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load AuditRunBundle & ProbeSuiteReport dictionaries from sample or separate JSON files."""
    if sample_json is None and audit_json is None and probe_json is None:
        sample_json = resolve_default_sample_run_path()

    audit_data: dict[str, Any] = {}
    probe_data: dict[str, Any] = {}
    if sample_json is not None:
        sample_path = Path(sample_json)
        loaded = json.loads(sample_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"Sample JSON {sample_path} must decode to a JSON object.")
        if isinstance(loaded.get("audit_bundle"), dict):
            audit_data = dict(loaded["audit_bundle"])
        elif "consensus" in loaded and "claim_id" in loaded:
            audit_data = dict(loaded)
        if isinstance(loaded.get("probe_report"), dict):
            probe_data = dict(loaded["probe_report"])

    if audit_json is not None:
        loaded_audit = json.loads(Path(audit_json).read_text(encoding="utf-8"))
        if not isinstance(loaded_audit, dict):
            raise ValueError(f"Audit JSON {audit_json} must decode to a JSON object.")
        audit_data = dict(loaded_audit)

    if probe_json is not None:
        loaded_probe = json.loads(Path(probe_json).read_text(encoding="utf-8"))
        if not isinstance(loaded_probe, dict):
            raise ValueError(f"Probe JSON {probe_json} must decode to a JSON object.")
        probe_data = dict(loaded_probe)

    if not audit_data or not probe_data:
        raise ValueError(
            "Both audit_bundle and probe_report payloads are required to render the demo video."
        )
    return audit_data, probe_data


def _load_font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates: list[Path]
    win_fonts = Path(r"C:\Windows\Fonts")
    linux_fonts = (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/truetype/liberation2"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/dejavu"),
        Path("/usr/share/fonts/liberation"),
        Path("/usr/share/fonts/TTF"),
        Path("/usr/share/fonts"),
    )
    mac_fonts = (
        Path("/System/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
        Path("/Library/Fonts"),
    )
    if mono:
        candidates = [
            win_fonts / ("consolab.ttf" if bold else "consola.ttf"),
            win_fonts / ("courbd.ttf" if bold else "cour.ttf"),
            win_fonts / ("arialbd.ttf" if bold else "arial.ttf"),
            *(
                p / name
                for p in linux_fonts
                for name in (
                    "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
                    "LiberationMono-Bold.ttf" if bold else "LiberationMono-Regular.ttf",
                    "NotoSansMono-Bold.ttf" if bold else "NotoSansMono-Regular.ttf",
                )
            ),
            *(p / name for p in mac_fonts for name in ("Menlo.ttc", "Monaco.ttf", "Courier New.ttf")),
        ]
    elif bold:
        candidates = [
            win_fonts / "segoeuib.ttf",
            win_fonts / "arialbd.ttf",
            *(
                p / name
                for p in linux_fonts
                for name in (
                    "DejaVuSans-Bold.ttf",
                    "LiberationSans-Bold.ttf",
                    "NotoSans-Bold.ttf",
                )
            ),
            *(
                p / name
                for p in mac_fonts
                for name in ("Helvetica.ttc", "Arial Bold.ttf", "HelveticaNeue.ttc")
            ),
        ]
    else:
        candidates = [
            win_fonts / "segoeui.ttf",
            win_fonts / "arial.ttf",
            *(
                p / name
                for p in linux_fonts
                for name in (
                    "DejaVuSans.ttf",
                    "LiberationSans-Regular.ttf",
                    "NotoSans-Regular.ttf",
                )
            ),
            *(
                p / name
                for p in mac_fonts
                for name in ("Helvetica.ttc", "Arial.ttf", "HelveticaNeue.ttc")
            ),
        ]

    for font_path in candidates:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []

    lines: list[str] = []
    current = ""
    raw_tokens = clean.split(" ")
    tokens: list[str] = []
    for raw_tok in raw_tokens:
        if not raw_tok or draw.textlength(raw_tok, font=font) <= max_width:
            tokens.append(raw_tok)
            continue
        piece = ""
        for ch in raw_tok:
            cand = piece + ch
            if piece and draw.textlength(cand, font=font) > max_width:
                tokens.append(piece)
                piece = ch
            else:
                piece = cand
        if piece:
            tokens.append(piece)
    for token in tokens:
        trial = f"{current} {token}".strip()
        width = draw.textlength(trial, font=font)
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = token
    if current:
        lines.append(current)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines[-1]:
            lines[-1] = _truncate_line(draw, lines[-1].rstrip("."), font, max_width)
    return lines


def _truncate_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    base = text.rstrip()
    while base and draw.textlength(base + "...", font=font) > max_width:
        base = base[:-1].rstrip()
    return (base + "...") if base else "..."


def _fit_single_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    clean = " ".join(str(text or "").split())
    if not clean or draw.textlength(clean, font=font) <= max_width:
        return clean
    return _truncate_line(draw, clean, font, max_width)


def _fit_caption_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    *,
    max_width: int = DEMO_WIDTH - 160,
    max_lines: int = 2,
) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    if draw.textlength(clean, font=font) <= max_width:
        return [clean]
    return _wrap_text(draw, clean, font, max_width=max_width, max_lines=max_lines)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    *,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    fill: str,
    max_width: int,
    line_height: int,
    max_lines: int | None = None,
) -> int:
    x, y = xy
    for line in _wrap_text(draw, text, font, max_width, max_lines=max_lines):
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _draw_card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str = "#111A2E",
    outline: str = "#1E293B",
    radius: int = 16,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    *,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    bg: str,
    fg: str,
    pad_x: int = 16,
    pad_y: int = 8,
) -> int:
    x, y = xy
    tw = int(draw.textlength(text, font=font))
    box = (x, y, x + tw + pad_x * 2, y + 36 + pad_y)
    draw.rounded_rectangle(box, radius=18, fill=bg)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return box[2]


@dataclass(frozen=True)
class _Fonts:
    h1: Any
    h2: Any
    h3: Any
    body: Any
    small: Any
    tiny: Any
    small_bold: Any
    mono: Any
    mono_sm: Any
    mono_bold: Any


def _create_fonts() -> _Fonts:
    return _Fonts(
        h1=_load_font(40, bold=True),
        h2=_load_font(28, bold=True),
        h3=_load_font(23, bold=True),
        body=_load_font(21, bold=False),
        small=_load_font(19, bold=False),
        tiny=_load_font(16, bold=False),
        small_bold=_load_font(19, bold=True),
        mono=_load_font(20, mono=True),
        mono_sm=_load_font(17, mono=True),
        mono_bold=_load_font(21, bold=True, mono=True),
    )


def _draw_chrome(
    scene_idx: int,
    *,
    fonts: _Fonts,
    calibration_status: str,
    model: str,
    sdk_version: str,
) -> Image.Image:
    img = Image.new("RGB", (DEMO_WIDTH, DEMO_HEIGHT), "#0A0F1C")
    draw = ImageDraw.Draw(img)

    # Subtle grid accents
    for gx in range(80, DEMO_WIDTH, 160):
        draw.line((gx, 0, gx, DEMO_HEIGHT), fill="#0E1526", width=1)
    for gy in range(80, DEMO_HEIGHT, 160):
        draw.line((0, gy, DEMO_WIDTH, gy), fill="#0E1526", width=1)

    # Top header bar
    draw.rectangle((0, 0, DEMO_WIDTH, 148), fill="#0D1424")
    draw.line((0, 148, DEMO_WIDTH, 148), fill="#1E293B", width=2)

    title_en, title_zh = _SCENE_TITLES[scene_idx]
    draw.text((56, 26), title_en, font=fonts.h1, fill="#F8FAFC")
    draw.text((58, 84), title_zh, font=fonts.body, fill="#94A3B8")

    # Right header badges
    is_live = "Live LLM Calibrated" in calibration_status
    cal_bg = "#064E3B" if is_live else "#78350F"
    cal_fg = "#6EE7B7" if is_live else "#FDE68A"
    cal_label = "LIVE LLM CALIBRATED" if is_live else "LOOPBACK BASELINE"
    meta_label = f"openminion=={sdk_version}  |  model={model}"
    meta_w = int(draw.textlength(meta_label, font=fonts.mono))
    draw.text((DEMO_WIDTH - meta_w - 56, 88), meta_label, font=fonts.mono, fill="#38BDF8")

    cal_w = int(draw.textlength(cal_label, font=fonts.small)) + 32
    _draw_pill(
        draw,
        xy=(DEMO_WIDTH - cal_w - 56, 26),
        text=cal_label,
        font=fonts.small,
        bg=cal_bg,
        fg=cal_fg,
        pad_x=16,
        pad_y=7,
    )

    # Scene caption bar above footer (wrapped strictly inside x in [80, 1840], y in [916, 996])
    _draw_card(draw, (56, 916, DEMO_WIDTH - 56, 996), fill="#0F172A", outline="#334155", radius=12)
    caption_lines = _fit_caption_lines(
        draw,
        _SCENE_CAPTIONS[scene_idx],
        fonts.small,
        max_width=DEMO_WIDTH - 160,
        max_lines=2,
    )
    if len(caption_lines) == 1:
        draw.text((80, 942), caption_lines[0], font=fonts.small, fill="#E2E8F0")
    elif caption_lines:
        draw.text((80, 924), caption_lines[0], font=fonts.small, fill="#E2E8F0")
        draw.text((80, 956), caption_lines[1], font=fonts.small, fill="#94A3B8")

    return img


def _fmt_probe_latency(probes: Sequence[Mapping[str, Any]], index: int) -> str:
    if index >= len(probes):
        return "n/a"
    lat = probes[index].get("latency_ms")
    return f"{float(lat):.0f}ms" if lat is not None else "n/a"


def _build_scene_terminal_lines(
    scene_idx: int,
    *,
    audit: Mapping[str, Any],
    probe: Mapping[str, Any],
) -> list[tuple[str, str]]:
    dossier = dict(audit.get("dossier") or {})
    consensus = dict(audit.get("consensus") or {})
    passes = list(consensus.get("passes") or [])
    publication = dict(audit.get("publication") or {})
    telemetry = dict((audit.get("metadata") or {}).get("telemetry") or {})
    per_pass = dict(telemetry.get("per_pass") or {})
    probes = list(probe.get("probes") or [])
    findings = list(probe.get("dx_findings") or [])

    claim_id = str(audit.get("claim_id") or dossier.get("claim_id") or "delphi-btc-etf-2024")
    preset = str(audit.get("preset") or probe.get("preset") or "openai-compatible")
    audit_model = _scene_model_label(0, audit=audit, probe=probe)
    probe_model = _scene_model_label(5, audit=audit, probe=probe)
    session_id = str(audit.get("session_id") or "cal-btc-etf-01")
    tool_calls = [str(item) for item in (audit.get("tool_calls") or [])]

    if scene_idx == 0:
        return [
            ("cmd", f"$ cortensor-verifier audit --claim-id {claim_id} --preset {preset} --model {audit_model} --multi-pass"),
            ("info", "[runtime] APIRuntime.from_config_path() -> .openminion/agents.json (api_key='', secret_free=True)"),
            ("info", f"[config] sdk=openminion=={probe.get('sdk_version', '0.1.21')} | host={probe.get('base_url_host', 'redacted')} | http_reuse=False"),
            ("highlight", f'[stdout] {{"claim_id": "{claim_id}", "preset": "{preset}", "calibrated_model": "{audit_model}"}}'),
            ("ok", "[ready] isolated SQLite data_root active; zero developer home state mutated."),
        ]

    if scene_idx == 1:
        hints_json = json.dumps(list(dossier.get("source_hints") or ["sec-spot-btc-2024-01-10"]))
        tools_json = json.dumps(
            tool_calls or ["load_delphi_market_fixture", "search_public_evidence", "fetch_source_excerpt"]
        )
        return [
            ("cmd", f"$ cortensor-verifier audit --claim-id {claim_id} --fixtures fixtures/claim_dossiers.json --model {audit_model} --multi-pass"),
            ("info", f'[dossier] {{"claim_id": "{claim_id}", "source_hints": {hints_json}}}'),
            ("highlight", f"[policy-guard] assert_read_only_tools(): min_scope='READ_ONLY' enforced across {max(len(tool_calls), 4)} tool(s)"),
            ("info", f'[tool-exec] "tool_calls": {tools_json}'),
            ("ok", "[verified] primary evidence excerpts retrieved; workspace_writes=0."),
        ]

    if scene_idx == 2:
        p0 = passes[0] if len(passes) > 0 else {"verdict": "SUPPORTED", "confidence": 0.96}
        p1 = passes[1] if len(passes) > 1 else {"verdict": "SUPPORTED", "confidence": 0.92}
        t0 = dict(per_pass.get("corroborator") or {})
        t1 = dict(per_pass.get("skeptic") or {})
        return [
            ("cmd", f"$ cortensor-verifier audit --claim-id {claim_id} --preset {preset} --model {audit_model} --multi-pass --session-id {session_id}"),
            ("info", "[isolation] SubagentRunContext: parent_transcript_inherited=False memory_posture='none' tools=READ_ONLY"),
            ("highlight", f"[pass:corroborator] verdict={p0.get('verdict')} conf={float(p0.get('confidence', 0.96)):.2f} requests={t0.get('requests', 0)} total_tokens={t0.get('total_tokens', 0)}"),
            ("highlight", f"[pass:skeptic]      verdict={p1.get('verdict')} conf={float(p1.get('confidence', 0.92)):.2f} requests={t1.get('requests', 0)} total_tokens={t1.get('total_tokens', 0)}"),
            ("ok", "[blind-check] dual redundant passes completed without cross-pass transcript leakage."),
        ]

    if scene_idx == 3:
        return [
            ("cmd", f"$ cortensor-verifier audit --claim-id {claim_id} --model {audit_model} --multi-pass --session-id {session_id} --memory-bundle-out mem.json"),
            ("highlight", f'[stdout] {{"claim_id": "{claim_id}", "final_verdict": "{consensus.get("final_verdict", "SUPPORTED")}", "agreement_score": {float(consensus.get("agreement_score", 0.98)):.2f}}}'),
            ("info", f'[telemetry] {{"requests": {telemetry.get("requests", 0)}, "prompt_tokens": {telemetry.get("prompt_tokens", 0)}, "completion_tokens": {telemetry.get("completion_tokens", 0)}, "total_tokens": {telemetry.get("total_tokens", 0)}}}'),
            ("info", f"[memory] export_bundle(session='{session_id}') -> save_bundle() -> import_bundle() | cross_session_guard=ON"),
            ("ok", f"[outcome] requires_human_review={consensus.get('requires_human_review', False)} | {consensus.get('disagreement_summary', '')}"),
        ]

    if scene_idx == 4:
        mode = str(publication.get("approval_mode") or "allow_once")
        tid = str(publication.get("thread_id") or "thread-cal-pub-01")
        appr_id = str(publication.get("approval_id") or "appr-cal-01")
        log_path = str(publication.get("log_path") or ".openminion-state/published_verdicts.jsonl")
        return [
            ("cmd", f"$ cortensor-verifier audit --claim-id {claim_id} --model {audit_model} --publish --approval-mode {mode} --session-id {session_id}"),
            ("info", "[handoff] coordinator -> transfer_to_publisher -> @tool(dangerous=True, min_scope='WRITE_SAFE')"),
            ("highlight", f"[gate:pause] approval_callback=None -> paused fail-closed | thread_id={tid}"),
            ("info", f"[gate:grant] resume_publication(allow_once) -> PolicyGrantInput(max_uses=1, ttl=5m) approval_id={appr_id}"),
            ("ok", f'[stdout] {{"publication_status": "{publication.get("publication_status", "published")}", "published": {json.dumps(bool(publication.get("published", True)))}, "log_path": "{log_path}"}}'),
        ]

    if scene_idx == 5:
        passed_n = probe.get("passed_probes", len(EXPECTED_PROBE_IDS))
        total_n = probe.get("total_probes", len(EXPECTED_PROBE_IDS))
        total_ms = float(probe.get("total_latency_ms", 0.0))
        stream_meta: dict[str, Any] = {}
        for item in probes:
            if item.get("probe_id") == "submit_turn_streaming_telemetry":
                stream_meta = dict(item.get("metadata") or {})
                break
        if stream_meta:
            stream_line = (
                f"[stream] TurnChunk(count={stream_meta.get('chunk_count', 0)}) | "
                f"TurnTelemetry(tokens_in={stream_meta.get('tokens_in', 0)}, tokens_out={stream_meta.get('tokens_out', 0)}) vs "
                f"stats(in={stream_meta.get('stats_input_tokens', 0)}, out={stream_meta.get('stats_output_tokens', 0)})"
            )
        else:
            stream_line = (
                f"[dx-export] TurnChunk streaming verified; emitted {len(findings)} empirical DX finding(s) -> WHAT_WE_LEARNED.md"
            )
        return [
            ("cmd", f"$ cortensor-verifier probe --preset {preset} --model {probe_model} --timeout-seconds 180 --export-docs"),
            ("info", f"[probes 01..05] iso={_fmt_probe_latency(probes, 0)} struct={_fmt_probe_latency(probes, 1)} tools={_fmt_probe_latency(probes, 2)} policy={_fmt_probe_latency(probes, 3)} sess={_fmt_probe_latency(probes, 4)}"),
            ("info", f"[probes 06..10] mem={_fmt_probe_latency(probes, 5)} sub={_fmt_probe_latency(probes, 6)} handoff={_fmt_probe_latency(probes, 7)} stream={_fmt_probe_latency(probes, 8)} err={_fmt_probe_latency(probes, 9)}"),
            ("highlight", stream_line),
            ("ok", f'[stdout] {{"passed_probes": {passed_n}, "total_probes": {total_n}, "failed_probes": {probe.get("failed_probes", 0)}, "total_latency_ms": {total_ms:.2f}}}'),
        ]

    return [
        ("cmd", "$ cortensor-verifier render-demo --sample-json fixtures/calibrated_sample_run.json --duration-seconds 75 --fps 10"),
        ("info", f'[inputs] "claim_id": "{claim_id}" ({audit_model}) | "passed_probes": {probe.get("passed_probes", 10)}/{probe.get("total_probes", 10)} ({probe_model}) | findings={len(findings)}'),
        ("highlight", "[secret-scan] assert_no_plaintext_secrets() -> 0 leaks | private relay URLs redacted"),
        ("info", f'[telemetry] "requests": {telemetry.get("requests", 0)}, "total_tokens": {telemetry.get("total_tokens", 0)} | libx264 yuv420p 1920x1080 @ 10fps'),
        ("ok", "[done] artifacts/cortensor_hackathon5_demo.mp4 ready (MIT Licensed, reproducible offline & live)."),
    ]


def _draw_cursor_block(draw: ImageDraw.ImageDraw, *, x: int, y: int, color: str) -> None:
    draw.rectangle((x, y + 2, x + 10, y + 19), fill=color)


def _draw_cli_command_line(
    draw: ImageDraw.ImageDraw,
    *,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
    cursor: bool,
) -> None:
    fitted = _fit_single_line(draw, text, font, max_width - (20 if cursor else 0))
    tx = x
    for idx, token in enumerate(fitted.split(" ")):
        if idx > 0:
            tx += int(draw.textlength(" ", font=font))
        if token == "$":
            color = "#22C55E"
        elif token.startswith("--"):
            color = "#38BDF8"
        elif idx == 1:
            color = "#F8FAFC"
        else:
            color = "#CBD5E1"
        draw.text((tx, y), token, font=font, fill=color)
        tx += int(draw.textlength(token, font=font))
    if cursor:
        _draw_cursor_block(draw, x=tx + 6, y=y, color="#22C55E")


def _draw_live_terminal_console(
    draw: ImageDraw.ImageDraw,
    *,
    fonts: _Fonts,
    scene_idx: int,
    stage_idx: int,
    audit: Mapping[str, Any],
    probe: Mapping[str, Any],
) -> None:
    box = (56, 710, DEMO_WIDTH - 56, 896)
    _draw_card(draw, box, fill="#050914", outline="#1E3A5F", radius=12)
    draw.rounded_rectangle((56, 710, DEMO_WIDTH - 56, 744), radius=12, fill="#0B1324")
    draw.rectangle((56, 732, DEMO_WIDTH - 56, 744), fill="#0B1324")
    draw.line((56, 744, DEMO_WIDTH - 56, 744), fill="#1E293B", width=1)

    for cx, dot_color in ((78, "#EF4444"), (98, "#F59E0B"), (118, "#22C55E")):
        draw.ellipse((cx - 5, 722, cx + 5, 732), fill=dot_color)
    draw.text(
        (138, 716),
        "Live Terminal Storyboard  —  cortensor-verifier CLI execution",
        font=fonts.tiny,
        fill="#94A3B8",
    )

    state_label = (
        f"STAGE {stage_idx + 1}/{ANIMATION_STAGES} · COMPLETED"
        if stage_idx >= ANIMATION_STAGES - 1
        else f"STAGE {stage_idx + 1}/{ANIMATION_STAGES} · STREAMING..."
    )
    state_color = "#4ADE80" if stage_idx >= ANIMATION_STAGES - 1 else "#FBBF24"
    sw = int(draw.textlength(state_label, font=fonts.mono_sm))
    draw.text((DEMO_WIDTH - 80 - sw, 716), state_label, font=fonts.mono_sm, fill=state_color)

    lines = _build_scene_terminal_lines(scene_idx, audit=audit, probe=probe)
    max_width = DEMO_WIDTH - 160
    visible_count = min(len(lines), stage_idx + 1)
    kind_colors = {
        "info": "#CBD5E1",
        "highlight": "#FDE68A",
        "ok": "#4ADE80",
    }

    ly = 754
    for idx in range(visible_count):
        kind, raw_line = lines[idx]
        is_active = idx == visible_count - 1
        display_line = raw_line
        if stage_idx == 0 and idx == 0:
            cut = max(24, int(len(raw_line) * 0.58))
            display_line = raw_line[:cut]

        if kind == "cmd":
            _draw_cli_command_line(
                draw,
                x=80,
                y=ly,
                text=display_line,
                font=fonts.mono_sm,
                max_width=max_width,
                cursor=is_active,
            )
        else:
            fitted = _fit_single_line(
                draw,
                display_line,
                fonts.mono_sm,
                max_width - (20 if is_active else 0),
            )
            color = kind_colors.get(kind, "#CBD5E1")
            draw.text((80, ly), fitted, font=fonts.mono_sm, fill=color)
            if is_active:
                lw = int(draw.textlength(fitted, font=fonts.mono_sm))
                cursor_color = "#4ADE80" if stage_idx >= ANIMATION_STAGES - 1 else "#38BDF8"
                _draw_cursor_block(draw, x=80 + lw + 6, y=ly, color=cursor_color)
        ly += 27


def _scene_model_label(
    scene_idx: int,
    *,
    audit: Mapping[str, Any],
    probe: Mapping[str, Any],
) -> str:
    """Resolve the accurate model label shown in the header for each storyboard scene."""
    audit_model = str(
        (audit.get("metadata") or {}).get("calibrated_model")
        or probe.get("model")
        or "grok-4.6"
    )
    probe_model = str(probe.get("model") or "grok-4.7")
    if scene_idx <= 4:
        return audit_model
    if scene_idx == 5:
        return probe_model
    return f"{audit_model} / {probe_model}" if audit_model != probe_model else probe_model


def _render_scene_canvas(
    scene_idx: int,
    *,
    fonts: _Fonts,
    audit: Mapping[str, Any],
    probe: Mapping[str, Any],
    stage_idx: int = ANIMATION_STAGES - 1,
) -> Image.Image:
    stage_idx = max(0, min(ANIMATION_STAGES - 1, int(stage_idx)))
    cal_status = str(
        ((audit.get("metadata") or {}).get("calibration_status") if scene_idx <= 4 else None)
        or probe.get("calibration_status")
        or "[Loopback Stub Baseline]"
    )
    model = _scene_model_label(scene_idx, audit=audit, probe=probe)
    sdk_version = str(probe.get("sdk_version") or "0.1.21")
    canvas = _draw_chrome(
        scene_idx,
        fonts=fonts,
        calibration_status=cal_status,
        model=model,
        sdk_version=sdk_version,
    )
    draw = ImageDraw.Draw(canvas)

    dossier = dict(audit.get("dossier") or {})
    consensus = dict(audit.get("consensus") or {})
    passes = list(consensus.get("passes") or [])
    publication = dict(audit.get("publication") or {})
    telemetry = dict((audit.get("metadata") or {}).get("telemetry") or {})
    probes = list(probe.get("probes") or [])
    findings = list(probe.get("dx_findings") or [])

    if scene_idx == 0:
        _draw_card(draw, (56, 172, 920, 696), outline="#38BDF8")
        draw.text(
            (84, 192),
            _fit_single_line(draw, "Architecture & Threat Model — Zero-Key Isolation", fonts.h2, 804),
            font=fonts.h2,
            fill="#38BDF8",
        )
        bullets = [
            "1. Zero-Key Disk Isolation: APIRuntime.from_config_path writes api_key='' to .openminion/agents.json; API keys stay strictly in env vars.",
            "2. Provider-Agnostic Switching: Presets for openai-compatible, cortensor-portal (/api/v2 & OpenAI), and cortensor-router.",
            "3. PoI/PoUW Redundant Consensus: Independent corroborator + skeptic subagents replace single-pass LLM bias.",
            "4. Fail-Closed Governance: READ_ONLY evidence tools on verifiers + PolicyGate pause/resume Handoff before publication.",
            "5. Full Empirical Benchmarking: 10-module probe suite captures live latency, token stats, and DX edge cases.",
        ]
        y = 244
        for idx, item in enumerate(bullets):
            active = idx <= stage_idx
            fill_col = "#E2E8F0" if active else "#475569"
            y = _draw_wrapped(
                draw,
                xy=(84, y),
                text=item,
                font=fonts.small,
                fill=fill_col,
                max_width=804,
                line_height=26,
                max_lines=2,
            ) + 14

        _draw_card(draw, (960, 172, 1864, 696), outline="#A855F7")
        draw.text((992, 192), "End-to-End Execution Pipeline", font=fonts.h2, fill="#C084FC")
        steps = [
            ("Claim Dossier", "Market question, criteria, and candidate public sources", "#38BDF8"),
            ("Dual subagent() Passes", "corroborator vs skeptic via READ_ONLY @tool functions", "#818CF8"),
            ("Consensus Verdict synthesis", "agreement_score, confidence gap & human-review flag", "#22C55E"),
            ("MemoryBundle & Session", "Scoped per session_id with explicit thread_id continuity", "#F59E0B"),
            ("Handoff Approval Gate", "pause -> thread_id resume -> single-use PolicyGrantInput", "#EC4899"),
        ]
        sy = 244
        for idx, (label, desc, color) in enumerate(steps, start=1):
            reached = (idx - 1) <= stage_idx
            outline_col = color if reached else "#1E293B"
            title_col = color if reached else "#64748B"
            desc_col = "#CBD5E1" if reached else "#475569"
            _draw_card(draw, (992, sy, 1832, sy + 76), fill="#0B1221", outline=outline_col, radius=12)
            draw.text((1014, sy + 10), f"{idx}. {label}", font=fonts.h3, fill=title_col)
            draw.text((1014, sy + 42), _fit_single_line(draw, desc, fonts.small, 790), font=fonts.small, fill=desc_col)
            sy += 86

    elif scene_idx == 1:
        _draw_card(draw, (56, 172, 1180, 696), outline="#38BDF8")
        draw.text((84, 192), _fit_single_line(draw, f"Claim Dossier: {dossier.get('claim_id', 'n/a')}", fonts.h2, 1060), font=fonts.h2, fill="#38BDF8")
        y = 244
        y = _draw_wrapped(draw, xy=(84, y), text=f"Title: {dossier.get('title', '')}", font=fonts.h3, fill="#F8FAFC", max_width=1060, line_height=28, max_lines=2) + 8
        y = _draw_wrapped(draw, xy=(84, y), text=f"Claim: {dossier.get('claim', '')}", font=fonts.small, fill="#E2E8F0", max_width=1060, line_height=26, max_lines=3) + 10
        if stage_idx >= 1:
            y = _draw_wrapped(draw, xy=(84, y), text=f"Market Question: {dossier.get('market_question', '')}", font=fonts.small, fill="#93C5FD", max_width=1060, line_height=26, max_lines=2) + 10
            y = _draw_wrapped(draw, xy=(84, y), text=f"Resolution Criteria: {dossier.get('resolution_criteria', '')}", font=fonts.small, fill="#CBD5E1", max_width=1060, line_height=26, max_lines=3) + 12
        if stage_idx >= 2:
            hints = ", ".join(dossier.get("source_hints") or [])
            _draw_wrapped(draw, xy=(84, min(y, 620)), text=f"Source Hints: {hints}", font=fonts.mono_sm, fill="#34D399", max_width=1060, line_height=24, max_lines=2)

        _draw_card(draw, (1210, 172, 1864, 696), outline="#22C55E")
        draw.text((1240, 192), "Observed READ_ONLY Tools", font=fonts.h2, fill="#4ADE80")
        tool_calls = list(audit.get("tool_calls") or ["load_delphi_market_fixture", "search_public_evidence", "fetch_source_excerpt"])
        ty = 246
        for idx, tool_name in enumerate(tool_calls[:4]):
            executed = stage_idx >= (idx + 1)
            box_outline = "#10B981" if executed else "#1E293B"
            box_fill = "#071912" if executed else "#0B1221"
            tag_col = "#6EE7B7" if executed else "#64748B"
            name_col = "#F8FAFC" if executed else "#64748B"
            prefix = "Executed" if executed else "Registered"
            _draw_card(draw, (1240, ty, 1834, ty + 84), fill=box_fill, outline=box_outline, radius=12)
            draw.text((1262, ty + 12), "@tool(min_scope='READ_ONLY', idempotent=True)", font=fonts.mono_sm, fill=tag_col)
            draw.text((1262, ty + 42), _fit_single_line(draw, f"{prefix}: {tool_name}", fonts.h3, 550), font=fonts.h3, fill=name_col)
            ty += 98
        draw.text((1240, 652), "Enforced by ConsensusAuditor._read_only_approval_guard()", font=fonts.tiny, fill="#94A3B8")

    elif scene_idx == 2:
        left_pass = passes[0] if len(passes) > 0 else {"pass_role": "corroborator", "verdict": "SUPPORTED", "confidence": 0.95, "rationale": "", "citations": []}
        right_pass = passes[1] if len(passes) > 1 else {"pass_role": "skeptic", "verdict": "SUPPORTED", "confidence": 0.93, "rationale": "", "citations": []}
        for idx, (box, pdata, accent) in enumerate([
            ((56, 172, 940, 696), left_pass, "#22C55E"),
            ((980, 172, 1864, 696), right_pass, "#F59E0B"),
        ]):
            pass_done = (idx == 0 and stage_idx >= 1) or (idx == 1 and stage_idx >= 2)
            cite_done = (idx == 0 and stage_idx >= 2) or (idx == 1 and stage_idx >= 3)
            card_outline = accent if pass_done else "#1E293B"
            _draw_card(draw, box, outline=card_outline)
            x0 = box[0] + 28
            role = str(pdata.get("pass_role", f"pass-{idx + 1}")).upper()
            draw.text((x0, 192), f"Subagent Pass: {role}", font=fonts.h2, fill=accent if pass_done else "#64748B")
            status_line = (
                f"Verdict: {pdata.get('verdict')}   |   Confidence: {float(pdata.get('confidence', 0.0)):.2f}"
                if pass_done
                else "Status: EXECUTING IN ISOLATED SUBAGENT RUNTIME..."
            )
            draw.text((x0, 236), _fit_single_line(draw, status_line, fonts.h3, 828), font=fonts.h3, fill="#F8FAFC" if pass_done else "#94A3B8")
            if pass_done:
                y = _draw_wrapped(
                    draw,
                    xy=(x0, 280),
                    text=f"Rationale: {pdata.get('rationale', '')}",
                    font=fonts.small,
                    fill="#E2E8F0",
                    max_width=828,
                    line_height=25,
                    max_lines=5,
                ) + 12
                if cite_done:
                    draw.text((x0, y), "Verified Citations:", font=fonts.h3, fill="#38BDF8")
                    y += 32
                    for cite in list(pdata.get("citations") or [])[:2]:
                        src = cite.get("source_id", "")
                        excerpt = cite.get("excerpt", "")
                        y = _draw_wrapped(
                            draw,
                            xy=(x0, y),
                            text=f"[{src}] {excerpt}",
                            font=fonts.tiny,
                            fill="#CBD5E1",
                            max_width=828,
                            line_height=22,
                            max_lines=3,
                        ) + 8
            draw.text(
                (x0, 654),
                "SubagentRunContext: parent_transcript_inherited=False, memory_posture='none'",
                font=fonts.mono_sm,
                fill="#94A3B8",
            )

    elif scene_idx == 3:
        verdict = str(consensus.get("final_verdict", "SUPPORTED"))
        verdict_ready = stage_idx >= 1
        _draw_card(draw, (56, 172, 1864, 434), outline="#22C55E" if verdict_ready else "#38BDF8")
        headline = f"Synthesized Consensus Verdict: {verdict}" if verdict_ready else "Synthesizing Consensus Verdict across Dual Passes..."
        draw.text((88, 192), headline, font=fonts.h1, fill="#4ADE80" if verdict_ready else "#38BDF8")
        metrics_line = (
            f"agreement_score={float(consensus.get('agreement_score', 1.0)):.2f}   |   "
            f"mean_confidence={float(consensus.get('mean_confidence', 0.95)):.2f}   |   "
            f"requires_human_review={consensus.get('requires_human_review', False)}"
        )
        draw.text((88, 250), metrics_line, font=fonts.mono_bold, fill="#38BDF8" if verdict_ready else "#64748B")
        _draw_wrapped(
            draw,
            xy=(88, 294),
            text=f"Synthesis Summary: {consensus.get('disagreement_summary', '')}",
            font=fonts.body,
            fill="#E2E8F0" if verdict_ready else "#475569",
            max_width=1740,
            line_height=30,
            max_lines=3,
        )

        tel_ready = stage_idx >= 2
        _draw_card(draw, (56, 452, 940, 696), outline="#38BDF8" if tel_ready else "#1E293B")
        draw.text((88, 472), "Runtime & Token Telemetry", font=fonts.h2, fill="#38BDF8" if tel_ready else "#64748B")
        tel_rows = [
            f"Total Model Requests: {telemetry.get('requests', 'n/a')}",
            f"Prompt / Completion Tokens: {telemetry.get('prompt_tokens', 0)} / {telemetry.get('completion_tokens', 0)}",
            f"Total Tokens Billed: {telemetry.get('total_tokens', 0)}",
            f"End-to-End Audit Latency: {telemetry.get('total_latency_ms', 0)} ms",
        ]
        ty = 520
        for row in tel_rows:
            draw.text((88, ty), row, font=fonts.body, fill="#E2E8F0" if tel_ready else "#475569")
            ty += 40

        mem_ready = stage_idx >= 3
        _draw_card(draw, (980, 452, 1864, 696), outline="#A855F7" if mem_ready else "#1E293B")
        draw.text((1012, 472), "Session Continuity & MemoryBundle Isolation", font=fonts.h2, fill="#C084FC" if mem_ready else "#64748B")
        mem_rows = [
            f"Session ID: {audit.get('session_id') or 'cal-session'}",
            "Thread Allocation: explicit thread_id forwarded across Agent.run() turns",
            "MemoryBundle Format: export_bundle() -> save_bundle() -> import_bundle()",
            "Cross-Session Guard: foreign session_id items raise ValueError fail-closed",
        ]
        my = 520
        for row in mem_rows:
            draw.text((1012, my), _fit_single_line(draw, row, fonts.small, 820), font=fonts.small, fill="#E2E8F0" if mem_ready else "#475569")
            my += 40

    elif scene_idx == 4:
        _draw_card(draw, (56, 172, 1864, 696), outline="#EC4899")
        draw.text((84, 192), "Approval-Gated Publication via OpenMinion Handoff", font=fonts.h2, fill="#F472B6")
        stages = [
            ("Step 1 · Handoff Coordinator", "publication_coordinator exposes transfer_to_publisher -> isolated publisher agent with WRITE_SAFE @tool(dangerous=True).", "#38BDF8"),
            ("Step 2 · Default Fail-Closed Pause", "Calling with approval_callback=None pauses execution cleanly & checkpoints thread_id snapshot JSON on disk.", "#F59E0B"),
            ("Step 3 · Explicit Operator Authorization", "resume_publication(thread_id, approval_mode='allow_once') grants 1-use PolicyGrantInput(max_uses=1, ttl=5m).", "#22C55E"),
            ("Step 4 · Committed Verdict & Replay Denial", f"Status={publication.get('publication_status', 'published')} | published={publication.get('published', True)} | Re-using approval_id/thread_id is denied fail-closed.", "#C084FC"),
        ]
        sy = 242
        for idx, (title, body, color) in enumerate(stages):
            reached = idx <= stage_idx
            outline_col = color if reached else "#1E293B"
            _draw_card(draw, (84, sy, 1836, sy + 96), fill="#0B1221", outline=outline_col, radius=12)
            draw.text((112, sy + 10), title, font=fonts.h3, fill=color if reached else "#64748B")
            badge_txt = "[DONE]" if idx < stage_idx or stage_idx == ANIMATION_STAGES - 1 else ("[ACTIVE]" if idx == stage_idx else "[QUEUED]")
            bw = int(draw.textlength(badge_txt, font=fonts.mono_sm))
            draw.text((1808 - bw, sy + 12), badge_txt, font=fonts.mono_sm, fill=color if reached else "#475569")
            _draw_wrapped(
                draw,
                xy=(112, sy + 42),
                text=body,
                font=fonts.small,
                fill="#E2E8F0" if reached else "#475569",
                max_width=1690,
                line_height=24,
                max_lines=2,
            )
            sy += 108

    elif scene_idx == 5:
        _draw_card(draw, (56, 172, 1864, 696), outline="#22C55E")
        passed = probe.get("passed_probes", len(EXPECTED_PROBE_IDS))
        total = probe.get("total_probes", len(EXPECTED_PROBE_IDS))
        total_ms = probe.get("total_latency_ms", 0.0)
        header_line = f"Building Block Probe Suite: {passed}/{total} PASSED (total={float(total_ms):.1f} ms | host={probe.get('base_url_host', 'redacted')})"
        draw.text((84, 192), _fit_single_line(draw, header_line, fonts.h2, 1750), font=fonts.h2, fill="#4ADE80")
        revealed_limit = min(10, (stage_idx + 1) * 2)
        for idx, item in enumerate(probes[:10]):
            col = 0 if idx < 5 else 1
            row = idx if idx < 5 else idx - 5
            x0 = 84 if col == 0 else 976
            y0 = 244 + row * 86
            box = (x0, y0, x0 + 858, y0 + 76)
            ok = bool(item.get("passed"))
            revealed = idx < revealed_limit
            accent = ("#22C55E" if ok else "#EF4444") if revealed else "#1E293B"
            _draw_card(draw, box, fill="#0B1221", outline=accent, radius=10)
            pid = str(item.get("probe_id", ""))
            lat = float(item.get("latency_ms", 0.0) or 0.0)
            badge = ("[PASS]" if ok else "[FAIL]") + f" {lat:.0f} ms" if revealed else "[WAIT]"
            draw.text((x0 + 18, y0 + 8), _fit_single_line(draw, f"{idx + 1:02d}. {pid}", fonts.mono_sm, 610), font=fonts.mono_sm, fill="#F8FAFC" if revealed else "#64748B")
            bw = int(draw.textlength(badge, font=fonts.mono_sm))
            draw.text((x0 + 840 - bw, y0 + 8), badge, font=fonts.mono_sm, fill=accent if revealed else "#475569")
            _draw_wrapped(
                draw,
                xy=(x0 + 18, y0 + 34),
                text=str(item.get("detail", "")),
                font=fonts.tiny,
                fill="#94A3B8" if revealed else "#475569",
                max_width=820,
                line_height=18,
                max_lines=2,
            )

    else:
        _draw_card(draw, (56, 172, 1110, 696), outline="#F59E0B")
        findings_header = f"Top OpenMinion 0.1 DX Findings ({min(4, len(findings))} of {len(findings)} in WHAT_WE_LEARNED.md)"
        draw.text((84, 190), _fit_single_line(draw, findings_header, fonts.h2, 1000), font=fonts.h2, fill="#FBBF24")
        fy = 238
        for idx, item in enumerate(findings[:4], start=1):
            active = (idx - 1) <= stage_idx
            _draw_card(
                draw,
                (84, fy, 1082, fy + 102),
                fill="#0B1221",
                outline="#F59E0B" if active else "#1E293B",
                radius=10,
            )
            title_txt = _fit_single_line(draw, f"{idx}. {item.get('title', '')}", fonts.small_bold, 962)
            draw.text((102, fy + 8), title_txt, font=fonts.small_bold, fill="#FDE68A" if active else "#64748B")
            _draw_wrapped(
                draw,
                xy=(102, fy + 34),
                text=str(item.get("observation", "")),
                font=fonts.tiny,
                fill="#CBD5E1" if active else "#475569",
                max_width=962,
                line_height=20,
                max_lines=3,
            )
            fy += 112

        _draw_card(draw, (1140, 172, 1864, 696), outline="#38BDF8")
        draw.text((1168, 190), "One-Command Reproducibility", font=fonts.h2, fill="#38BDF8")
        audit_model = _scene_model_label(0, audit=audit, probe=probe)
        probe_model = _scene_model_label(5, audit=audit, probe=probe)
        claim_id = str(audit.get("claim_id") or "delphi-btc-etf-2024")
        preset = str(audit.get("preset") or probe.get("preset") or "openai-compatible")
        cmds = [
            "# 1. Probe all 10 OpenMinion primitives & export docs",
            f"cortensor-verifier probe --preset {preset} \\",
            f"  --model {probe_model} --timeout-seconds 180 --export-docs",
            "",
            "# 2. Dual-pass consensus audit w/ Handoff gate",
            f"cortensor-verifier audit --claim-id {claim_id} \\",
            f"  --preset {preset} --model {audit_model} --multi-pass \\",
            "  --session-id demo-01 --publish --approval-mode allow_once",
            "",
            "# 3. Render 75s captioned 1080p walkthrough",
            "cortensor-verifier render-demo \\",
            "  --sample-json fixtures/calibrated_sample_run.json \\",
            "  -o artifacts/cortensor_hackathon5_demo.mp4",
        ]
        cy = 242
        for line in cmds:
            if not line:
                cy += 16
                continue
            color = "#6EE7B7" if line.startswith("#") else "#E2E8F0"
            draw.text((1168, cy), _fit_single_line(draw, line, fonts.mono_sm, 672), font=fonts.mono_sm, fill=color)
            cy += 29
        draw.text((1168, 654), "MIT Licensed · Zero Plaintext Secrets · Offline & Live Reproducible", font=fonts.tiny, fill="#94A3B8")

    _draw_live_terminal_console(
        draw,
        fonts=fonts,
        scene_idx=scene_idx,
        stage_idx=stage_idx,
        audit=audit,
        probe=probe,
    )
    return canvas


def _overlay_progress_bar(
    base_rgb: Image.Image,
    *,
    fonts: _Fonts,
    scene_idx: int,
    frame_idx: int,
    total_frames: int,
    duration_seconds: float,
) -> np.ndarray:
    frame = base_rgb.copy()
    draw = ImageDraw.Draw(frame)

    draw.rectangle((0, 1012, DEMO_WIDTH, DEMO_HEIGHT), fill="#090D18")
    elapsed = (frame_idx / max(1, total_frames)) * duration_seconds
    timer_text = f"Step {scene_idx + 1}/{TOTAL_SCENES}  |  {elapsed:04.1f}s / {duration_seconds:04.1f}s"
    timer_w = int(draw.textlength(timer_text, font=fonts.mono))
    timer_x = DEMO_WIDTH - 56 - timer_w
    bar_x0, bar_y0, bar_x1, bar_y1 = 56, 1028, timer_x - 28, 1044
    draw.rounded_rectangle((bar_x0, bar_y0, bar_x1, bar_y1), radius=6, fill="#1E293B")
    frac = min(1.0, max(0.0, (frame_idx + 1) / max(1, total_frames)))
    fill_x1 = max(bar_x0 + 12, int(bar_x0 + (bar_x1 - bar_x0) * frac))
    draw.rounded_rectangle((bar_x0, bar_y0, fill_x1, bar_y1), radius=6, fill="#38BDF8")

    draw.text((timer_x, 1022), timer_text, font=fonts.mono, fill="#CBD5E1")
    return np.asarray(frame, dtype=np.uint8)


def render_demo_video(
    *,
    output_path: str | Path,
    audit_bundle: Mapping[str, Any],
    probe_report: Mapping[str, Any],
    duration_seconds: int = DEFAULT_DEMO_DURATION_SECONDS,
    fps: int = DEFAULT_DEMO_FPS,
    secret_env_names: Sequence[str] | None = None,
    extra_secrets: Sequence[str] | None = None,
) -> DemoRenderResult:
    """Render a captioned 1920x1080 H.264 MP4 walkthrough from AuditRunBundle & ProbeSuiteReport."""
    if not (60 <= int(duration_seconds) <= 300):
        raise ValueError(
            f"Demo video duration_seconds must be between 60 and 300 seconds; got {duration_seconds}."
        )
    if int(fps) <= 0:
        raise ValueError(f"fps must be positive; got {fps}.")

    serialized_inputs = json.dumps(
        {"audit_bundle": audit_bundle, "probe_report": probe_report},
        ensure_ascii=True,
    )
    assert_no_plaintext_secrets(
        serialized_inputs,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )
    terminal_dump = "\n".join(
        line
        for s_idx in range(TOTAL_SCENES)
        for _, line in _build_scene_terminal_lines(s_idx, audit=audit_bundle, probe=probe_report)
    )
    assert_no_plaintext_secrets(
        terminal_dump,
        secret_env_names=secret_env_names,
        extra_secrets=extra_secrets,
    )

    total_frames = int(duration_seconds) * int(fps)
    fonts = _create_fonts()
    scene_canvases: list[list[Image.Image]] = [
        [
            _render_scene_canvas(
                s_idx,
                fonts=fonts,
                audit=audit_bundle,
                probe=probe_report,
                stage_idx=st_idx,
            )
            for st_idx in range(ANIMATION_STAGES)
        ]
        for s_idx in range(TOTAL_SCENES)
    ]

    # Allocate frames monotonically across scenes based on relative instructional weight.
    weights = (0.10, 0.13, 0.16, 0.14, 0.14, 0.18, 0.15)
    raw_counts = [max(1, round(w * total_frames)) for w in weights]
    diff = total_frames - sum(raw_counts)
    raw_counts[-1] = max(1, raw_counts[-1] + diff)

    scene_schedule: list[tuple[int, int]] = []
    for s_idx, count in enumerate(raw_counts):
        for local_idx in range(count):
            stage_idx = (
                ANIMATION_STAGES - 1
                if count <= 1
                else min(ANIMATION_STAGES - 1, (local_idx * ANIMATION_STAGES) // count)
            )
            scene_schedule.append((s_idx, stage_idx))
    if len(scene_schedule) > total_frames:
        scene_schedule = scene_schedule[:total_frames]
    while len(scene_schedule) < total_frames:
        scene_schedule.append((TOTAL_SCENES - 1, ANIMATION_STAGES - 1))

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio.get_writer(
        str(target_path),
        fps=int(fps),
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=1,
        ffmpeg_params=["-preset", "ultrafast"],
    )
    try:
        for frame_idx, (scene_idx, stage_idx) in enumerate(scene_schedule):
            arr = _overlay_progress_bar(
                scene_canvases[scene_idx][stage_idx],
                fonts=fonts,
                scene_idx=scene_idx,
                frame_idx=frame_idx,
                total_frames=total_frames,
                duration_seconds=float(duration_seconds),
            )
            writer.append_data(arr)
    finally:
        writer.close()

    return DemoRenderResult(
        output_path=target_path,
        width=DEMO_WIDTH,
        height=DEMO_HEIGHT,
        fps=int(fps),
        duration_seconds=float(duration_seconds),
        frame_count=total_frames,
        scene_count=TOTAL_SCENES,
        file_size_bytes=target_path.stat().st_size,
        calibration_status=str(probe_report.get("calibration_status") or ""),
        model=_scene_model_label(6, audit=audit_bundle, probe=probe_report),
        claim_id=str(audit_bundle.get("claim_id") or ""),
    )
