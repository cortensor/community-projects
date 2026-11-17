"""Render demo.mp4 from a real Hackathon Scout run log.

The terminal frames replay examples/demo-run.txt (captured from an actual run on
Gemini via OpenMinion), followed by the generated checklist and a summary card.

Usage: python tools/make_demo_video.py
Needs: pillow, imageio-ffmpeg
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1280, 720, 10
BG, FG, DIM, ACC, OK, BAD = "#0d1117", "#e6edf3", "#7d8590", "#f0b429", "#3fb950", "#f85149"
MONO = "C:/Windows/Fonts/consola.ttf"
SANS = "C:/Windows/Fonts/segoeui.ttf"
SANS_B = "C:/Windows/Fonts/segoeuib.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


F_MONO = font(MONO, 17)
F_TITLE = font(SANS_B, 46)
F_SUB = font(SANS, 26)
F_BODY = font(SANS, 24)

frames: list[Image.Image] = []


def hold(img: Image.Image, seconds: float) -> None:
    frames.extend([img] * max(1, int(seconds * FPS)))


def card(title: str, lines: list[str], seconds: float, accent: str = ACC) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=accent)
    d.text((80, 110), title, font=F_TITLE, fill=FG)
    y = 200
    for line in lines:
        for chunk in textwrap.wrap(line, 80) or [""]:
            d.text((80, y), chunk, font=F_BODY, fill=FG if not line.startswith("  ") else DIM)
            y += 38
        y += 6
    d.text((80, H - 60), "Hackathon Scout · OpenMinion 0.1 SDK · Cortensor Hackathon #5", font=F_SUB, fill=DIM)
    hold(img, seconds)


def color_for(line: str) -> str:
    low = line.lower()
    if line.startswith("$"):
        return ACC
    if "skip" in low or "blocker" in low:
        return BAD
    if "| go" in low or ": go" in low or "approval" in low:
        return OK
    if line.startswith("run=") or "[backoff]" in line or "[retry]" in line:
        return DIM
    return FG


def terminal(lines: list[str], title: str, per_line: float = 0.6, end_hold: float = 3.0) -> None:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, 118, subsequent_indent="    ") or [""])
    shown: list[str] = []
    for line in wrapped:
        shown.append(line)
        view = shown[-30:]
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 34], fill="#161b22")
        for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
            d.ellipse([16 + i * 22, 11, 28 + i * 22, 23], fill=c)
        d.text((100, 7), title, font=F_MONO, fill=DIM)
        y = 50
        for v in view:
            d.text((24, y), v, font=F_MONO, fill=color_for(v))
            y += 22
        hold(img, per_line if line.strip() else 0.2)
    hold(img, end_hold)


# 1. intro
card(
    "Hackathon Scout",
    [
        "An OpenMinion 0.1 agent that reads a hackathon or bounty page and returns:",
        "• a typed brief: deadline, prizes, deliverables, blockers, effort, GO / SKIP",
        "• a submission checklist written only after human approval",
        "• a ranking of every page scouted in one run",
        "  Model: Google Gemini (free tier) via OpenMinion's built-in gemini preset",
    ],
    7,
)

# 2. setup
terminal(
    [
        "$ pip install openminion            # 0.1.22",
        "$ openminion setup --provider gemini --model gemini-3.5-flash-lite --no-chat",
        "Configuration saved at ...\\.openminion\\agents.json (provider: Gemini)",
        "",
        "$ python scout.py --yes \\",
        "    https://superteam.fun/api/listings/details/build-an-autonomous-capital-agent-... \\",
        "    https://redditgameofday2026.devpost.com/",
    ],
    "setup",
    per_line=0.9,
    end_hold=1.5,
)

# 3. the real run
log = (ROOT / "examples" / "demo-run.txt").read_text(encoding="utf-8").splitlines()
run_lines = [
    "$ python scout.py --yes <superteam bounty> <reddit hackathon>",
    *[line for line in log if line.strip()],
]
terminal(run_lines, "python scout.py  (real run, Gemini 3.5 Flash Lite)", per_line=0.75, end_hold=5)

# 4. explain the two verdicts
card(
    "What just happened",
    [
        "1. fetch_page (READ_ONLY tool) pulled each page; a deterministic pre-scan put",
        "   gating lines such as 'Fund your agent wallet with at least 20 USDC' first.",
        "2. save_checklist is a write tool, so OpenMinion's action policy asked for",
        "   approval through Agent.run(approval_callback=...) before touching disk.",
        "3. submit_brief (typed tool parameters) recorded the structured brief.",
        "4. A fixed policy forces SKIP when a blocker needs the builder's own capital.",
    ],
    10,
)

# 5. checklist file
checklist = (ROOT / "examples" / "redditgameofday2026.md").read_text(encoding="utf-8").splitlines()
terminal(["$ type out\\redditgameofday2026.md", *checklist], "generated checklist (approved write)", per_line=0.5, end_hold=4)

# 6. findings
card(
    "Building blocks tested · 10 findings",
    [
        "✓ @tool scopes, action policy + approval_callback, typed tool params, sessions/stats",
        "✗ output_type schema never reaches the model; replies wrapped in an answer envelope",
        "✗ no backoff on provider 429 even with retry-after; 300 s turn budget ignores run timeout",
        "✗ parallel tool calls trip the task_update guard -> user-facing 'restate the task'",
        "✗ Windows long paths break runtime bootstrap; stale provider preset models",
        "  Full write-up with repros and suggested fixes: FEEDBACK.md",
    ],
    10,
    accent=OK,
)
card("Thanks!", ["Source, README, FEEDBACK.md and examples: see the repository.", "  Built and tested on Windows 10 · Python 3.12 · openminion 0.1.22"], 4)

# encode
out = ROOT / "demo.mp4"
cmd = [
    imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
    "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "23", str(out),
]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
assert proc.stdin is not None
for frame in frames:
    proc.stdin.write(frame.tobytes())
proc.stdin.close()
proc.wait()
print(f"wrote {out} ({len(frames) / FPS:.0f}s, {out.stat().st_size // 1024} KB)")
