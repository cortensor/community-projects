"""Standalone dark-mode HTML security audit report generator."""

from __future__ import annotations

import html

from .models import FullAuditBundle


def render_html_report(bundle: FullAuditBundle) -> str:
    rep = bundle.structured_report
    grade_colors = {"A": "#22c55e", "B": "#4ade80", "C": "#facc15", "D": "#fb923c", "F": "#ef4444"}
    g_color = grade_colors.get(rep.overall_grade, "#38bdf8")

    probe_rows = "\n".join(
        f"""<tr>
          <td><code>{html.escape(p.vector_id)}</code></td>
          <td>{html.escape(p.category)}</td>
          <td><span class="sev sev-{p.severity.lower()}">{p.severity}</span></td>
          <td><span class="badge {'ok' if p.blocked and not p.canary_leaked else 'bad'}">{'BLOCKED' if p.blocked and not p.canary_leaked else 'BYPASS'}</span></td>
          <td>{'Yes' if p.approval_intercepted else 'N/A'}</td>
          <td class="mono">{html.escape(p.response_excerpt[:140])}</td>
        </tr>"""
        for p in bundle.live_attack_probes
    )

    static_rows = "\n".join(
        f"""<tr>
          <td><code>{html.escape(f.rule_id)}</code></td>
          <td><span class="sev sev-{f.severity.lower()}">{f.severity}</span></td>
          <td class="mono">{html.escape(f.file_path)}:{f.line_number} ({html.escape(f.function_name)})</td>
          <td>{html.escape(f.detail)}</td>
        </tr>"""
        for f in bundle.static_tool_findings
    ) or '<tr><td colspan="4" class="muted">Zero static @tool decorator issues detected in target workspace.</td></tr>'

    patches_li = "\n".join(f"<li>{html.escape(item)}</li>" for item in rep.openminion_patches)
    findings_li = "\n".join(f"<li>{html.escape(item)}</li>" for item in rep.top_findings)

    iso = bundle.session_isolation
    iso_pass = iso.shared_session_recalled and not iso.isolated_session_leaked

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Cortensor Prompt Shield — OpenMinion {html.escape(bundle.openminion_version)} Security Audit</title>
<style>
  :root {{ --bg:#080c12; --card:#101722; --border:#1f2d42; --text:#e2e8f0; --muted:#8aa0bc; --accent:#38bdf8; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,Inter,Segoe UI,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; }}
  .hdr {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px; border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px; }}
  h1 {{ margin:0; font-size:24px; letter-spacing:0.02em; }}
  .sub {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .grade-box {{ display:flex; align-items:center; gap:14px; background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 18px; }}
  .grade {{ font-size:36px; font-weight:800; color:{g_color}; line-height:1; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-bottom:18px; }}
  .kpi {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 14px; }}
  .kpi .k {{ font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:var(--muted); }}
  .kpi .v {{ font-size:20px; font-weight:700; margin-top:4px; color:#f8fafc; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px 18px; margin-bottom:16px; }}
  .card h2 {{ margin:0 0 12px; font-size:14px; text-transform:uppercase; letter-spacing:0.07em; color:var(--accent); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--border); vertical-align:top; }}
  th {{ color:var(--muted); font-size:11px; text-transform:uppercase; }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
  .muted {{ color:var(--muted); }}
  .badge {{ padding:3px 8px; border-radius:999px; font-size:11px; font-weight:700; }}
  .badge.ok {{ background:rgba(34,197,94,0.18); color:#4ade80; }}
  .badge.bad {{ background:rgba(239,68,68,0.2); color:#f87171; }}
  .sev {{ padding:2px 6px; border-radius:4px; font-size:11px; font-weight:700; }}
  .sev-critical,.sev-high {{ background:rgba(239,68,68,0.18); color:#f87171; }}
  .sev-medium {{ background:rgba(250,204,21,0.18); color:#facc15; }}
  .sev-low,.sev-info {{ background:rgba(56,189,248,0.16); color:#38bdf8; }}
  ul {{ margin:6px 0 0; padding-left:20px; line-height:1.6; }}
  .ftr {{ font-size:11.5px; color:var(--muted); font-family:ui-monospace,Menlo,monospace; margin-top:16px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div>
      <h1>Cortensor Prompt Shield — Security Audit Report</h1>
      <div class="sub">OpenMinion {html.escape(bundle.openminion_version)} · Provider: {html.escape(bundle.provider)} ({html.escape(bundle.model)}) · {html.escape(bundle.timestamp_utc)}</div>
    </div>
    <div class="grade-box">
      <div class="grade">{html.escape(rep.overall_grade)}</div>
      <div>
        <div style="font-weight:700;">Verdict: {html.escape(rep.cortensor_readiness_verdict)}</div>
        <div class="sub">Risk Score: {rep.risk_score_0_100} / 100</div>
      </div>
    </div>
  </div>

  <div class="grid">
    <div class="kpi"><div class="k">Live Probes Blocked</div><div class="v">{sum(1 for p in bundle.live_attack_probes if p.blocked and not p.canary_leaked)} / {len(bundle.live_attack_probes)}</div></div>
    <div class="kpi"><div class="k">Session Isolation</div><div class="v">{'PASS' if iso_pass else 'FAIL'}</div></div>
    <div class="kpi"><div class="k">Dangerous Write Gate</div><div class="v">{'DENY + ALLOW OK' if (bundle.write_gate_denied_verified and bundle.write_gate_approved_verified) else 'CHECK'}</div></div>
    <div class="kpi"><div class="k">Stream Events Observed</div><div class="v">{bundle.stream_events_observed}</div></div>
  </div>

  <div class="card">
    <h2>Executive Summary (Pydantic Structured Output)</h2>
    <p style="margin:0 0 10px; line-height:1.6;">{html.escape(rep.executive_summary)}</p>
    <strong>Prioritized Findings</strong>
    <ul>{findings_li}</ul>
    <strong style="display:block;margin-top:12px;">Concrete OpenMinion Hardening Patches</strong>
    <ul>{patches_li}</ul>
  </div>

  <div class="card">
    <h2>Live Adversarial Probes (Target Sandbox Subagent + Approval Callback)</h2>
    <table>
      <thead><tr><th>Vector</th><th>Category</th><th>Severity</th><th>Status</th><th>Gate Intercept</th><th>Response Excerpt</th></tr></thead>
      <tbody>{probe_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Static AST @tool Decorator Audit ({len(bundle.static_tool_findings)} Findings)</h2>
    <table>
      <thead><tr><th>Rule</th><th>Severity</th><th>Location</th><th>Detail</th></tr></thead>
      <tbody>{static_rows}</tbody>
    </table>
  </div>

  <div class="ftr">SHA-256 Attestation: {html.escape(bundle.report_sha256)} · Target: {html.escape(bundle.target_path)}</div>
</div>
</body>
</html>
"""
