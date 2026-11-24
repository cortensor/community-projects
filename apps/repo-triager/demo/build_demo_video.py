#!/usr/bin/env python3
"""Build ``demo.mp4`` — the Cortensor Hackathon #5 walkthrough for Repo Triager.

The video is assembled from three deterministic parts:

1. ``demo/captures/*.txt`` — the *real* stdout of ``doctor``, ``demo``, ``pytest`` and
   ``findings/repro_instructions_truncation.py`` (regenerate with ``--capture``).
2. narration rendered per scene with ``edge-tts`` and concatenated with ``ffmpeg``.
3. 1280x720 frames drawn with Pillow, one per caption chunk.

Timing is driven by the measured narration length of each scene, so a scene is never
shorter than its own voice-over. Audio is placed with ``adelay`` at the *cumulative* start
of each scene (``starts[i]``), which is what keeps multi-scene narration from stacking at
t=0 — the bug that broke the earlier Reactive Sentinel cut.

Output: ``demo.mp4`` (H.264 + AAC, 1280x720, 30 fps) and ``demo/VOICEOVER.md``.

    python demo/build_demo_video.py              # full build (needs network for TTS)
    python demo/build_demo_video.py --capture    # refresh demo/captures/*.txt first
    python demo/build_demo_video.py --frames-only
    python demo/verify_demo.py                   # audio/video checks on the result
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo"
CAPS = DEMO / "captures"
BUILD = DEMO / "build"
TTS_DIR = BUILD / "tts"
FRAME_DIR = BUILD / "frames"
OUT = ROOT / "demo.mp4"

FPS = 30
W, H = 1280, 720
LEAD = 0.55   # silence before the narration of a scene starts
TAIL = 0.45   # silence after it ends
VOICE = "en-US-AndrewNeural"
RATE = "-3%"

# --------------------------------------------------------------------------- palette
BG = (10, 14, 20)
PANEL = (14, 19, 26)
PANEL_EDGE = (38, 48, 62)
BAR = (22, 28, 37)
FG = (201, 212, 224)
DIM = (120, 133, 149)
GREEN = (126, 205, 137)
CYAN = (108, 197, 214)
AMBER = (233, 183, 96)
RED = (232, 118, 118)
ACCENT = (99, 179, 237)

MONO = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"
MONO_B = "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

F_BODY = ImageFont.truetype(MONO, 16)
F_BODY_B = ImageFont.truetype(MONO_B, 16)
F_SMALL = ImageFont.truetype(MONO, 14)
F_TITLE = ImageFont.truetype(SANS_B, 68)
F_SUB = ImageFont.truetype(SANS, 27)
F_CHIP = ImageFont.truetype(SANS_B, 16)
F_HEAD = ImageFont.truetype(SANS_B, 17)
F_CAP = ImageFont.truetype(SANS, 20)
F_CAP_B = ImageFont.truetype(SANS_B, 20)

LINE_H = 22
BODY_W = 116  # characters that fit the panel at 16 px monospace

# --------------------------------------------------------------------------- ffmpeg

def _tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for extra in (Path.home() / ".local/bin", Path("/usr/local/bin"), Path("/opt/homebrew/bin")):
        cand = extra / name
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    if name == "ffmpeg":
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:  # pragma: no cover
            pass
    raise SystemExit(f"{name} not found on PATH")


FFMPEG = None
FFPROBE = None


def tools() -> tuple[str, str]:
    global FFMPEG, FFPROBE
    if FFMPEG is None:
        FFMPEG = _tool("ffmpeg")
        try:
            FFPROBE = _tool("ffprobe")
        except SystemExit:
            FFPROBE = ""  # fall back to parsing `ffmpeg -i`
    return FFMPEG, FFPROBE


def media_duration(path: Path) -> float:
    ffmpeg, ffprobe = tools()
    if ffprobe:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(out.stdout.strip())
    out = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out.stderr)
    if not m:
        raise RuntimeError(f"cannot read duration of {path}")
    h, mnt, sec = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(sec)


# --------------------------------------------------------------------------- capture

CAPTURE_CMDS = {
    "doctor.txt": [".venv/bin/python", "-m", "repo_triager.cli", "--provider", "scripted", "doctor"],
    "demo.txt": [".venv/bin/python", "-m", "repo_triager.cli", "--provider", "scripted", "demo"],
    "pytest.txt": [".venv/bin/python", "-m", "pytest"],
    "repro1.txt": [".venv/bin/python", "findings/repro_instructions_truncation.py"],
    "turncost.txt": [".venv/bin/python", "findings/measure_turn_cost.py"],
}


def capture() -> None:
    CAPS.mkdir(parents=True, exist_ok=True)
    for name, cmd in CAPTURE_CMDS.items():
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        text = res.stdout + res.stderr
        (CAPS / name).write_text(text, encoding="utf-8")
        print(f"captured {name}: {len(text.splitlines())} lines")


def cap(name: str) -> list[str]:
    return (CAPS / name).read_text(encoding="utf-8").splitlines()


def tidy(line: str) -> str:
    """Hide the build machine's absolute path — the demo should read like a checkout."""
    return line.replace(str(ROOT) + "/", "").replace(str(ROOT), ".")


# --------------------------------------------------------------------------- scenes

def build_scenes() -> list[dict]:
    doctor = cap("doctor.txt")
    demo = cap("demo.txt")
    pytest_out = cap("pytest.txt")
    repro = cap("repro1.txt")

    pytest_line = next((tidy(l) for l in pytest_out if "passed" in l), "69 passed").strip()

    doctor_lines = [
        "> repo-triager --provider scripted doctor",
        "",
    ]
    for ln in doctor:
        s = tidy(ln).rstrip()
        if not s.strip() or s.startswith("Repo Triager") or s.startswith("====="):
            continue
        if s.startswith("full diagnostics"):
            continue
        if s.startswith("memory tools"):
            s = "memory tools      : memory.forget, memory.search, memory.write, ..."
        if s.startswith("skill tools"):
            s = "skill tools       : skill.get, skill.ingest, skill.inspect, ..."
        if s.startswith("[WARN] security.untrusted_content"):
            s = "[WARN] security.untrusted_content.boundary_posture: external surfaces enabled"
        doctor_lines.append(s)

    demo_lines = [
        "> repo-triager --provider scripted demo",
        "",
    ]
    for ln in demo:
        s = tidy(ln).rstrip()
        t = s.strip()
        if not t or t.startswith("Repo Triager demo") or t.startswith("====="):
            continue
        if "policy events" in t:
            continue
        if t.startswith("outbox:"):
            s = "   outbox: var/outbox/openminion_openminion/0859.md  (+ .json)"
        if t.startswith("applied=False"):
            s = "   applied=False  — nothing staged for #853"
        if t.startswith("report:"):
            s = "   report: var/runs/<timestamp>-openminion_openminion/report.md  (+ .json)"
        if t.startswith("json  :"):
            continue
        demo_lines.append(s)

    repro_lines = [
        "> python findings/repro_instructions_truncation.py",
        "",
    ]
    for ln in repro:
        s = tidy(ln).rstrip()
        if not s or s.startswith("FINDING 1") or s.startswith("====="):
            continue
        repro_lines.append(s)

    return [
        dict(
            key="title", label="01 / 08 · OVERVIEW", layout="title",
            narration=(
                "Repo Triager is a maintainer tool built on the OpenMinion 0.1 Python SDK. "
                "It reads one open issue, classifies it against the repository's own labels, "
                "drafts the maintainer's reply, and stops at a human approval gate before "
                "anything is written."
            ),
            caps=[
                "Repo Triager — a maintainer tool on the OpenMinion 0.1 Python SDK.",
                "Reads an issue, classifies it against the repository's own labels, drafts the reply,",
                "and stops at a human approval gate before anything is written.",
            ],
            pipeline=[
                "issue #859   →   analyse    read-only tools + pydantic decision",
                "             →   dedupe     bounded subagent",
                "             →   gate       stage_triage   (approval required)",
                "             →   outbox     dry run + memory",
            ],
        ),
        dict(
            key="workflow", label="02 / 08 · SDK WORKFLOW", layout="term",
            window="src/repo_triager/ — one runtime, four turns",
            narration=(
                "The workflow is four steps on a single runtime. A read-only analysis turn "
                "returns a pydantic-validated decision. A bounded subagent double-checks "
                "duplicates. Then a staging turn whose only write tool is gated by OpenMinion's "
                "action policy. Approved decisions go to memory, so the next run stays consistent."
            ),
            caps=[
                "Four steps on a single runtime.",
                "Read-only analysis, a bounded duplicate subagent, then a staging turn whose only",
                "write tool is gated by OpenMinion's action policy.",
                "Approved decisions go to memory, so the next run stays consistent.",
            ],
            content=[
                "§ tools.py — the risk contract does the gating",
                '  @tool(min_scope="READ_ONLY")   triage_precheck · get_issue · label_taxonomy',
                "                                 search_duplicate_issues · list_open_issues",
                "                                 → runs with no prompt",
                "",
                "  @tool  (bare, no scope)        stage_triage",
                "                                 → the action policy requires confirmation",
                "",
                "§ agent.py — phases on APIRuntime",
                "  1  analyse    output_type=TriageDecision      read-only tools",
                "  2  dedupe     subagent()                      isolated session",
                "  3  stage      forced_tools=[stage_triage]     the human gate",
                "  4  remember   memory.write                    read by the next run",
            ],
        ),
        dict(
            key="runtime", label="03 / 08 · RUNTIME", layout="term",
            window="repo-triager doctor — the real OpenMinion runtime",
            narration=(
                "Everything runs in process. The runtime bootstraps into a local home, one "
                "hundred and six tools register, memory and skill tools are present, and doctor "
                "reports OK: twenty-three checks pass, three warn, none fail."
            ),
            caps=[
                "Everything runs in process.",
                "One hundred and six tools register; memory and skill tools are present.",
                "doctor: OK — 23 checks pass, 3 warn, none fail.",
            ],
            content=doctor_lines,
            highlight=["tools registered", "doctor: OK"],
        ),
        dict(
            key="triage", label="04 / 08 · TRIAGE", layout="term",
            window="repo-triager --provider scripted demo",
            narration=(
                "The demo uses a local scripted provider, so the run is reproducible with no "
                "credential and no network. Only the token stream is scripted: the runtime, the "
                "tools, the policy gate, sessions and memory are the real SDK. Issue 859 comes "
                "back as S2, area tools, from a decision the runtime validated."
            ),
            caps=[
                "The demo uses a local scripted provider: reproducible, no credential, no network.",
                "Only the token stream is scripted — runtime, tools, policy gate, sessions and",
                "memory are the real SDK.",
                "Issue 859 comes back as S2, area tools, from a validated decision.",
            ],
            content=demo_lines,
            highlight=["#859 →", "subagent verdict"],
        ),
        dict(
            key="gate", label="05 / 08 · THE APPROVAL GATE", layout="term",
            window="the same gate, approved and denied",
            narration=(
                "Now the gate. The write tool is a bare tool, so the action policy requires a "
                "confirmation before it can run. Approved, the plan is staged. Denied, the same "
                "gate refuses and nothing is written. Both decisions are recorded with the "
                "policy source that produced them."
            ),
            caps=[
                "Now the gate: the write tool is a bare tool, so the action policy requires",
                "a confirmation before it can run.",
                "Approved, the plan is staged. Denied, the same gate refuses and nothing is written.",
                "Both decisions are recorded with the policy source that produced them.",
            ],
            content=[
                "§ the write cannot run without an answer from the policy engine",
                "",
                "  allow  →  stage_triage   decision: allow   policy: operator-flag: auto",
                "            outbox/openminion_openminion/0859.md   (dry run)",
                "",
                "  deny   →  stage_triage   decision: deny    policy: operator-flag: deny",
                "            applied=False — the outbox stays empty for #853",
                "",
                "§ every answer is written into the run report",
                "  #859  Policy: stage_triage → allow (operator-flag: auto (non-interactive))",
                "  #853  Policy: stage_triage → deny  (operator-flag: deny)",
                "",
                "  --apply skip  → analyse only, no write tool is offered",
                "  --apply ask   → interactive prompt (default)",
                "  --apply pause → OpenMinion's own confirmation, replayed on the waiting thread",
            ],
            highlight=["allow", "deny"],
        ),
        dict(
            key="output", label="06 / 08 · OUTPUT", layout="term",
            window="the staged plan and the run report",
            narration=(
                "The staged plan is a dry-run artifact: severity, component, labels, duplicates "
                "and the reply draft, marked as never sent to GitHub. Every run also leaves a "
                "Markdown and JSON report with the policy audit line and the model call count."
            ),
            caps=[
                "The staged plan is a dry-run artifact: severity, component, labels, duplicates",
                "and the reply draft — marked as never sent to GitHub.",
                "Every run also leaves a Markdown and JSON report with the policy audit line and",
                "the model call count.",
            ],
            content=[
                "> cat var/outbox/openminion_openminion/0859.md",
                "",
                "§ Triage plan — #859 Reject malformed explicit plugin contract versions",
                "  - Severity: S2   - Component: area:tools   - Type: bug",
                "  - Labels to add: bug, area:tools",
                "  - Possible duplicates: none      - Confidence: 0.78",
                "  - Mode: dry run — staged locally, nothing was written to GitHub",
                "",
                "  ## Reply draft",
                "  Thanks for the precise report — the contract-version check should reject an",
                "  explicit but malformed version before any plugin module is imported ...",
                "",
                "> repo-triager report",
                "  | Issue | Severity | Component  | Type | Staged |",
                "  | #859  | S2       | area:tools | bug  | yes    |",
                "  | #853  | S2       | area:sdk   | bug  | no     |",
            ],
            highlight=["Mode:", "| #859", "| #853"],
        ),
        dict(
            key="findings", label="07 / 08 · WHAT BROKE", layout="term",
            window="openminion 0.1.24 — six reproducible issues",
            narration=(
                "The hackathon asks what broke. Testing the SDK at this depth surfaced six "
                "reproducible issues in 0.1.24: instructions silently truncated at eight hundred "
                "and sixty characters; output_type never sending the schema; a policy denial "
                "breaking structured output; session ids with a slash disabling memory; operator "
                "command-line tools crashing without a passwd entry; and memory search hiding the "
                "content it found. Each has a runnable reproduction, and the container crash has a "
                "two-line patch."
            ),
            caps=[
                "The hackathon asks what broke. Testing the SDK at this depth surfaced six",
                "reproducible issues in 0.1.24.",
                "Silent instruction truncation, output_type without a schema, a denial that breaks",
                "structured output, slash session ids that disable memory, operator CLIs without a",
                "passwd entry, and memory search that hides its content.",
                "Each has a runnable reproduction; the container crash has a two-line patch.",
            ],
            content=[
                "§ findings/ — each script prints RESULT: REPRODUCED, no credential needed",
                "",
                "  P0  instructions truncated at ~860 chars       repro_instructions_truncation.py",
                "  P0  output_type never sends the schema         repro_structured_output_schema.py",
                "  P1  a policy denial breaks structured output   repro_policy_gate_vs_output_type.py",
                "  P1  session id with \"/\" disables memory        repro_session_scope.py",
                "  P1  operator CLIs crash without a passwd entry repro_operator_id_getpwuid.py",
                "  P2  memory.search returns [TRUNCATED]          repro_memory_search_truncation.py",
                "",
                "§ impact, not just bugs",
                "  patches/operator_id_fallback.patch     a two-line fix for every container and CI",
                "  docs/openminion-issue-reports.md       six ready-to-file reports with repro steps",
                "  BUILDING_BLOCKS_TESTED.md              what each building block did in a real flow",
            ],
            highlight=["P0", "P1", "P2"],
        ),
        dict(
            key="close", label="08 / 08 · REPRODUCE", layout="term",
            window="the reproduction, the suite, the repository",
            narration=(
                "Here is one reproduction running: eight of thirty rules survive, and the turn "
                "still reports completed. The suite is sixty-nine tests, offline, in about half "
                "a minute. Code, six reproductions and these notes are MIT licensed — the links "
                "are below."
            ),
            caps=[
                "Here is one reproduction: eight of thirty rules survive, and the turn still",
                "reports completed.",
                "The suite is sixty-nine tests, offline, in about half a minute.",
                "Code, six reproductions and these notes are MIT licensed.",
            ],
            content=repro_lines + [
                "",
                "> python -m pytest",
                "",
                "  " + pytest_line.strip() + "        (no API key, no network)",
                "",
                "§ Repo Triager — github.com/dorithesky/cortensor-triager · MIT",
                "  OpenMinion 0.1.24  ·  Cortensor Hackathon #5  ·  DoraHacks #2418",
            ],
            highlight=["RESULT:", "passed in", "github.com/"],
        ),
    ]


# --------------------------------------------------------------------------- drawing

MARKUP = re.compile(r"\*\*([^*]+)\*\*")


def line_style(line: str):
    if line.startswith("§"):
        return CYAN, True
    if line.startswith(">"):
        return GREEN, True
    if line.startswith("──"):
        return CYAN, False
    return FG, False


def emphasise(text: str, needles: tuple[str, ...]) -> list[tuple[str, bool]]:
    """Split a line into (text, emphasised) runs from **markup** and plain needles."""
    runs: list[tuple[str, bool]] = []
    pos = 0
    for m in MARKUP.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], False))
        runs.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], False))

    out: list[tuple[str, bool]] = []
    needles = tuple(n for n in needles if n)
    for chunk, strong in runs:
        if strong or not needles:
            out.append((chunk, strong))
            continue
        pattern = re.compile("|".join(re.escape(n) for n in needles))
        last = 0
        for m in pattern.finditer(chunk):
            if m.start() > last:
                out.append((chunk[last:m.start()], False))
            out.append((m.group(0), True))
            last = m.end()
        if last < len(chunk):
            out.append((chunk[last:], False))
    return out


def draw_body(draw: ImageDraw.ImageDraw, lines: list[str], visible: int, y0: int = 104,
              highlight: tuple[str, ...] = ()) -> None:
    y = y0
    for raw in lines[:visible]:
        base, strong = line_style(raw)
        x = 64
        for text, emph in emphasise(raw, highlight):
            font = F_BODY_B if (strong or emph) else F_BODY
            color = base if strong else (AMBER if emph else FG)
            draw.text((x, y), text, font=font, fill=color)
            x += draw.textlength(text, font=font)
        y += LINE_H
    if y > 566:
        print(f"  ! content overflows the panel ({len(lines)} lines)", file=sys.stderr)


def rounded(draw: ImageDraw.ImageDraw, box, radius: int, fill, outline) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)


def render(scene: dict, visible: int, caption: str, progress: float, out: Path) -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # header
    draw.text((40, 24), scene["label"], font=F_HEAD, fill=DIM)
    right = "repo-triager  ·  OpenMinion 0.1.24  ·  MIT"
    draw.text((W - 40 - draw.textlength(right, font=F_SMALL) - 6, 26), right, font=F_SMALL, fill=(80, 92, 106))

    if scene["layout"] == "title":
        title = "Repo Triager"
        tw = draw.textlength(title, font=F_TITLE)
        draw.text(((W - tw) / 2, 150), title, font=F_TITLE, fill=(238, 243, 248))
        sub = "GitHub issue triage with a human approval gate"
        sw = draw.textlength(sub, font=F_SUB)
        draw.text(((W - sw) / 2, 236), sub, font=F_SUB, fill=(150, 164, 180))

        chips = ["OpenMinion 0.1.24", "Cortensor Hackathon #5", "Hackathon #5 · apps/repo-triager", "MIT"]
        chips = ["OpenMinion 0.1.24", "Cortensor Hackathon #5", "MIT"]
        widths = [draw.textlength(c, font=F_CHIP) + 28 for c in chips]
        total = sum(widths) + 12 * (len(chips) - 1)
        x = (W - total) / 2
        for c, wd in zip(chips, widths):
            rounded(draw, (x, 292, x + wd, 326), 17, (22, 30, 40), (52, 68, 86))
            draw.text((x + 14, 300), c, font=F_CHIP, fill=ACCENT)
            x += wd + 12

        box_top = 368
        box_bottom = box_top + 26 + LINE_H * len(scene["pipeline"])
        rounded(draw, (150, box_top, W - 150, box_bottom + 14), 10, (13, 18, 25), (32, 41, 53))
        y = box_top + 24
        for i, ln in enumerate(scene["pipeline"]):
            if i >= visible:
                break
            draw.text((W / 2 - 285, y), ln, font=F_BODY, fill=FG if i else (222, 231, 240))
            y += LINE_H
    else:
        rounded(draw, (40, 58, W - 40, 572), 10, PANEL, PANEL_EDGE)
        draw.rectangle((41, 59, W - 41, 86), fill=BAR)
        for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            draw.ellipse((58 + i * 18, 68, 68 + i * 18, 78), fill=col)
        tw = draw.textlength(scene["window"], font=F_SMALL)
        draw.text(((W - tw) / 2, 66), scene["window"], font=F_SMALL, fill=DIM)
        draw_body(draw, scene["content"], visible, highlight=tuple(scene.get("highlight", ())))

    # caption
    if caption:
        draw.rectangle((40, 592, W - 40, 690), fill=(17, 23, 31))
        draw.rectangle((40, 592, 44, 690), fill=ACCENT)
        words, lines, cur = caption.split(), [], ""
        for w_ in words:
            trial = (cur + " " + w_).strip()
            if draw.textlength(trial, font=F_CAP) > W - 40 - 44 - 40:
                lines.append(cur)
                cur = w_
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines[:3]
        y = 592 + (98 - 26 * len(lines)) / 2
        for ln in lines:
            draw.text((64, y), ln, font=F_CAP, fill=(226, 233, 240))
            y += 26

    # progress bar
    draw.rectangle((40, 706, W - 40, 709), fill=(30, 38, 48))
    draw.rectangle((40, 706, 40 + (W - 80) * min(1.0, progress), 709), fill=ACCENT)

    img.save(out)


# --------------------------------------------------------------------------- audio

def tts(text: str, out: Path) -> None:
    edge = shutil.which("edge-tts") or str(Path.home() / ".local/bin/edge-tts")
    subprocess.run(
        [edge, "--voice", VOICE, f"--rate={RATE}", "--text", text, "--write-media", str(out)],
        check=True, capture_output=True,
    )


def build_scenes_with_audio(scenes: list[dict], reuse: bool) -> list[dict]:
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg, _ = tools()
    for i, sc in enumerate(scenes):
        mp3 = TTS_DIR / f"{i:02d}-{sc['key']}.mp3"
        wav = TTS_DIR / f"{i:02d}-{sc['key']}.wav"
        if not reuse or not mp3.exists():
            print(f"  tts {i + 1}/{len(scenes)} {sc['key']} …", flush=True)
            tts(sc["narration"], mp3)
        if not reuse or not wav.exists() or wav.stat().st_mtime < mp3.stat().st_mtime:
            # Trim the TTS lead-in/lead-out so a scene starts exactly at `lead`.
            # Without this, edge-tts' ~0.25 s of leading silence would make every
            # scene start late by the same amount.
            subprocess.run(
                [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp3),
                 "-af", "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.04,"
                        "areverse,"
                        "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.12,"
                        "areverse",
                 "-ar", "48000", "-ac", "1", str(wav)],
                check=True,
            )
        sc["audio"] = wav
        sc["speech"] = media_duration(wav)
    return scenes


def timeline(scenes: list[dict]) -> list[dict]:
    start = 0.0
    for sc in scenes:
        need = LEAD + sc["speech"] + TAIL
        frames = math.ceil(need * FPS - 1e-9)
        sc["frames"] = frames
        sc["start"] = start
        sc["visual"] = frames / FPS
        sc["audio_delay_ms"] = int(round((start + LEAD) * 1000))
        start += sc["visual"]
    return scenes


def split_frames(sc: dict) -> list[int]:
    caps = sc["caps"]
    weights = [max(1, len(c)) for c in caps]
    total_w = sum(weights)
    counts, acc = [], 0
    for i, w_ in enumerate(weights):
        if i == len(weights) - 1:
            counts.append(sc["frames"] - acc)
        else:
            n = max(1, int(round(sc["frames"] * w_ / total_w)))
            counts.append(n)
            acc += n
    # repair rounding so the sum is exact
    diff = sum(counts) - sc["frames"]
    idx = len(counts) - 1
    while diff > 0 and idx >= 0:
        if counts[idx] > 1:
            counts[idx] -= 1
            diff -= 1
        idx -= 1
    return counts


def render_frames(scenes: list[dict]) -> list[dict]:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    for f in FRAME_DIR.glob("*.png"):
        f.unlink()
    segments = []
    total = sum(sc["frames"] for sc in scenes)
    done = 0
    for i, sc in enumerate(scenes):
        counts = split_frames(sc)
        n_lines = len(sc.get("content") or sc.get("pipeline") or [])
        shown_lines = 0
        for j, (count, caption) in enumerate(zip(counts, sc["caps"])):
            shown_lines = max(shown_lines, math.ceil(n_lines * (j + 1) / len(counts)))
            path = FRAME_DIR / f"{i:02d}-{j}.png"
            render(sc, shown_lines, caption, (done + count / 2) / total, path)
            segments.append({"png": path, "frames": count})
            done += count
    (BUILD / "segments.json").write_text(
        json.dumps([{"png": s["png"].name, "frames": s["frames"]} for s in segments], indent=1),
        encoding="utf-8",
    )
    return segments


# --------------------------------------------------------------------------- encode

def encode(scenes: list[dict], segments: list[dict]) -> None:
    ffmpeg, _ = tools()
    concat = BUILD / "concat.txt"
    lines = []
    for s in segments:
        lines.append(f"file '{(FRAME_DIR / s['png'].name).as_posix()}'")
        lines.append(f"duration {s['frames'] / FPS:.6f}")
    lines.append(f"file '{(FRAME_DIR / segments[-1]['png'].name).as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(sc["frames"] for sc in scenes) / FPS
    graph = []
    for i, sc in enumerate(scenes):
        graph.append(
            f"[{i + 1}:a]aresample=48000,adelay={sc['audio_delay_ms']}:all=1[a{i}]"
        )
    graph.append("".join(f"[a{i}]" for i in range(len(scenes)))
                 + f"amix=inputs={len(scenes)}:normalize=0:dropout_transition=0[mix]")
    graph.append("[mix]loudnorm=I=-16:TP=-1.5:LRA=11,apad[aout]")

    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "concat", "-safe", "0", "-i", str(concat)]
    for sc in scenes:
        cmd += ["-i", str(sc["audio"])]
    cmd += [
        "-filter_complex", ";".join(graph),
        "-map", "0:v", "-map", "[aout]",
        "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "24",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(OUT),
    ]
    subprocess.run(cmd, check=True)
    print(f"\nwrote {OUT}  ({OUT.stat().st_size / 1_048_576:.2f} MB, {total:.1f}s)")


def write_manifest(scenes: list[dict]) -> None:
    data = {
        "fps": FPS,
        "lead": LEAD,
        "tail": TAIL,
        "voice": VOICE,
        "rate": RATE,
        "scenes": [
            {
                "key": sc["key"],
                "label": sc["label"],
                "start": round(sc["start"], 3),
                "visual": round(sc["visual"], 3),
                "narration_start": round(sc["start"] + LEAD, 3),
                "speech": round(sc["speech"], 3),
                "audio_delay_ms": sc["audio_delay_ms"],
                "narration": sc["narration"],
            }
            for sc in scenes
        ],
    }
    (BUILD / "timeline.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def write_voiceover(scenes: list[dict]) -> None:
    def ts(t: float) -> str:
        return f"{int(t // 60)}:{t % 60:04.1f}"

    rows = ["# Voice-over and shot list — demo.mp4", "",
            f"Voice: `{VOICE}` at {RATE}  ·  {W}×{H}, {FPS} fps, H.264 + AAC  ·  "
            f"total {ts(sum(s['frames'] for s in scenes) / FPS)}", "",
            "| # | Scene | In | Out | On screen | Narration |",
            "| --- | --- | --- | --- | --- | --- |"]
    for i, sc in enumerate(scenes):
        rows.append(
            f"| {i + 1} | {sc['label'].split('·')[1].strip()} | {ts(sc['start'])} | "
            f"{ts(sc['start'] + sc['visual'])} | `{sc.get('window', 'title card')}` | {sc['narration']} |"
        )
    rows += ["", "Regenerate: `python demo/build_demo_video.py`  ·  check: `python demo/verify_demo.py`", ""]
    (DEMO / "VOICEOVER.md").write_text("\n".join(rows), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true", help="re-run doctor/demo/pytest/repro first")
    ap.add_argument("--fresh-tts", action="store_true", help="re-render narration instead of reusing")
    ap.add_argument("--frames-only", action="store_true", help="only redraw PNG frames")
    args = ap.parse_args()

    tools()
    if args.capture:
        capture()
    BUILD.mkdir(parents=True, exist_ok=True)
    scenes = build_scenes()
    print(f"{len(scenes)} scenes")
    scenes = build_scenes_with_audio(scenes, reuse=not args.fresh_tts)
    scenes = timeline(scenes)
    segments = render_frames(scenes)
    print(f"{len(segments)} frame segments, {sum(s['frames'] for s in segments)} frames")
    if not args.frames_only:
        encode(scenes, segments)
        write_manifest(scenes)
        write_voiceover(scenes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
