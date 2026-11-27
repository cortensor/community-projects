"""CLI entry point for NovaTriage Minion."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

from .agent import run_novatriage_workflow
from .onchain_tools import fetch_token_preflight, probe_x402_service
from .solidity_analyzer import analyze_solidity_source


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novatriage-minion",
        description="NovaTriage Minion: autonomous Web3 Solidity, token & x402 triage agent on OpenMinion 0.1",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    audit_p = sub.add_parser("audit", help="Run full multi-agent OpenMinion triage workflow")
    audit_p.add_argument("--contract", required=True, help="Path to Solidity .sol file")
    audit_p.add_argument(
        "--token",
        default="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        help="Token contract address for live DexScreener/GoPlus preflight",
    )
    audit_p.add_argument("--chain", default="base", help="Chain slug or ID (default: base)")
    audit_p.add_argument("--x402-url", default="", help="Override x402 base URL")
    audit_p.add_argument("--provider", default="local", help="Model provider: local | cortensor | openai")
    audit_p.add_argument("--model", default="", help="Model name override")
    audit_p.add_argument("--workspace", default=".novatriage-run", help="Workspace directory for OpenMinion state")
    audit_p.add_argument("--json", action="store_true", help="Emit full JSON output")

    sol_p = sub.add_parser("scan-sol", help="Run deterministic Solidity static scan only")
    sol_p.add_argument("contract", help="Path to Solidity .sol file")

    x402_p = sub.add_parser("x402-probe", help="Probe live x402 v2 discovery & HTTP 402 header")
    x402_p.add_argument("--base-url", default="", help="x402 service base URL")
    x402_p.add_argument("--path", default="/api/v1/solidity-triage", help="Resource path")

    pre_p = sub.add_parser("preflight", help="Run live DexScreener + GoPlus token preflight")
    pre_p.add_argument("token", help="Token contract address")
    pre_p.add_argument("--chain", default="base", help="Chain slug or ID")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "scan-sol":
        res = analyze_solidity_source(file_path=args.contract)
        print(res.model_dump_json(indent=2))
        return 0

    if args.command == "x402-probe":
        res = probe_x402_service(base_url=args.base_url, resource_path=args.path)
        print(res.model_dump_json(indent=2))
        return 0

    if args.command == "preflight":
        res = fetch_token_preflight(args.token, chain_id=args.chain)
        print(res.model_dump_json(indent=2))
        return 0

    if args.command == "audit":
        if args.json:
            logging.disable(logging.INFO)
        summary = run_novatriage_workflow(
            workspace_dir=Path(args.workspace).resolve(),
            contract_path=Path(args.contract).resolve(),
            token_address=args.token,
            chain_id=args.chain,
            x402_base_url=args.x402_url,
            provider=args.provider,
            model=args.model,
        )
        payload = {
            "report": summary.report.model_dump(mode="json"),
            "session_id": summary.session_id,
            "run_id": summary.run_id,
            "run_state": summary.run_state,
            "stream_events_seen": summary.stream_events_seen,
            "followup_reply": summary.followup_reply,
            "skill_summary": summary.skill_summary,
            "memory_summary": summary.memory_summary,
            "task_summary": summary.task_summary,
            "diagnostics": summary.diagnostics,
            "approval_decisions": summary.approval_decisions,
            "written_report_path": summary.written_report_path,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            r = summary.report
            print(f"=== NovaTriage Minion Report: {r.target_name} ===")
            print(f"Verdict      : {r.recommendation} ({r.overall_risk_tier}, {r.overall_risk_score}/100)")
            print(f"Solidity     : {r.solidity_audit.finding_count} findings across {r.solidity_audit.lines_scanned} lines")
            for f in r.solidity_audit.findings:
                print(f"  - [{f.severity}] L{f.line} {f.rule_id}: {f.title}")
            if r.token_preflight:
                tp = r.token_preflight
                print(
                    f"Token Preflight: {tp.symbol or tp.token_address} | dex_ok={tp.dexscreener_ok} "
                    f"goplus_ok={tp.goplus_ok} | honeypot={tp.is_honeypot} | liq=${tp.liquidity_usd}"
                )
            if r.x402_probe:
                xp = r.x402_probe
                print(
                    f"x402 Probe   : discovery={xp.discovery_status} | challenge={xp.challenge_status} "
                    f"| network={xp.network} | payTo={xp.pay_to}"
                )
            print(f"Session      : {summary.session_id} | Stream events={summary.stream_events_seen}")
            print(f"Delegations  : {len(r.delegations)} bounded subagents | Approvals={len(summary.approval_decisions)}")
            print(f"Skill        : {summary.skill_summary.get('skill_id')} | Memory items={summary.memory_summary.get('item_count')}")
            print(f"Tasks        : {summary.task_summary.get('visible_task_count')} scheduled | Tools={summary.diagnostics.get('tool_inventory_count')}")
            if summary.written_report_path:
                print(f"Artifact     : {summary.written_report_path}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
