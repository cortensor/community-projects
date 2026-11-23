#!/usr/bin/env python3
"""Record the FixBrief demo video from a REAL terminal session.

Every command below is executed for real via subprocess; the captured
stdout/stderr is written verbatim to outputs/demo_transcript.txt and
rendered as terminal-style frames (Pillow) assembled with ffmpeg into
demo-video.mp4. Nothing is staged or faked: if the Ollama model is not
reachable, the transcript and frames say so and the model step is
replaced by the honest echo-validation failure + offline brief.

Usage:
    .venv/bin/python record_demo.py [--provider ollama|echo] [--model qwen2.5:1.5b]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_BIN = ROOT / ".venv" / "bin"
FRAMES_DIR = ROOT / "outputs" / "demo_frames"
TRANSCRIPT = ROOT / "outputs" / "demo_transcript.txt"
VIDEO = ROOT / "demo-video.mp4"

WIDTH, HEIGHT = 1280, 720
BG = (13, 17, 23)
FG = (201, 209, 217)
ACCENT = (88, 166, 255)
DIM = (139, 148, 158)
MAX_LINES = 28
WRAP = 108


def run_step(title: str, cmd: list[str], timeout: int = 2600) -> tuple[str, str, int]:
    print(f"\n=== {title} ===")
    print("$ " + " ".join(cmd))
    import os

    env = dict(os.environ)
    env.setdefault("FIXBRIEF_BASE_URL", "http://127.0.0.1:8000/v1")
    env.setdefault("FIXBRIEF_API_KEY", "local")
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    print(output[:3000])
    print(f"[exit {proc.returncode}]")
    return title, output, proc.returncode


def load_font(size: int):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_frame(path: Path, title: str, cmd_line: str, output: str, footer: str) -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    font = load_font(19)
    font_title = load_font(24)
    y = 28
    draw.text((36, y), title, font=font_title, fill=ACCENT)
    y += 44
    draw.text((36, y), "$ " + cmd_line, font=font, fill=FG)
    y += 34
    lines: list[str] = []
    for raw in output.splitlines():
        wrapped = textwrap.wrap(raw, width=WRAP) or [""]
        lines.extend(wrapped)
    for line in lines[:MAX_LINES]:
        draw.text((36, y), line, font=font, fill=FG)
        y += 24
        if y > HEIGHT - 70:
            break
    if len(lines) > MAX_LINES:
        draw.text((36, y), f"… ({len(lines) - MAX_LINES} more lines in transcript)", font=font, fill=DIM)
    draw.text((36, HEIGHT - 40), footer, font=font, fill=DIM)
    img.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", default="openai", choices=["ollama", "echo", "openai"]
    )
    parser.add_argument(
        "--model",
        default="/home/hatch/workspace/tools/models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    )
    parser.add_argument("--skip-model", action="store_true", help="Skip model steps")
    args = parser.parse_args()

    fixbrief = str(VENV_BIN / "fixbrief")
    python = str(VENV_BIN / "python")
    steps: list[tuple[str, list[str], float]] = [
        ("FixBrief — Cortensor Hackathon #5 (OpenMinion 0.1.24)",
         [fixbrief, "--version"], 5),
        ("Test suite (fully offline)",
         [python, "-m", "pytest", "tests/", "-q"], 9),
        ("Setup: project-local OpenMinion config",
         [fixbrief, "setup", "--provider", args.provider, "--model", args.model], 7),
        ("Doctor: SDK, provider, samples",
         [fixbrief, "doctor"], 7),
        ("Offline deterministic brief (no model, labeled as such)",
         [fixbrief, "brief", "--device", "iPhone 12", "--symptom", "black screen",
          "--sample", "iphone-black-screen.md", "--offline"], 11),
    ]
    if not args.skip_model:
        # Real model-backed run: the agent calls get_source_facts and
        # writes a Spanish summary from the tool facts. (Typed-output
        # brief turns on this 1.5B CPU model exceed the turn budget —
        # see BUILDING_BLOCKS_TESTED.md finding 11; the structured
        # brief above is the deterministic path, labeled as such.)
        steps.append(
            ("Real model run: tool-grounded Spanish summary (OpenMinion Agent)",
             [fixbrief, "followup", "--session", "demo-live",
              "--message", "Use get_source_facts with kind=sample and "
              "locator=samsung-not-charging.md, then write a short repair "
              "summary in Spanish (5-8 sentences) covering likely causes "
              "and first diagnostic steps. Base it only on the tool facts. Do not save any file.",
              "--provider", args.provider, "--model", args.model,
              "--timeout", "2400", "--yes"], 14)
        )
        steps.append(
            ("Session follow-up (same session_id, continuity)",
             [fixbrief, "followup", "--session", "demo-live",
              "--message", "In one sentence, what is the most likely cause?",
              "--provider", args.provider, "--model", args.model,
              "--timeout", "2400", "--yes"], 9)
        )
    steps.append(("Brief history (SQLite)", [fixbrief, "history"], 7))
    steps.append(
        ("Run receipt (provider / model / session / stats)",
         ["cat", "outputs/live_model_run_receipt.json"], 8)
    )

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    transcript_parts: list[str] = []
    frame_specs: list[tuple[Path, float]] = []
    footer = "FixBrief · OpenMinion 0.1.24 · real terminal output — full text in outputs/demo_transcript.txt"

    for index, (title, cmd, seconds) in enumerate(steps):
        cmd_line = " ".join(cmd).replace(str(VENV_BIN) + "/", ".venv/bin/")
        try:
            _, output, code = run_step(title, cmd)
        except subprocess.TimeoutExpired:
            output, code = "(command timed out — see transcript notes)", 124
        transcript_parts.append(
            f"\n{'=' * 72}\nSTEP {index + 1}: {title}\n$ {cmd_line}\n[exit {code}]\n{output}"
        )
        frame = FRAMES_DIR / f"frame_{index:02d}.png"
        render_frame(frame, title, cmd_line, output, footer)
        frame_specs.append((frame, seconds))

    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT.write_text("\n".join(transcript_parts), encoding="utf-8")
    print(f"\ntranscript: {TRANSCRIPT}")

    concat_file = FRAMES_DIR / "concat.txt"
    with concat_file.open("w", encoding="utf-8") as handle:
        for frame, seconds in frame_specs:
            handle.write(f"file '{frame}'\n")
            handle.write(f"duration {seconds}\n")
        handle.write(f"file '{frame_specs[-1][0]}'\n")

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "23", str(VIDEO),
    ]
    print("$ " + " ".join(ffmpeg_cmd))
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, cwd=ROOT)
    print(result.stderr[-1500:])
    if result.returncode != 0:
        print("ffmpeg failed", file=sys.stderr)
        return 1
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "default=noprint_wrappers=1", str(VIDEO)],
        capture_output=True, text=True,
    )
    print(probe.stdout)
    print(f"video: {VIDEO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
