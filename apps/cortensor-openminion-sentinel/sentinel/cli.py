"""CLI entrypoint for Cortensor OpenMinion Sentinel."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sentinel.engine import run_consensus_audit
from sentinel.probes import run_openminion_probes
from sentinel.rpc_tools import DEFAULT_TARGETS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cortensor-sentinel",
        description="Cortensor + OpenMinion 0.1 DeFi Control-Plane Security Sentinel",
    )
    parser.add_argument(
        "--probes-only",
        action="store_true",
        help="Run only the 8-probe OpenMinion 0.1.23 SDK verification suite.",
    )
    parser.add_argument(
        "--audit-all",
        action="store_true",
        help="Run SDK probes + full multi-agent consensus audits on all default targets.",
    )
    parser.add_argument(
        "--target",
        help="Custom contract target formatted as chain:0xAddress (e.g. base:0x3128...).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic offline control-plane fixtures instead of live public RPC.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "cortensor"],
        default="cortensor",
        help="Provider mode for consensus audit turns (default: cortensor).",
    )
    parser.add_argument(
        "--export-report",
        help="Optional output JSON path (e.g. artifacts/latest_report.json).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    probe_summary = run_openminion_probes()
    audits: list[dict] = []

    if args.probes_only:
        pass
    elif args.target:
        chain, _, address = args.target.partition(":")
        if not chain or not address.startswith("0x") or len(address) != 42:
            print(f"Invalid --target format: {args.target!r} (expected chain:0x40hex)", file=sys.stderr)
            return 2
        res = run_consensus_audit(
            target={"id": "custom", "name": f"Target {address[:10]}", "chain": chain, "address": address},
            offline_rpc=args.offline,
            provider_mode=args.provider,
            use_loopback=True,
        )
        audits.append(res.to_dict())
    else:
        # Default / --audit-all audits all default targets plus 1 explicit fail-closed disagreement check
        for target in DEFAULT_TARGETS:
            res = run_consensus_audit(
                target=dict(target),
                offline_rpc=args.offline,
                provider_mode=args.provider,
                use_loopback=True,
            )
            audits.append(res.to_dict())
        fail_closed = run_consensus_audit(
            target=dict(DEFAULT_TARGETS[0]),
            offline_rpc=True,
            provider_mode=args.provider,
            use_loopback=True,
            force_disagree=True,
        )
        audits.append(fail_closed.to_dict())

    report = {
        "project": "cortensor-openminion-sentinel",
        "version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sdk_probes": probe_summary,
        "audits": audits,
    }

    if args.export_report:
        out_path = Path(args.export_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        f"[cortensor-sentinel] OpenMinion v{probe_summary['openminion_version']} probes: "
        f"{probe_summary['passed']}/{probe_summary['total_probes']} passed "
        f"({probe_summary['total_duration_ms']} ms)"
    )
    for p in probe_summary["probes"]:
        status = "PASS" if p["passed"] else "FAIL"
        print(f"  - {p['probe_id']} [{status}] ({p['duration_ms']} ms): {p['detail']}")

    for idx, a in enumerate(audits, 1):
        cp = a["control_plane"]
        print(
            f"  [Audit {idx}] {a['target']['name']} ({cp['chain']}:{cp['address']}) | "
            f"source={cp['source']} | consensus={a['consensus_status']} | "
            f"final_tier={a['final_risk_tier']} | handoff={a['escalated_via_handoff']}"
        )

    return 0 if probe_summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
