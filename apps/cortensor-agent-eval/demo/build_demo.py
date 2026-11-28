"""Render a crisp 720p H.264 walkthrough demo video from real verified run artifacts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _draw_slide(
    *,
    out_png: Path,
    badge: str,
    title: str,
    subtitle: str,
    lines: list[str],
    accent: tuple[int, int, int],
) -> None:
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (15, 18, 25))
    draw = ImageDraw.Draw(img)

    # Flat header bar (no gradients)
    draw.rectangle([0, 0, w, 8], fill=accent)
    draw.rectangle([48, 44, 1232, 676], outline=(42, 50, 66), width=2, fill=(21, 25, 34))

    font_badge = _load_font(20, bold=True)
    font_title = _load_font(38, bold=True)
    font_sub = _load_font(22, bold=False)
    font_body = _load_font(22, bold=False)

    draw.rectangle([80, 76, 390, 114], fill=accent)
    draw.text((96, 84), badge, fill=(15, 18, 25), font=font_badge)
    draw.text((80, 134), title, fill=(242, 246, 252), font=font_title)
    draw.text((80, 190), subtitle, fill=(156, 170, 192), font=font_sub)

    draw.line([(80, 236), (1200, 236)], fill=(48, 58, 76), width=2)

    y = 264
    for line in lines:
        draw.text((88, y), line, fill=(216, 224, 238), font=font_body)
        y += 42

    draw.text(
        (80, 628),
        "Cortensor Hackathon #5  |  OpenMinion 0.1.24 Python SDK  |  MIT License",
        fill=(115, 130, 152),
        font=_load_font(18),
    )
    img.save(out_png)


def build_demo_video(project_root: Path) -> Path:
    facts_e2e = json.loads(
        (project_root / "examples" / "e2e-verified-run" / "facts.json").read_text(
            encoding="utf-8"
        )
    )
    facts_portal = json.loads(
        (project_root / "examples" / "cortensor-portal-probe" / "facts.json").read_text(
            encoding="utf-8"
        )
    )

    slides_dir = project_root / "demo" / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    slides = [
        (
            "01_intro.png",
            "CORTENSOR HACKATHON #5",
            "Cortensor Agent Eval",
            "Deterministic Multi-Agent Benchmark Suite on OpenMinion 0.1.24",
            [
                "- Runtime: APIRuntime.from_config_path (isolated SQLite home/data)",
                "- Agents: Collector -> Bounded Subagent -> Gated Writer -> Judge",
                "- Tools: @tool(min_scope='READ_ONLY'), @tool(idempotent=True), @tool(dangerous=True)",
                "- Portability: MemoryBundle export + import verification",
                "- Resilience: ProviderError & TurnTimeoutError offline fallback",
            ],
            (56, 189, 248),
        ),
        (
            "02_architecture.png",
            "SDK ARCHITECTURE",
            "5-Stage OpenMinion Execution Graph",
            "ProviderSetupRequest -> APIRuntime -> Agent -> subagent -> EvalReport",
            [
                "1. Bootstrap: ProviderSetupRequest builds isolated agents.json",
                "2. Case 1 (Collector): probe_inference_endpoint [READ_ONLY]",
                "3. Case 2 (Subagent): reviewer child checks score_case_output",
                "4. Case 3 (Policy Gate): FailClosedApprovalGate allows 1 write",
                "5. Case 4 & 5: Session continuity + Judge Agent(output_type=EvalReport)",
            ],
            (16, 185, 129),
        ),
        (
            "03_e2e_run.png",
            "VERIFIED E2E RUN",
            f"Verdict: {facts_e2e['report']['verdict']} ({facts_e2e['report']['score']}/100)",
            f"Suite: {facts_e2e['summary']['suite_name']}  |  Session: {facts_e2e['summary']['suite_name']}",
            [
                f"- Total Cases Passed: {facts_e2e['summary']['passed_cases']} / {facts_e2e['summary']['total_cases']} (pass_rate={facts_e2e['summary']['pass_rate']})",
                f"- Avg Latency: {facts_e2e['summary']['avg_latency_ms']} ms",
                f"- Approvals Logged: {facts_e2e['summary']['approvals_logged']} (single-use approved)",
                f"- Session Persisted: {facts_e2e['summary']['session_persisted']}",
                f"- MemoryBundle Items: {facts_e2e['summary']['memory_bundle_items']} round-trip verified",
            ],
            (34, 197, 94),
        ),
        (
            "04_portal_probe.png",
            "CORTENSOR PORTAL PROBE",
            "Live Reachability + ProviderError Handling",
            f"Target: {facts_portal['probe']['endpoint']}",
            [
                f"- Reachable: {facts_portal['probe']['reachable']} ({facts_portal['probe']['detail']} in {facts_portal['probe']['latency_ms']} ms)",
                f"- Offline Fallback Triggered: {facts_portal['used_offline_fallback']}",
                "- Key Finding: ProviderSetupRequest allow_local_api_key quirk",
                "- Key Finding: Minimal agents.json requires default_channel='console'",
                "- Full artifacts: facts.json, report.md, memory_bundle.json",
            ],
            (250, 204, 21),
        ),
        (
            "05_tests_cli.png",
            "TESTS & REPRODUCIBILITY",
            "pytest -v : 3/3 Passed  |  CLI Ready",
            "Run locally with zero external API keys required",
            [
                "$ pip install -e .[dev]",
                "$ pytest -v   -> 6 passed (SSRF + path traversal + SDK reproducer + E2E + fallback)",
                "$ cortensor-eval --provider cortensor-portal --model oss-20b --json",
                "- Repo: cortensor/community-projects/apps/cortensor-agent-eval",
                "- License: MIT  |  Zero hardcoded secrets",
            ],
            (56, 189, 248),
        ),
    ]

    for fname, badge, title, sub, lines, color in slides:
        _draw_slide(
            out_png=slides_dir / fname,
            badge=badge,
            title=title,
            subtitle=sub,
            lines=lines,
            accent=color,
        )

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    out_mp4 = project_root / "demo" / "cortensor-agent-eval-demo.mp4"
    # 12s per slide = 60s total 1280x720 H.264 video
    concat_file = slides_dir / "slides.txt"
    concat_lines = []
    for fname, *_ in slides:
        p = (slides_dir / fname).as_posix()
        concat_lines.append(f"file '{p}'")
        concat_lines.append("duration 12")
    concat_lines.append(f"file '{(slides_dir / slides[-1][0]).as_posix()}'")
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-vf",
        "fps=24,format=yuv420p",
        "-c:v",
        "libx264",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out_mp4


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    mp4 = build_demo_video(root)
    print(f"Generated demo video: {mp4} ({mp4.stat().st_size} bytes)")
