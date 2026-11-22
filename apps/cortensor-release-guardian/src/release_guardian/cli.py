"""Command-line interface for Cortensor Release Guardian."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_guardian.agent import run_followup, run_release_audit


def _print_stream_event(event: dict) -> None:
    kind = event.get("kind") or event.get("type") or "delta"
    text = event.get("text") or event.get("delta") or ""
    if text:
        print(text, end="", flush=True)
    else:
        print(f"\n[event:{kind}]", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release-guardian",
        description="Audit a Cortensor / OpenMinion repository for release readiness.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Run a release-readiness audit on a repository")
    p_audit.add_argument("--repo", default=".", help="Path to target repository")
    p_audit.add_argument(
        "--config",
        default="configs/agents.ollama.json",
        help="Path to OpenMinion agents.json config",
    )
    p_audit.add_argument("--agent", default=None, help="Configured agent_id override")
    p_audit.add_argument("--session", default="release-guardian-session", help="Session ID")
    p_audit.add_argument("--stream", action="store_true", help="Stream progress events")
    p_audit.add_argument("--structured", action="store_true", help="Validate typed ReleaseVerdict JSON")
    p_audit.add_argument("--no-tools", action="store_true", help="Skip tool registration (useful for small models)")
    p_audit.add_argument("--out", default=None, help="Optional path to save JSON report")

    p_follow = sub.add_parser("followup", help="Ask a follow-up question in the same OpenMinion session")
    p_follow.add_argument("question", help="Follow-up question")
    p_follow.add_argument("--config", default="configs/agents.ollama.json")
    p_follow.add_argument("--agent", default=None)
    p_follow.add_argument("--session", default="release-guardian-session")

    args = parser.parse_args(argv)

    if args.command == "audit":
        report = run_release_audit(
            repo_path=args.repo,
            config_path=args.config,
            agent_id=args.agent,
            session_id=args.session,
            stream=args.stream,
            structured=args.structured,
            use_tools=not args.no_tools,
            on_event=_print_stream_event if args.stream else None,
        )
        if args.stream:
            print()
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"=== SESSION: {report['session_id']} ===")
        if report.get("structured_verdict"):
            print(json.dumps(report["structured_verdict"], indent=2))
        else:
            print(report["text"])
        if report.get("validation_warning"):
            print(f"\n[WARN] {report['validation_warning']}", file=sys.stderr)
        return 0

    if args.command == "followup":
        res = run_followup(
            question=args.question,
            config_path=args.config,
            session_id=args.session,
            agent_id=args.agent,
        )
        print(f"=== SESSION: {res['session_id']} ===")
        print(res["text"])
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
