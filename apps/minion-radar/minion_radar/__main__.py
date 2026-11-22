"""CLI: python -m minion_radar [--repo owner/name] [--demo | --no-model] [--yes]"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from . import brief, diff, github, state

DEMO_LABEL = "DEMO MODE: simulated repo data and no model call. Not a real run."
NOMODEL_LABEL = "NO MODEL: live GitHub data, rule based brief (OpenMinion agent not used)."


def load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def ask(auto_yes: bool):
    def decide(tool_name: str, args: dict, approval_id: str) -> bool:
        if tool_name != "radar_save_checkpoint":
            print(f"[approval] denying unexpected tool {tool_name}")
            return False
        if auto_yes:
            print("[approval] auto approved radar_save_checkpoint (--yes)")
            return True
        return input("[approval] Save checkpoint so next run shows only newer items? [y/N] ").strip().lower() == "y"
    return decide


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    p = argparse.ArgumentParser(description="Minion Radar builder brief")
    p.add_argument("--repo", default="openminion/openminion")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="offline: fixture data, no model (clearly labelled)")
    mode.add_argument("--no-model", action="store_true", help="live GitHub data, rule based brief")
    p.add_argument("--demo-data", action="store_true", help="real model run, but on the fixture repo data")
    p.add_argument("--yes", action="store_true", help="auto approve the checkpoint write")
    p.add_argument("--film", action="store_true",
                   help="fast filmed demo: one compact snapshot, auto approve checkpoint")
    p.add_argument("--out", default="briefs")
    a = p.parse_args(argv)
    if a.film and (a.demo or a.no_model):
        p.error("--film needs a real model run; do not combine it with --demo or --no-model")

    label, meta = "", {}
    if a.demo or a.no_model:
        label = DEMO_LABEL if a.demo else NOMODEL_LABEL
        print(label)
        st = state.load(a.repo)
        rel = diff.new_releases(github.fetch_releases(a.repo, demo=a.demo), st)
        iss = diff.new_or_updated_issues(github.fetch_issues(a.repo, demo=a.demo), st)
        b = brief.offline_brief(a.repo, rel[:5], iss[:20])
        if not a.demo and (a.yes or ask(False)("radar_save_checkpoint", {}, "local")):
            state.save(diff.next_state(st, rel, iss))
    else:
        from .agent import run_agent
        try:
            timeout = float(os.environ.get("RADAR_TIMEOUT") or (600 if a.film else 1800))
            b, meta = run_agent(a.repo, agent_id=os.environ.get("RADAR_AGENT_ID") or None,
                                approve=ask(a.yes or a.film), demo_data=a.demo_data,
                                timeout=timeout, model=os.environ.get("RADAR_MODEL") or None,
                                compact=a.film, allow_retry=not a.film)
        except Exception as exc:
            print(f"OpenMinion run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            print("Tip: run `openminion doctor --check-turn` or try --demo.", file=sys.stderr)
            return 1
        origin = (meta or {}).get("origin") or (
            "fallback" if (meta or {}).get("run_state") == "snapshot_fallback" else "model_generated"
        )
        if a.demo_data:
            label = "Real model run on SIMULATED fixture repo data."
        elif a.film and origin == "fallback":
            label = "FALLBACK: rule based brief from the live snapshot. Not model generated."
        elif a.film:
            label = "MODEL GENERATED: compact live snapshot, real model brief, checkpoint auto approved."
        meta = dict(meta or {})
        meta["origin"] = origin
    md = brief.to_markdown(b, label)
    if meta:
        md += (
            f"\n<sub>origin={meta.get('origin')} run_id={meta.get('run_id')} "
            f"session={meta.get('session_id')} state={meta.get('run_state')}</sub>\n"
        )
    out = Path(a.out); out.mkdir(exist_ok=True)
    f = out / f"{a.repo.replace('/', '__')}_{datetime.now():%Y%m%d_%H%M%S}.md"
    f.write_text(md)
    print(md)
    print(f"saved {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
