#!/usr/bin/env python3
"""Build the Minion Radar demo video from the 22 Nov 2026 Portal film run."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_terminal_video import write_video

COMMAND = "python -m minion_radar --repo openminion/openminion --film --out samples"
PLAIN = (ROOT / "demo" / "raw-film-2026-11-22.out").read_text()
# Replace typographic dashes the mono font may not draw, for the video only.
PLAIN = PLAIN.replace("‑", "-").replace("‐", "-").replace("‒", "-").replace("–", "-").replace("—", "-").replace("−", "-")

# Split captured output into: prelude (until snapshot), then brief (from approval).
lines = PLAIN.splitlines(keepends=False)
snap_idx = next(i for i, line in enumerate(lines) if line.startswith("[tool] radar_snapshot"))
appr_idx = next(i for i, line in enumerate(lines) if line.startswith("[approval]"))
prelude = lines[: snap_idx + 1]
brief = lines[appr_idx:]


def events() -> list[dict]:
    ev: list[dict] = [
        {"type": "hold", "seconds": 0.7},
        {"type": "type", "text": COMMAND, "cps": 24, "hold": 0.8},
        {"type": "line", "text": "", "pause": 0.2},
        {"type": "lines", "text": "\n".join(prelude), "pause": 0.18, "hold": 6.0},
        {
            "type": "caption",
            "text": "# hosted model wait trimmed: 4 minutes 4 seconds of Cortensor Portal oss-20b latency (09:35:29 to 09:39:33 WAT)",
            "seconds": 7.0,
        },
        {"type": "line", "text": "", "pause": 0.2},
        {"type": "lines", "text": "\n".join(brief), "pause": 0.22, "hold": 45.0},
        {"type": "hold", "seconds": 25.0},
    ]
    return ev


def main() -> int:
    out = ROOT / "demo" / "minion-radar-demo.mp4"
    gif = ROOT / "demo" / "minion-radar-demo.gif"
    write_video(
        events(),
        out_mp4=out,
        gif=gif,
        title="Minion Radar  |  real Cortensor Portal oss-20b run  |  22 Nov 2026, Africa/Lagos (WAT)",
        width=1920,
        height=1080,
        font_size=26,
        fps=30,
    )
    print(f"wrote {out}")
    print(f"wrote {gif}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
