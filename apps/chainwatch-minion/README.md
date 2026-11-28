# chainwatch-minion

An on-chain wallet activity analyst built on the **OpenMinion SDK 0.1** for
Cortensor Hackathon #5.

chainwatch-minion is a CLI agent that investigates any EVM address across
multiple chains and produces a structured, honest **Wallet Activity Digest**:
balance snapshot, activity narrative, notable transactions, and heuristic risk
flags (dust/poisoning inflows, unsolicited token drops, scripted burst
patterns, contract-vs-EOA ambiguity).

## What it does

```
$ python -m chainwatch.cli 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 --chain eth
```

1. The agent calls `fetch_wallet_overview` (balance, USD value, contract flag,
   lifetime tx count).
2. It calls `fetch_recent_transactions` (latest txs with direction, value,
   decoded method, status, fee).
3. It calls `fetch_token_transfers` (ERC-20/721 movement).
4. It writes a markdown digest — snapshot time, balance, activity summary,
   notable transactions, risk flags, data-quality notes, and a one-line
   verdict (active / dormant / suspicious).
5. The CLI persists the digest under `sandbox/runs/`.

The agent is deliberately **read-only**: every tool it can invoke is
`READ_ONLY`-scoped. The durable write (saving the digest) is performed by the
host CLI, not the model. This is a least-privilege design decision — see
FINDINGS.md for why.

## Data source

Public **Blockscout API v2** instances (no API key required). Reachability
verified 2026-11-28 from a datacenter IP:

| Chain    | Endpoint                    | Status |
|----------|-----------------------------|--------|
| eth      | eth.blockscout.com          | 200 OK |
| optimism | explorer.optimism.io        | 200 OK |
| base     | base.blockscout.com         | 403 (Cloudflare challenge) |
| polygon  | polygon.blockscout.com      | 403 (Cloudflare challenge) |
| gnosis   | gnosisscan.io               | 403 (Cloudflare challenge) |

The agent handles unreachable chains gracefully: when every endpoint for a
chain fails, it issues a digest with explicit data gaps instead of inventing
data (see `examples/run2-base-degraded.md` for a real degraded run).

## Architecture

```
chainwatch/
  __init__.py   # package marker (v0.1.0)
  tools.py      # @tool-decorated functions: fetch_wallet_overview,
                # fetch_recent_transactions, fetch_token_transfers
  cli.py        # Agent wiring + digest persistence
```

- **Model**: any OpenAI-compatible endpoint. This build ran
  `fp/deepseek-v4.1-flash` through a local SSE-aggregating proxy (see
  FINDINGS.md, finding #1).
- **Tool strategy**: hybrid (model-native tool calls).
- **Policy**: all tools are `READ_ONLY` + `idempotent`, so no confirmation
  round-trips are needed during a run.

## Setup

```bash
uv venv --python 3.11 .venv
uv pip install openminion==0.1.24
openminion --no-interactive config init --provider openai
# point base_url at your OpenAI-compatible endpoint, set the model name
python -m chainwatch.cli <0x-address> --chain eth
```

## Digest format

Every run emits the same shape, so digests are diff-able across snapshots:

```
# Wallet Activity Digest
- Snapshot (explicit UTC date/time)
- Address / chain
- Balance (ETH + USD)
- Activity summary (3-5 sentences)
- Notable transactions (top 3-5, with direction / value / method)
- Risk flags (dust, rapid in-out, fresh funding, failed tx bursts, mixer-like)
- Data quality (what the tools could / could not retrieve)
- Verdict (active / dormant / suspicious)
```

## Files

- `chainwatch/tools.py` — Blockscout v2 tools
- `chainwatch/cli.py` — agent wiring and digest persistence
- `sandbox/runs/` — persisted digests (real run output)
- `examples/run1-attempt.log` — first successful full-agent run (eth)
- `examples/run2-base-degraded.md` — honest degraded run when a chain's
  endpoints are unreachable
- `FINDINGS.md` — building blocks tested, rough edges found, what we learned
