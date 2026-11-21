"""Smoke test for docs/browser-preview/index.html (the try-out page source).

Static checks (no network, always run):
- the page exists and its <script> block parses (node --check when available)
- the audit hardening is present: response_format json_object on the triage
  call only, 105 s per-attempt timeout, Retry-After handling, one bounded
  auto-retry with max(47 s, Retry-After), tool_calls envelope parsing,
  label filtering against the repo's real label list, cooldown remembered
  in localStorage, Start disabled while in flight
- the #778 prefill matches fixtures/openminion-issue-778.json

Live check (--live, 1 Pollinations call, $0): POST the page's exact triage
request shape (response_format json_object, #778 title + body) and verify
the reply parses to JSON with all 7 required keys. Skip with --no-live.

Usage: python3 scripts/smoke_browser_preview.py [--live | --no-live]
Exit 0 = all checks pass.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "browser-preview" / "index.html"
FIXTURE = ROOT / "fixtures" / "openminion-issue-778.json"
API = "https://text.pollinations.ai/openai/v1/chat/completions"

TRIAGE_KEYS = {
    "issue_type", "severity", "component", "suggested_labels",
    "route", "confidence", "rationale",
}


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def static_checks() -> bool:
    print("== static checks ==")
    ok = True
    html = PAGE.read_text(encoding="utf-8")
    ok &= check("page exists and is non-trivial", PAGE.exists() and len(html) > 10_000,
                f"{len(html)} bytes")
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    ok &= check("exactly one inline <script> block", len(scripts) == 1,
                f"found {len(scripts)}")
    js = scripts[0] if scripts else ""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        js_path = f.name
    try:
        r = subprocess.run(["node", "--check", js_path],
                           capture_output=True, text=True, timeout=30)
        ok &= check("inline JS parses (node --check)", r.returncode == 0,
                    r.stderr.strip()[:200] or "ok")
    except FileNotFoundError:
        print("  [SKIP] node not available — JS parse check skipped")
    ok &= check("triage sends response_format json_object",
                "response_format" in js and "json_object" in js)
    ok &= check("per-attempt timeout is 105 s", "105000" in js)
    ok &= check("Retry-After header is read on 402",
                'get("Retry-After")' in js or "Retry-After" in js)
    ok &= check("one bounded auto-retry with max(47, Retry-After)",
                "Math.max(47" in js and "triageRetried" in js)
    ok &= check("tool_calls envelope parsed",
                "tool_calls" in js and "function.arguments" in js)
    ok &= check("Start disabled while in flight",
                "triageBtn.disabled = true" in js)
    ok &= check("cooldown remembered in localStorage",
                "localStorage" in js and "cortensor-triage-next-allowed" in js)
    # Triage call passes jsonMode=true; the brief call must not.
    triage_calls = re.findall(r"callModel\(\[.*?\]\)", js, re.S)
    ok &= check("triage call passes jsonMode=true",
                any("800, true" in c for c in triage_calls),
                f"{len(triage_calls)} callModel sites")
    ok &= check("brief call does NOT request json_object",
                any("900)" in c for c in triage_calls))
    # Label list matches the fixture exactly.
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    repo_labels = fixture["_repo_labels"]
    m = re.search(r"var REPO_LABELS = \[(.*?)\];", js, re.S)
    if m:
        page_labels = json.loads("[" + m.group(1) + "]")
        ok &= check("REPO_LABELS matches fixture _repo_labels",
                    page_labels == repo_labels,
                    f"{len(page_labels)} labels")
    else:
        ok &= check("REPO_LABELS present", False)
    ok &= check("page labels the preview as simplified one-call",
                "简化版预览" in html and "只做分类一步" in html)
    ok &= check("#778 title prefilled from fixture",
                fixture["title"] in html)
    ok &= check("#778 body embedded (issueBodySrc)",
                'id="issueBodySrc"' in html
                and "completion still rests on confidence" in html)
    return ok


def live_check() -> bool:
    print("== live check (1 Pollinations call, $0) ==")
    import urllib.request

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    body_text = fixture["body"][:6000]
    system = (
        "You are an issue triage classifier for a GitHub repository. Read the "
        "issue and reply with STRICT JSON ONLY (no markdown, no prose) with "
        "exactly these keys: "
        '{"issue_type": one of "bug"|"feature"|"question"|"docs"|"chore"|"duplicate", '
        '"severity": one of "critical"|"high"|"medium"|"low", '
        '"component": short module name as a plain string, '
        '"suggested_labels": array of up to 4 label strings, '
        '"route": one of "ready-to-fix"|"needs-info"|"good-first-issue"|"needs-maintainer"|"needs-design"|"duplicate"|"wontfix-candidate", '
        '"confidence": number between 0 and 1, '
        '"rationale": 1-3 sentences explaining the verdict with evidence from the issue}'
    )
    payload = {
        "model": "openai",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Issue title: {fixture['title']}\n\nIssue body:\n{body_text}"},
        ],
        "reasoning_effort": "low",
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=105) as resp:
            data = json.loads(resp.read())
    except Exception as exc:  # noqa: BLE001
        return check("live triage call succeeds", False, str(exc)[:200])
    msg = data["choices"][0]["message"]
    content = msg.get("content") or (
        msg.get("tool_calls", [{}])[0].get("function", {}).get("arguments", "")
    )
    try:
        verdict = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return check("live reply is JSON", False, (content or "")[:200])
    ok = check("live reply has all 7 required keys",
               TRIAGE_KEYS <= set(verdict), f"keys={sorted(verdict)}")
    ok &= check("live reply type is bug (matches #778)",
                verdict.get("issue_type") == "bug",
                f"got {verdict.get('issue_type')}")
    print(f"  live verdict: {verdict.get('issue_type')}/{verdict.get('severity')} "
          f"route={verdict.get('route')} conf={verdict.get('confidence')}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="run the live 1-call check")
    ap.add_argument("--no-live", action="store_true", help="skip the live check")
    args = ap.parse_args()
    ok = static_checks()
    if args.live and not args.no_live:
        ok &= live_check()
    elif not args.no_live:
        print("== live check skipped (pass --live to run it) ==")
    print("SMOKE " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
