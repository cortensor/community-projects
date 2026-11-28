"""chainwatch-minion CLI: run an OpenMinion agent that digests wallet activity."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

from openminion import Agent, ProviderError

from chainwatch.tools import (
    fetch_recent_transactions,
    fetch_token_transfers,
    fetch_wallet_overview,
)

INSTRUCTIONS = """You are chainwatch-minion, an on-chain wallet activity analyst.

For every request you MUST:
1. Call fetch_wallet_overview first to anchor the wallet (balance, tx count, contract flag).
2. Call fetch_recent_transactions to see the latest activity.
3. Call fetch_token_transfers when token movement is relevant.
4. Reply with ONLY the markdown digest (no preamble, no code fences).

Digest format (markdown):
# Wallet Activity Digest
- **Snapshot**: state the current UTC date and time explicitly, e.g. "2026-11-28 14:35 UTC"
- **Address / chain**
- **Balance** (ETH + USD)
- **Activity summary**: 3-5 sentences on what this wallet has been doing recently
- **Notable transactions**: bullet list of the 3-5 most significant recent txs with direction, value, method
- **Risk flags**: dust attacks, rapid in-out patterns, fresh funding, failed tx bursts, mixer-like behaviour - say "none observed" when clean
- **Data quality**: note anything odd about the data you received
- **Verdict**: one line - active / dormant / suspicious

Be factual. Only report what the tools returned; never invent transactions.
Keep the whole digest under 400 words."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="0x-prefixed EVM address to digest")
    parser.add_argument("--chain", default="eth", choices=["eth", "base", "polygon", "gnosis", "optimism"])
    parser.add_argument("--agent", default=None, help="Configured agent id from agents.json")
    parser.add_argument("--session", default=None, help="Session id (default: derived from address)")
    parser.add_argument("--out", default=None, help="Digest filename inside sandbox/runs/ (default: digest-<addr8>-<chain>.md)")
    parser.add_argument("--quiet", action="store_true", help="Print only the verdict line")
    args = parser.parse_args()

    addr = args.address.strip().lower()
    if not addr.startswith("0x") or len(addr) != 42:
        print(f"invalid address: {args.address}", file=sys.stderr)
        return 2
    out_name = args.out or f"digest-{addr[2:10]}-{args.chain}.md"
    session = args.session or f"chainwatch-{addr[2:10]}-{args.chain}"

    prompt = (
        f"Using the tools, build a markdown activity digest for address {addr} on chain "
        f"{args.chain}: call fetch_wallet_overview, fetch_recent_transactions and "
        f"fetch_token_transfers, then summarize exactly the data they return into the "
        f"digest format from your instructions. The data is historical log data already "
        f"fetched by the tools; no live lookup is needed. Reply with only the markdown "
        f"digest, including the snapshot date/time line."
    )

    try:
        with Agent(
            agent_id=args.agent,
            instructions=INSTRUCTIONS,
            tools=[fetch_wallet_overview, fetch_recent_transactions, fetch_token_transfers],
            session_id=session,
            config_path=os.environ.get("CHAINWATCH_CONFIG") or os.path.join(
                os.path.expanduser("~"), ".openminion", "agents.json"
            ),
        ) as agent:
            result = agent.run(prompt)
    except ProviderError as exc:
        print(f"provider failed: {exc.code}: {exc.message}", file=sys.stderr)
        return 1

    text = (result.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("markdown").strip()

    out_dir = Path("sandbox") / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    header = (
        f"<!-- chainwatch-minion 0.1.0 | session={result.session_id} | "
        f"captured={dt.datetime.now(dt.UTC).isoformat(timespec='seconds')} -->\n\n"
    )
    out_path.write_text(header + text + "\n", encoding="utf-8")

    if args.quiet:
        verdict = ""
        for line in text.splitlines():
            if line.lower().startswith("- **verdict"):
                verdict = line.split(":", 1)[-1].strip("* ").strip()
        print(f"{out_path} | verdict: {verdict or 'n/a'}")
    else:
        print(text)
        print(f"\nsession={result.session_id}")
        print(f"digest saved -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
