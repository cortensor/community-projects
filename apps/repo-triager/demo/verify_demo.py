#!/usr/bin/env python3
"""Verify ``demo.mp4``: container/stream facts, audio timing, and sampled frames.

Checks, in order:

1. ``ffprobe`` — one H.264 1280x720 video stream and one AAC audio stream, duration and size.
2. audio envelope — every scene's narration starts where the timeline says it does
   (onset offset < 0.2 s), the silence before it really is silent, and no narration bleeds
   into another scene's window. This is the check that would have caught the earlier
   "all eight voice-overs at t=0.35 s" bug.
3. frames — one PNG per scene pulled from the finished MP4, checked for non-blank content
   and kept in ``demo/build/verify-frames/`` so a human can look at them.

    python demo/verify_demo.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo.mp4"
BUILD = ROOT / "demo" / "build"
FRAMES = BUILD / "verify-frames"
FFMPEG = "ffmpeg"
FFPROBE = "ffprobe"


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def probe() -> dict:
    out = run([FFPROBE, "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", str(DEMO)])
    return json.loads(out)


def decode_audio() -> tuple[np.ndarray, int]:
    rate = 16000
    raw = subprocess.run(
        [FFMPEG, "-v", "error", "-i", str(DEMO), "-vn", "-ac", "1", "-ar", str(rate),
         "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return data, rate


def db(x: float) -> float:
    return 20 * np.log10(max(x, 1e-9))


def rms(seg: np.ndarray) -> float:
    return float(np.sqrt(np.mean(seg ** 2))) if seg.size else 0.0


def main() -> int:
    if not DEMO.exists():
        raise SystemExit("demo.mp4 not found — run demo/build_demo_video.py first")
    timeline = json.loads((BUILD / "timeline.json").read_text(encoding="utf-8"))

    info = probe()
    fmt = info["format"]
    streams = info["streams"]
    video = [s for s in streams if s["codec_type"] == "video"][0]
    audio = [s for s in streams if s["codec_type"] == "audio"][0]
    dur = float(fmt["duration"])
    fps_num, fps_den = (video.get("avg_frame_rate") or "30/1").split("/")
    fps = float(fps_num) / float(fps_den or 1)

    lines: list[str] = []
    ok = True

    def say(s: str = "") -> None:
        lines.append(s)
        print(s)

    say("== container ==")
    say(f"file        : {DEMO}  ({DEMO.stat().st_size / 1_048_576:.2f} MB)")
    say(f"duration    : {dur:.2f} s  ({int(dur // 60)}:{dur % 60:04.1f})")
    say(f"bitrate     : {int(fmt['bit_rate']) / 1000:.0f} kb/s")
    say(f"video       : {video['codec_name']} {video['width']}x{video['height']} "
        f"{fps:.2f} fps  {video.get('pix_fmt')}")
    say(f"audio       : {audio['codec_name']} {audio['sample_rate']} Hz "
        f"{audio.get('channels')} ch  {int(audio.get('bit_rate', 0)) / 1000:.0f} kb/s")

    checks = [
        ("one video stream", len([s for s in streams if s["codec_type"] == "video"]) == 1),
        ("one audio stream", len([s for s in streams if s["codec_type"] == "audio"]) == 1),
        ("h264 + aac", video["codec_name"] == "h264" and audio["codec_name"] == "aac"),
        ("1280x720", (video["width"], video["height"]) == (1280, 720)),
        ("1:30 <= length <= 5:00", 90 <= dur <= 300),
        ("size <= 10 MB", DEMO.stat().st_size <= 10 * 1024 * 1024),
    ]
    say("")
    for name, good in checks:
        say(f"  [{'OK ' if good else 'FAIL'}] {name}")
        ok &= bool(good)

    say("")
    say("== audio timing (per scene) ==")
    data, rate = decode_audio()
    say(f"decoded {len(data) / rate:.2f} s of audio at {rate} Hz")
    say("")
    say("  scene         start   lead-gap dB   speech dB   onset offset   verdict")
    for sc in timeline["scenes"]:
        s = sc["start"]
        lead = timeline["lead"]
        sp = sc["speech"]
        pre = data[int((s + 0.05) * rate):int((s + lead - 0.05) * rate)]
        speech = data[int((s + lead + 0.15) * rate):int((s + lead + sp - 0.10) * rate)]
        win = data[int(s * rate):int((s + lead + 0.6) * rate)]
        thresh = 0.008
        idx = np.where(np.abs(win) > thresh)[0]
        onset = (s + (idx[0] / rate)) if idx.size else float("nan")
        offset = onset - (s + lead)
        tail = data[int((s + lead + sp + 0.05) * rate):int((s + sc["visual"] - 0.02) * rate)]
        good = (
            abs(offset) < 0.20
            and rms(pre) < 0.01          # -40 dBFS: the lead gap is silent
            and rms(speech) > 0.02       # speech is actually there
            and rms(tail) < 0.02
        )
        ok &= bool(good)
        say(f"  {sc['key']:<12s} {s:6.1f}s  {db(rms(pre)):8.1f}      {db(rms(speech)):7.1f}     "
            f"{offset:+.3f}s      {'OK' if good else 'FAIL'}")

    total_speech = sum(sc["speech"] for sc in timeline["scenes"])
    say("")
    say(f"  narration total {total_speech:.1f}s  ·  timeline {timeline['scenes'][-1]['start'] + timeline['scenes'][-1]['visual']:.1f}s"
        f"  ·  decoded audio {len(data) / rate:.1f}s")

    say("")
    say("== sampled frames ==")
    FRAMES.mkdir(parents=True, exist_ok=True)
    for sc in timeline["scenes"]:
        t = sc["start"] + sc["visual"] * 0.55
        out = FRAMES / f"{sc['key']}.png"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(DEMO),
                        "-frames:v", "1", str(out)], check=True)
        arr = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(out).convert("L"))
        mean, p99 = float(arr.mean()), float(np.percentile(arr, 99))
        good = mean > 12 and p99 > 120
        ok &= bool(good)
        say(f"  {sc['key']:<12s} @ {t:6.1f}s  mean luma {mean:5.1f}  p99 {p99:5.1f}  "
            f"{'OK' if good else 'FAIL'}  -> {out.relative_to(ROOT)}")

    say("")
    say("RESULT: " + ("ALL CHECKS PASSED" if ok else "CHECKS FAILED"))
    (BUILD / "verify.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
