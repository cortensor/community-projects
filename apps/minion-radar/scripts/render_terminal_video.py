#!/usr/bin/env python3
"""Render a scripted terminal session as MP4 (and optional GIF) with ffmpeg.

The video is a paced playback of a real command's output, not a live tty capture.
Long quiet waits can be cut and labelled. No secrets should be in the input text.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_REG = "/usr/share/fonts/truetype/sand-box/google/IBM Plex Mono/IBMPlexMono-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/sand-box/google/IBM Plex Mono/IBMPlexMono-Bold.ttf"
FONT_UI = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BG = (18, 18, 22)
CHROME = (36, 36, 42)
CHROME_TEXT = (190, 190, 198)
TEXT = (230, 230, 235)
DIM = (120, 122, 130)
GREEN = (74, 222, 128)
RED = (248, 113, 113)
YELLOW = (250, 204, 21)
CYAN = (103, 232, 249)
BLUE = (147, 197, 253)
MAGENTA = (232, 121, 249)
ORANGE = (251, 191, 36)
WHITE = TEXT


def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def color_for(line: str) -> tuple[int, int, int]:
    s = line.strip()
    if s.startswith("$ ") or s.startswith("python -m"):
        return BLUE
    if s.startswith("== "):
        return CYAN
    if s.startswith("STATUS"):
        return DIM
    if s.startswith("HIT"):
        return GREEN
    if s.startswith("MISSED"):
        return RED
    if s.startswith("OPEN") or s.startswith("VOID") or s.startswith("APPROXIMATE"):
        return YELLOW
    if s.startswith("parsed ") or s.startswith("reports in") or s.startswith("saved "):
        return DIM
    if s.startswith("[tool]") or s.startswith("[approval]"):
        return MAGENTA
    if s.startswith("Minion Radar") or s.startswith("OpenMinion") or s.startswith("MODEL GENERATED") or s.startswith("> MODEL"):
        return ORANGE
    if s.startswith("FALLBACK:") or s.startswith("OpenMinion run failed") or s.startswith("PROVIDER"):
        return RED
    if s.startswith("#") and not s.startswith("# "):
        return TEXT
    if s.startswith("**") or s.startswith("# "):
        return WHITE
    return TEXT



def wrap_line(line: str, cols: int) -> list[str]:
    """Wrap a terminal line. Table rows keep column spaces; prose breaks on words."""
    if len(line) <= cols:
        return [line]
    table_prefixes = ("STATUS", "HIT", "MISSED", "OPEN", "VOID", "COIN")
    if line.startswith(table_prefixes) or (line[:7].strip() in table_prefixes):
        return [line[i:i + cols] for i in range(0, len(line), cols)]
    out: list[str] = []
    rest = line
    first = True
    while len(rest) > cols:
        cut = rest.rfind(" ", 0, cols)
        if cut < cols // 3:
            cut = cols
            piece, rest = rest[:cut], rest[cut:]
        else:
            piece, rest = rest[:cut], rest[cut + 1:]
        out.append(piece)
        if not first:
            pass
        first = False
        # indent wrapped prose so it is visible as a continuation
        if rest and not rest.startswith(" "):
            rest = "  " + rest
            # if indent pushed it over, it will wrap again
    if rest:
        out.append(rest)
    return out or [""]


class Terminal:
    def __init__(self, width=1920, height=1080, font_size=28, title="terminal"):
        self.width = width
        self.height = height
        self.title = title
        self.margin_x = 36
        self.chrome_h = 52
        self.font = load_font(FONT_REG, font_size)
        self.font_bold = load_font(FONT_BOLD, font_size)
        self.ui = load_font(FONT_UI, 18)
        # measure advance
        self.cw = max(1.0, float(self.font.getlength("M")))
        self.ch = int(font_size * 1.45)
        self.rows = max(8, (height - self.chrome_h - 28) // self.ch)
        self.cols = max(40, int((width - self.margin_x * 2) // self.cw))
        self.lines: list[str] = []
        self.cursor_vis = True

    def set_lines(self, lines: list[str]) -> None:
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(wrap_line(line, self.cols))
        self.lines = wrapped[-self.rows :]

    def render(self) -> Image.Image:
        img = Image.new("RGB", (self.width, self.height), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, self.width, self.chrome_h], fill=CHROME)
        # traffic lights
        for i, col in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
            x = 22 + i * 22
            d.ellipse([x, 18, x + 14, 32], fill=col)
        t = self.title
        tw = d.textlength(t, font=self.ui)
        d.text(((self.width - tw) / 2, 16), t, font=self.ui, fill=CHROME_TEXT)
        y = self.chrome_h + 16
        for line in self.lines:
            d.text((self.margin_x, y), line, font=self.font, fill=color_for(line))
            y += self.ch
        return img


def write_video(events: list[dict], out_mp4: Path, title: str, width=1920, height=1080,
                font_size=28, fps=30, gif: Path | None = None) -> None:
    term = Terminal(width, height, font_size, title)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="termvid-"))
    frames_meta: list[tuple[str, float]] = []
    buffer: list[str] = []
    n = 0

    def snapshot(duration: float) -> None:
        nonlocal n
        if duration <= 0:
            return
        img = term.render()
        # hash to reuse identical frames
        raw = img.tobytes()
        digest = hashlib.md5(raw).hexdigest()[:16]
        path = tmp / f"{digest}.png"
        if not path.exists():
            img.save(path, "PNG")
        frames_meta.append((str(path), duration))
        n += 1

    def show():
        term.set_lines(buffer)
        snapshot(1 / fps)

    for ev in events:
        kind = ev["type"]
        if kind == "type":
            text = ev["text"]
            cps = ev.get("cps", 24)
            prefix = ev.get("prefix", "$ ")
            # type into a fresh prompt line
            typed = prefix
            buffer.append(typed)
            term.set_lines(buffer)
            snapshot(0.25)
            for ch in text:
                typed += ch
                buffer[-1] = typed
                term.set_lines(buffer)
                snapshot(max(1 / fps, 1 / cps))
            snapshot(ev.get("hold", 0.35))
        elif kind == "line":
            buffer.append(ev["text"])
            term.set_lines(buffer)
            snapshot(ev.get("pause", 0.12))
        elif kind == "lines":
            for i, line in enumerate(ev["text"].splitlines() or [""]):
                buffer.append(line)
                term.set_lines(buffer)
                pause = ev.get("pause", 0.08)
                if ev.get("pause_blank") is not None and not line.strip():
                    pause = ev["pause_blank"]
                snapshot(pause)
            snapshot(ev.get("hold", 0))
        elif kind == "hold":
            term.set_lines(buffer)
            snapshot(ev.get("seconds", 1.0))
        elif kind == "caption":
            # a one-line trim marker, then optional hold
            buffer.append("")
            buffer.append(ev["text"])
            term.set_lines(buffer)
            snapshot(ev.get("seconds", 1.6))
        elif kind == "prompt_ready":
            if not buffer or buffer[-1] != "$ ":
                buffer.append("$ ")
            term.set_lines(buffer)
            snapshot(ev.get("seconds", 0.4))
        else:
            raise ValueError(f"unknown event type {kind}")

    # ffmpeg concat
    lst = tmp / "concat.txt"
    with lst.open("w") as f:
        for path, dur in frames_meta:
            f.write(f"file '{path}'\n")
            f.write(f"duration {dur:.4f}\n")
        if frames_meta:
            f.write(f"file '{frames_meta[-1][0]}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-fps_mode", "cfr", "-r", str(fps), "-pix_fmt", "yuv420p", "-c:v", "libx264",
        "-crf", "20", "-preset", "medium", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if gif:
        palette = tmp / "palette.png"
        scale = ev_scale = "fps=12,scale=960:-1:flags=lanczos"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(out_mp4), "-vf", f"{scale},palettegen=max_colors=64", str(palette)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(out_mp4), "-i", str(palette),
             "-lavfi", f"{scale}[x];[x][1:v]paletteuse=dither=bayer",
             str(gif)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="terminal")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gif")
    args = ap.parse_args()
    raise SystemExit("This module is imported by the demo builders; it is not a standalone CLI.")


if __name__ == "__main__":
    main()
