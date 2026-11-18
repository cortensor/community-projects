# Cortensor OpenMinion Sentinel (`v0.1.0`)

**Verifiable Multi-Agent DeFi Control-Plane Sentinel built on Cortensor Decentralized Inference + OpenMinion 0.1.23 SDK**

- **Live Interactive Dashboard:** https://random-solver.github.io/cortensor-openminion-sentinel/
- **Walkthrough Video (`66s` H.264 MP4):** https://random-solver.github.io/cortensor-openminion-sentinel/demo.mp4
- **Standalone Repository:** https://github.com/random-solver/cortensor-openminion-sentinel
- **License:** `MIT`
- **OpenMinion SDK Version:** `openminion==0.1.23`

---

## What It Does

**Cortensor OpenMinion Sentinel** inspects smart-contract control planes on Ethereum and Base Mainnet using read-only JSON-RPC calls and verifies findings through a multi-agent **Auditor + Skeptic** workflow powered by **Cortensor** (`/api/v2/completions`) and **OpenMinion 0.1.23**:

1. **Read-Only EVM Control-Plane Inspection (`sentinel/rpc_tools.py`):**
   - Queries `eth_getCode`, EIP-1967 implementation (`0x3608...2bbc`) and admin (`0xb531...6103`) storage slots, `governance()` / `owner()` selectors, Gnosis Safe `getThreshold()` / `getOwners()`, and Timelock `getMinDelay()` / `delay()`.
   - Includes deterministic offline fixtures (`--offline`) so CI tests and air-gapped demos remain 100% reproducible.
2. **Multi-Agent Consensus Engine (`sentinel/engine.py`):**
   - **Primary Auditor (`Agent("sentinel")`):** Executes `@tool(min_scope="READ_ONLY")` contract inspection through `APIRuntime` and `CortensorProviderConfig` (`/api/v2/completions`, `session_id=1`, `session_pool="auto"`, `privacy_level="high"`).
   - **Bounded Skeptic (`subagent(auditor, name="skeptic", memory_posture="none")`):** Runs in an isolated child context (`parent_transcript_inherited=False`) to cross-check control-plane invariants.
   - **Fail-Closed Routing (`Handoff`):** Any `HIGH`/`CRITICAL` governance exposure or auditor-skeptic disagreement (`DISAGREEMENT_FAIL_CLOSED`) triggers `Handoff(target=incident_desk, name="transfer_to_incident_desk")`.
   - **Portable Evidence (`MemoryBundle`):** Serializes verified audit state into `MemoryBundle(version="memory_bundle.v1")` JSON snapshots.
3. **Automated 8-Probe OpenMinion 0.1.23 Verification Suite (`sentinel/probes.py`):**
   - Exercises and benchmarks 8 core OpenMinion 0.1 building blocks (`APIRuntime`, `@tool`, `ChannelAuthenticityConfig`, `subagent`, v1 memory posture guard, `Handoff`, `MemoryBundle`, and `CortensorProviderConfig`), feeding empirical findings into [FEEDBACK.md](./FEEDBACK.md).

---

## Verified Benchmark & Audit Results

Latest run (`python -m sentinel.cli --audit-all --export-report artifacts/latest_report.json`):

- **OpenMinion `0.1.23` SDK Probes:** **`8/8 PASSED`** (`10800.13 ms` total)
- **Live On-Chain & Fail-Closed Consensus Audits:**
  1. **Yearn OG USDC (`yvUSDC v2`)** (`ethereum:0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE`) — `source=live-rpc:ethereum`, `6/9` Gnosis Safe multisig at `0xfeb4acf3df3cdea7399794d0869ef76a6efaff52`, `consensus=AGREED`, `final_tier=LOW`, `handoff=False`.
  2. **Spark sUSDC Vault** (`base:0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858`) — `source=live-rpc:base`, EIP-1967 proxy (`implementation=0x6acc02ddd82206a44ff4ec13977e63d1a29c7723`), `consensus=AGREED`, `final_tier=HIGH`, `handoff=True` (`transfer_to_incident_desk`).
  3. **Circle USDC (`FiatTokenProxy`)** (`base:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`) — `source=live-rpc:base`, `1852` bytes bytecode, EOA owner controller `0x3abd6f64a422225e61e435bae41db12096106df7`, `consensus=AGREED`, `final_tier=HIGH`, `handoff=True` (`transfer_to_incident_desk`).
  4. **Fail-Closed Disagreement Check** (`ethereum:0xa354F35829Ae975e850e23e9615b11Da1B3dC4DE`) — simulated Skeptic challenge (`FORCE_DISAGREE`) upgrades `LOW` -> `HIGH` (`consensus=DISAGREEMENT_FAIL_CLOSED`) and triggers `transfer_to_incident_desk`.

---

## Quick Start

```bash
# 1. Install dependencies (Python 3.11+)
pip install -e .

# 2. Run unit and OpenMinion integration test suite
python -m unittest discover -s tests -v

# 3. Run the 8-probe OpenMinion 0.1.23 SDK verification suite
python -m sentinel.cli --probes-only

# 4. Run full multi-agent consensus audits & export JSON report
python -m sentinel.cli --audit-all --export-report artifacts/latest_report.json

# 5. Audit any custom Ethereum or Base contract address
python -m sentinel.cli --target base:0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858
```

---

## Repository Structure

```text
cortensor-openminion-sentinel/
├── sentinel/
│   ├── __init__.py          # Package exports
│   ├── rpc_tools.py         # Read-only EVM proxy, EIP-1967, Safe & Timelock inspector
│   ├── engine.py            # OpenMinion 0.1.23 + Cortensor multi-agent consensus runtime
│   ├── probes.py            # 8-probe OpenMinion 0.1.23 SDK verification harness
│   └── cli.py               # CLI entrypoint (cortensor-sentinel)
├── tests/
│   └── test_sentinel.py     # Unit + OpenMinion integration tests (5/5 passing)
├── scripts/
│   └── generate_demo_video.py
├── artifacts/
│   └── latest_report.json   # Verified probe & live RPC audit report
├── index.html               # Interactive dashboard + live browser RPC inspector
├── demo.mp4                 # 66-second 1280x720 H.264 walkthrough video
├── FEEDBACK.md              # Empirical OpenMinion 0.1.23 SDK feedback
├── PROJECTS.yml             # Cortensor community-projects registry metadata
├── STATUS.md                # Project status & roadmap
├── RELEASE.md               # v0.1.0 release notes
├── pyproject.toml           # Package configuration
├── .env.example             # Environment variable template
└── LICENSE                  # MIT License
```
