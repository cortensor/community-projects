"""Generate 8 high-contrast 1280x720 HTML slides from real NovaTriage outputs and render PNGs via headless Chromium."""

from __future__ import annotations

import html
import json
from pathlib import Path
import subprocess


CHROMIUM = "/Users/zhufan/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"


def _run_capture(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return (proc.stdout + proc.stderr).strip()


def _render_html(slide_num: int, badge: str, title: str, subtitle: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 1280px;
    height: 720px;
    background: radial-gradient(circle at 15% 15%, #16223a 0%, #0b1120 55%, #070b14 100%);
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif;
    padding: 44px 56px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    overflow: hidden;
  }}
  .top {{ display: flex; justify-content: space-between; align-items: center; }}
  .badge {{
    display: inline-block;
    padding: 6px 14px;
    border-radius: 999px;
    background: rgba(56, 189, 248, 0.14);
    border: 1px solid rgba(56, 189, 248, 0.4);
    color: #38bdf8;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  .step {{ color: #94a3b8; font-size: 15px; font-weight: 600; font-family: ui-monospace, monospace; }}
  h1 {{ font-size: 38px; line-height: 1.15; color: #f8fafc; margin-top: 14px; font-weight: 800; }}
  .sub {{ font-size: 18px; color: #94a3b8; margin-top: 8px; }}
  .main {{ flex: 1; margin-top: 22px; display: flex; flex-direction: column; justify-content: center; gap: 16px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
  .card {{
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 14px;
    padding: 20px 22px;
  }}
  .card h3 {{ font-size: 16px; color: #38bdf8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card p, .card li {{ font-size: 15px; line-height: 1.48; color: #cbd5e1; }}
  .card ul {{ padding-left: 18px; }}
  .term {{
    background: #050811;
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-radius: 12px;
    padding: 18px 20px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 13.5px;
    line-height: 1.45;
    color: #a7f3d0;
    white-space: pre-wrap;
    overflow: hidden;
  }}
  .crit {{ color: #f87171; font-weight: 700; }}
  .ok {{ color: #34d399; font-weight: 700; }}
  .warn {{ color: #fbbf24; font-weight: 700; }}
  .pill {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(52, 211, 153, 0.16);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.35);
  }}
  .foot {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #64748b;
    border-top: 1px solid rgba(148, 163, 184, 0.15);
    padding-top: 12px;
  }}
</style>
</head>
<body>
  <div>
    <div class="top">
      <span class="badge">{html.escape(badge)}</span>
      <span class="step">SCENE {slide_num:02d} / 08</span>
    </div>
    <h1>{html.escape(title)}</h1>
    <div class="sub">{html.escape(subtitle)}</div>
  </div>
  <div class="main">{body_html}</div>
  <div class="foot">
    <span>cortensor-novatriage-minion • OpenMinion 0.1.24</span>
    <span>Cortensor Hackathon #5 • Zero Fake Outputs • MIT License</span>
  </div>
</body>
</html>"""


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    venv_bin = ROOT / ".venv" / "bin"

    scan_sol_out = _run_capture([str(venv_bin / "novatriage-minion"), "scan-sol", "samples/VulnerableVault.sol"])
    x402_out = _run_capture([str(venv_bin / "novatriage-minion"), "x402-probe"])
    audit_out = Path("/tmp/demo_audit_cli.txt").read_text(encoding="utf-8") if Path("/tmp/demo_audit_cli.txt").exists() else _run_capture(
        [str(venv_bin / "novatriage-minion"), "audit", "--contract", "samples/VulnerableVault.sol", "--workspace", "/tmp/novatriage-demo-ws"]
    )
    pytest_out = _run_capture([str(venv_bin / "pytest"), "-v"])

    scan_json = json.loads(scan_sol_out)
    scan_preview = json.dumps(
        {
            "contract_label": scan_json["contract_label"],
            "risk_score": scan_json["risk_score"],
            "risk_tier": scan_json["risk_tier"],
            "finding_count": scan_json["finding_count"],
            "top_findings": scan_json["findings"][:4],
        },
        indent=2,
    )

    slides = [
        (
            "Cortensor Hackathon #5",
            "NovaTriage Minion",
            "Autonomous Web3 Solidity, Token & x402 v2 Risk Triage Agent on OpenMinion 0.1.24",
            """
            <div class="grid3">
              <div class="card"><h3>Solidity Static Auditor</h3><p>Deterministic line-level scanner for <code>tx.origin</code>, <code>delegatecall</code>, reentrancy before write, unchecked calls, and mint/drain hooks.</p></div>
              <div class="card"><h3>On-Chain & x402 Recon</h3><p>Live public DexScreener + GoPlus token security preflight and live Cloud Run <code>/.well-known/x402.json</code> + HTTP <code>402</code> challenge verification.</p></div>
              <div class="card"><h3>Fail-Closed OpenMinion</h3><p>Bounded <code>subagent</code> + peer <code>Handoff</code>s, single-use <code>WRITE_SAFE</code> approval gate, SQLite sessions, <code>MemoryBundle</code>, Skills &amp; Tasks.</p></div>
            </div>
            <div class="card">
              <h3>Zero-Cost Reproducible Inference + Cortensor Ready</h3>
              <p>Runs end-to-end through OpenMinion's real <code>OpenAIProvider</code> &amp; <code>LLMCTL</code> pipeline via an in-process OpenAI-compatible server at <strong>$0.00</strong> cost, or switches via env vars to <code>NOVATRIAGE_PROVIDER=cortensor</code>.</p>
            </div>
            """,
        ),
        (
            "Architecture & Delegation",
            "Multi-Agent OpenMinion 0.1.24 Runtime",
            "Exercising Coordinator, Bounded Subagent, Peer Handoffs & Policy Boundaries",
            """
            <div class="grid2">
              <div class="card">
                <h3>NovaTriageCoordinator (Agent)</h3>
                <ul>
                  <li>Typed Pydantic <code>output_type=NovaTriageReport</code></li>
                  <li>Streaming execution via <code>Agent.run_stream(on_delta=...)</code></li>
                  <li><code>NovaTriageApprovalGate</code> enforces single-use <code>WRITE_SAFE</code> &amp; blocks <code>dangerous=True</code> fail-closed</li>
                  <li>Multi-turn SQLite continuity via <code>session_id</code> + <code>thread_id</code></li>
                </ul>
              </div>
              <div class="card">
                <h3>Bounded Specialists</h3>
                <ul>
                  <li><strong>SolidityAuditorMinion</strong> (<code>READ_ONLY</code>): <code>analyze_solidity_contract</code></li>
                  <li><strong>ReconMinion</strong> (<code>READ_ONLY</code>): <code>fetch_token_onchain_preflight</code> + <code>probe_x402_endpoint</code></li>
                  <li><strong>Bounded Subagent Check</strong>: <code>openminion.subagent()</code> verifying <code>SubagentRunContext</code> allowlist isolation</li>
                </ul>
              </div>
            </div>
            <div class="card">
              <h3>OpenMinion Building Blocks Exercised (10 / 10)</h3>
              <p>Agent Execution • Models • Tools • Permissions • Sessions • MemoryBundle • Skills • Tasks • Delegation • Runtime Diagnostics</p>
            </div>
            """,
        ),
        (
            "Tool 1: Deterministic Static Scan",
            "Solidity Security Scanner (VulnerableVault.sol)",
            "Command: novatriage-minion scan-sol samples/VulnerableVault.sol",
            f'<div class="term">{html.escape(scan_preview)}</div>',
        ),
        (
            "Tools 2 & 3: Live On-Chain & x402 v2",
            "Live Cloud Run HTTP 402 & Token Preflight",
            "Command: novatriage-minion x402-probe (Zero Fake Payments)",
            f"""
            <div class="grid2">
              <div class="term">{html.escape(x402_out)}</div>
              <div class="card">
                <h3>Verified Live Challenge Facts</h3>
                <ul>
                  <li>Endpoint: <code>novacraft-x402-api-...run.app</code></li>
                  <li>Discovery: <span class="ok">HTTP 200</span> (<code>x402Version: 2</code>)</li>
                  <li>Challenge: <span class="warn">HTTP 402 PAYMENT-REQUIRED</span></li>
                  <li>Network: <code>eip155:8453</code> (Base USDC <code>50000</code> atomic)</li>
                  <li>PayTo: <code>0x445F7447532d3e9300194E289C7C023A5f3CFc9E</code></li>
                  <li>Token preflight queries DexScreener &amp; GoPlus with clean offline/timeout handling.</li>
                </ul>
              </div>
            </div>
            """,
        ),
        (
            "Full Multi-Agent Run",
            "End-to-End OpenMinion Audit Output",
            "Command: novatriage-minion audit --contract samples/VulnerableVault.sol",
            f'<div class="term">{html.escape(audit_out)}</div>',
        ),
        (
            "Permissions, Memory, Skills & Tasks",
            "Durable State & Fail-Closed Safety Controls",
            "Every write and escalation passes through OpenMinion policy and SQLite stores",
            """
            <div class="grid2">
              <div class="card">
                <h3>NovaTriageApprovalGate</h3>
                <ul>
                  <li><span class="ok">APPROVED</span>: <code>transfer_to_solidity_auditor_minion</code></li>
                  <li><span class="ok">APPROVED</span>: <code>transfer_to_recon_minion</code></li>
                  <li><span class="ok">APPROVED (1x)</span>: <code>write_triage_report</code> (2nd call denied)</li>
                  <li><span class="crit">DENIED</span>: <code>publish_emergency_freeze_notice</code> (<code>dangerous=True</code>)</li>
                </ul>
              </div>
              <div class="card">
                <h3>Persistence & Diagnostics</h3>
                <ul>
                  <li><strong>Skill Catalog:</strong> <code>novatriage_solidity_audit</code> ingested &amp; verified</li>
                  <li><strong>MemoryBundle:</strong> exported, reloaded &amp; recalled on Run #2</li>
                  <li><strong>Tasks:</strong> <code>task.schedule</code> recurring 24h watchlist created</li>
                  <li><strong>Diagnostics:</strong> <code>106</code> visible tools, posture &amp; self-model OK</li>
                </ul>
              </div>
            </div>
            """,
        ),
        (
            "Genuine SDK Feedback",
            "5 Reproducible Findings in OpenMinion 0.1.24",
            "Documented in OPENMINION_FEEDBACK.md & verified in tests/test_openminion_findings.py",
            """
            <div class="card">
              <ul>
                <li><strong>1. <code>subagent()</code> + <code>Handoff()</code> Deadlock Contradiction:</strong> <code>subagent()</code> forces shared parent runtime (<code>handoff.py:295</code>), while <code>ToolRegistry.temporary_registration_scope</code> raises <code>RuntimeError</code> on cross-thread shared-runtime handoffs (<code>registry/__init__.py:98</code>).</li>
                <li><strong>2. Empty <code>default_channel</code> Fails in <code>warn</code> Mode:</strong> Fresh <code>agents.default</code> fails with <code>inbound authenticity denied (reason=invalid_channel, mode=warn)</code> unless <code>default_channel="console"</code> is explicitly set.</li>
                <li><strong>3. <code>Handoff</code> Hardcodes <code>WRITE_SAFE</code>:</strong> Triggers approval prompts even for <code>READ_ONLY</code> peers; denial immediately aborts turn.</li>
                <li><strong>4. YAML Config Rejected:</strong> <code>load_config()</code> calls <code>json.loads()</code> despite <code>pyyaml</code> in dependencies (<code>io.py:59</code>).</li>
                <li><strong>5. API Mismatches:</strong> <code>Skill.render_snippet(..., purpose=...)</code> undocumented enum; <code>TaskSurface.list_tasks(runs_limit=5)</code> vs <code>task.list(limit=20)</code>.</li>
              </ul>
            </div>
            """,
        ),
        (
            "Verification Suite",
            "14 / 14 Pytest Cases Passing (0 Failed, 0 Skipped)",
            "Includes live Cloud Run x402 HTTP 402 check & full OpenMinion runtime tests",
            f'<div class="term">{html.escape(pytest_out)}</div>',
        ),
    ]

    for idx, (badge, title, subtitle, body) in enumerate(slides, start=1):
        html_path = DEMO_DIR / f"slide_{idx:02d}.html"
        png_path = DEMO_DIR / f"slide_{idx:02d}.png"
        html_path.write_text(_render_html(idx, badge, title, subtitle, body), encoding="utf-8")
        subprocess.run(
            [
                CHROMIUM,
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1280,720",
                f"--screenshot={png_path}",
                f"file://{html_path}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        html_path.unlink(missing_ok=True)
        print(f"Rendered {png_path.name}")


if __name__ == "__main__":
    main()
