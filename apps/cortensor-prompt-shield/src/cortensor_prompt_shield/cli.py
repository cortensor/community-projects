"""CLI entrypoint for Cortensor Prompt Shield."""

from __future__ import annotations

import argparse
import os
import sys

from openminion import OPENMINION_VERSION

from .agent import run_full_security_audit
from .scanner import scan_python_workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt-shield",
        description="Cortensor Prompt Shield — OpenMinion 0.1 Prompt-Injection, @tool Scope & Session Isolation Auditor",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Run full 5-stage live OpenMinion security audit")
    p_audit.add_argument("--target", default="examples", help="Target Python workspace or file to audit")
    p_audit.add_argument("--out", default="outputs", help="Output directory for JSON + HTML reports")
    p_audit.add_argument("--provider", default=os.environ.get("PROMPT_SHIELD_PROVIDER", "openai"))
    p_audit.add_argument("--base-url", default=os.environ.get("PROMPT_SHIELD_BASE_URL"))
    p_audit.add_argument("--model", default=os.environ.get("PROMPT_SHIELD_MODEL", "gemini-3.8-flash"))
    p_audit.add_argument("--api-key-env", default=os.environ.get("PROMPT_SHIELD_API_KEY_ENV", "OPENAI_API_KEY"))
    p_audit.add_argument("--no-compact-proxy", action="store_true", help="Disable CompactGuardProxy prompt compaction")

    p_scan = sub.add_parser("scan", help="Run fast offline static AST @tool decorator scan")
    p_scan.add_argument("--target", default="examples", help="Target Python workspace or file")

    args = parser.parse_args(argv)

    if args.command == "scan":
        findings = scan_python_workspace(args.target)
        print(f"Cortensor Prompt Shield (OpenMinion {OPENMINION_VERSION}) — Static Scan: {len(findings)} findings")
        for f in findings:
            print(f"  [{f.severity}] {f.rule_id} {f.file_path}:{f.line_number} ({f.function_name}) -> {f.detail}")
        return 0

    if args.command == "audit":
        bundle = run_full_security_audit(
            target_path=args.target,
            output_dir=args.out,
            provider=args.provider,
            base_url=args.base_url,
            model=args.model,
            api_key_env=args.api_key_env,
            use_compact_proxy=not args.no_compact_proxy,
            verbose=True,
        )
        print(f"\n=== AUDIT COMPLETE: GRADE {bundle.structured_report.overall_grade} ({bundle.structured_report.cortensor_readiness_verdict}) ===")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
