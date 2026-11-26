"""Command-line entrypoint for ReleaseGuard Minion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openminion import AgentOutputValidationError, ProviderError, TurnTimeoutError

from .agent import ReleaseGuardMinion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release-guard",
        description="Inspectable, permission-gated repository release auditor on OpenMinion 0.1.",
    )
    parser.add_argument("--config", default=None, help="Path to OpenMinion agents.json")
    parser.add_argument("--agent", default=None, help="Configured OpenMinion agent_id")

    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Audit a local repository for release readiness")
    audit_p.add_argument("repo_path", help="Path to the repository to audit")
    audit_p.add_argument("--session", default=None, help="Explicit OpenMinion session_id")
    audit_p.add_argument(
        "--output-brief",
        default=None,
        help="Path to write Markdown release brief (requires --approve-brief)",
    )
    audit_p.add_argument(
        "--approve-brief",
        action="store_true",
        help="Approve the policy-gated write_release_brief tool once",
    )
    audit_p.add_argument(
        "--memory-out",
        default=None,
        help="Export audit findings to an OpenMinion MemoryBundle JSON file",
    )
    audit_p.add_argument("--timeout", type=float, default=120.0)
    audit_p.add_argument("--json", action="store_true", help="Emit JSON output")

    sub.add_parser(
        "diagnostics",
        help="Inspect OpenMinion runtime posture, capabilities, and self-model",
    )

    sec_p = sub.add_parser(
        "security-subagent",
        help="Run a bounded read-only secret-hygiene OpenMinion subagent",
    )
    sec_p.add_argument("repo_path", help="Path to the repository to scan")
    sec_p.add_argument("--timeout", type=int, default=60)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with ReleaseGuardMinion(config_path=args.config, agent_id=args.agent) as guard:
            if args.command == "diagnostics":
                print(json.dumps(guard.diagnostics_snapshot(), indent=2, sort_keys=True))
                return 0
            if args.command == "security-subagent":
                print(
                    guard.run_security_subagent(
                        Path(args.repo_path), timeout_seconds=args.timeout
                    )
                )
                return 0
            envelope = guard.audit_repository(
                Path(args.repo_path),
                session_id=args.session,
                output_brief_path=args.output_brief,
                memory_bundle_path=args.memory_out,
                allow_write_brief=bool(args.approve_brief),
                timeout_seconds=args.timeout,
            )
    except BrokenPipeError:
        return 0
    except (ProviderError, TurnTimeoutError, AgentOutputValidationError) as exc:
        print(f"release-guard: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    try:
        if args.json:
            print(envelope.model_dump_json(indent=2))
        else:
            r = envelope.report
            print(f"ReleaseGuard Verdict: {r.verdict.upper()} ({r.score}/100) — {r.repo_name}")
            print(f"Session: {envelope.session_id} | Run: {envelope.run_id}")
            print(f"Rationale: {r.rationale}")
            for chk in r.checks:
                print(f"  [{'PASS' if chk.passed else 'FAIL'}] {chk.category}: {chk.evidence}")
            if envelope.approvals:
                print("Approval Decisions:")
                for dec in envelope.approvals:
                    print(f"  - {dec.tool_name}: allowed={dec.allowed} ({dec.reason})")
            if envelope.brief_path:
                print(f"Brief: {envelope.brief_path}")
            if envelope.memory_bundle_path:
                print(f"MemoryBundle: {envelope.memory_bundle_path}")
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
