#!/usr/bin/env python3
"""TriageMinion — a GitHub issue triage agent built on the OpenMinion 0.1 Python SDK.

Workflow (one repeatable run):
  1. Fetch open issues from a public GitHub repo (REST API, no token required).
  2. Skip issues already triaged in a previous run whose `updated_at` has not
     changed (durable memory: `.triageminion-state.json`).
  3. For every new/changed issue, an OpenMinion `Agent` (real model) must:
       - call the READ_ONLY tool `get_issue` to load the full issue body,
       - classify it (bug / feature / question / docs), assign a priority
         (critical / high / medium / low) with a one-line justification,
         suggest labels, and draft a maintainer response,
       - persist the verdict ONLY through the approval-gated tool
         `save_triage_record` (permissions block: a human approval callback
         decides; `--auto-approve yes|no` for non-interactive runs).
  4. Write `triage-report.md` + `triage-report.json` locally. The agent never
     posts anything to GitHub — triage is read-only by design.

The OpenMinion SDK is the runtime: agent execution, model/provider routing,
tools, permissions (approval callback), sessions (one session per target repo,
continued across issues and runs), typed structured output (Pydantic), and
typed errors (ProviderError / TurnTimeoutError / AgentOutputValidationError).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openminion import (
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
    tool,
)

# --------------------------------------------------------------------------- #
# Typed structured output (OpenMinion `output_type`)
# --------------------------------------------------------------------------- #


class TriageVerdict(BaseModel):
    """One issue's triage verdict, validated by the SDK against this schema."""

    issue_number: int
    classification: Literal["bug", "feature", "question", "docs"]
    priority: Literal["critical", "high", "medium", "low"]
    suggested_labels: list[str] = Field(default_factory=list)
    justification: str  # one line: why this classification + priority
    draft_response: str  # short maintainer reply the human may post manually


# --------------------------------------------------------------------------- #
# Run-scoped state shared with the tools (populated per CLI invocation)
# --------------------------------------------------------------------------- #

ISSUE_CACHE: dict[int, dict] = {}
SAVED_RECORDS: list[dict] = []
STAGING_PATH: Path | None = None


# --------------------------------------------------------------------------- #
# OpenMinion tools
# --------------------------------------------------------------------------- #


@tool(min_scope="READ_ONLY", idempotent=True)
def get_issue(issue_number: int) -> str:
    """Return the full title, body, labels and comment count for one issue."""
    issue = ISSUE_CACHE.get(int(issue_number))
    if issue is None:
        return f"error: issue #{issue_number} is not in the fetched set"
    body = (issue.get("body") or "").strip()
    if len(body) > 3000:
        body = body[:3000] + "\n...[body truncated at 3000 chars]"
    labels = ", ".join(label["name"] for label in issue.get("labels", [])) or "(none)"
    return (
        f"Issue #{issue['number']}: {issue['title']}\n"
        f"Author: {issue['user']['login']}  Created: {issue['created_at']}  "
        f"Updated: {issue['updated_at']}  Comments: {issue['comments']}\n"
        f"Existing labels: {labels}\n"
        f"URL: {issue['html_url']}\n\nBody:\n{body or '(empty body)'}"
    )


@tool(dangerous=True)
def save_triage_record(
    issue_number: int,
    classification: str,
    priority: str,
    suggested_labels: str,
    justification: str,
    draft_response: str,
) -> str:
    """Persist one triage verdict to the local staging file.

    This is the only write tool. It is marked dangerous, so OpenMinion routes
    every call through the run's approval callback (the permissions gate)
    before it executes. `suggested_labels` is a comma-separated string.
    """
    record = {
        "issue_number": int(issue_number),
        "classification": classification,
        "priority": priority,
        "suggested_labels": [s.strip() for s in suggested_labels.split(",") if s.strip()],
        "justification": justification,
        "draft_response": draft_response,
        "saved_via": "save_triage_record tool (approval-gated)",
    }
    SAVED_RECORDS.append(record)
    if STAGING_PATH is not None:
        with STAGING_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return f"saved triage record for issue #{issue_number}"


# --------------------------------------------------------------------------- #
# Environment workaround for an OpenMinion/httpx interop bug (see FINDINGS F1)
# --------------------------------------------------------------------------- #


def sanitize_proxy_env() -> None:
    """Drop bracketed IPv6 entries (e.g. ``[::1]``) from NO_PROXY/no_proxy.

    OpenMinion 0.1.24's ProviderHTTPClient builds ``httpx.Client(trust_env=True)``
    unconditionally; httpx 0.29.0 raises ``InvalidURL: Invalid port: ':1]'`` while
    parsing bracketed IPv6 literals in NO_PROXY, which kills every provider call
    before it starts. Unbracketed entries (127.0.0.1, localhost, ::1) keep working.
    """
    for key in ("NO_PROXY", "no_proxy"):
        raw = os.environ.get(key)
        if not raw:
            continue
        entries = [e.strip() for e in raw.split(",") if e.strip()]
        kept = [e for e in entries if not (e.startswith("[") and e.endswith("]"))]
        if len(kept) != len(entries):
            print(f"[env] removed {len(entries) - len(kept)} bracketed IPv6 entries from {key} "
                  "(workaround for the OpenMinion/httpx NO_PROXY bug, FINDINGS F1)")
            os.environ[key] = ",".join(kept)


# --------------------------------------------------------------------------- #
# GitHub fetch (deterministic, outside the model loop)
# --------------------------------------------------------------------------- #


def fetch_open_issues(repo: str, limit: int) -> list[dict]:
    """Fetch the most recently created open issues (PRs excluded)."""
    url = (
        f"https://api.github.com/repos/{repo}/issues"
        f"?state=open&per_page=100&sort=created&direction=desc"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.load(resp)
    issues = [i for i in items if "pull_request" not in i]
    return issues[:limit]


# --------------------------------------------------------------------------- #
# Memory: durable per-repo state across runs
# --------------------------------------------------------------------------- #


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"repos": {}}


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def plan_work(issues: list[dict], repo_state: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Split issues into (to_triage, changed, skipped) using stored memory."""
    known = repo_state.get("issues", {})
    to_triage, changed, skipped = [], [], []
    for issue in issues:
        prev = known.get(str(issue["number"]))
        if prev is None:
            to_triage.append(issue)
        elif prev.get("updated_at") != issue["updated_at"]:
            changed.append(issue)
        else:
            skipped.append(issue)
    return to_triage, changed, skipped


# --------------------------------------------------------------------------- #
# Report rendering
# --------------------------------------------------------------------------- #


def render_report(
    repo: str,
    verdicts: list[dict],
    skipped: list[dict],
    changed: list[dict],
    failures: list[dict],
    model_label: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Triage report — {repo}",
        "",
        f"Generated by TriageMinion (OpenMinion SDK) · {now} · model: {model_label}",
        "",
        f"- Newly triaged this run: **{len(verdicts)}**",
        f"- Changed since last run (re-triaged): **{len(changed)}**",
        f"- Skipped (already triaged, unchanged): **{len(skipped)}**",
        f"- Failed this run: **{len(failures)}**",
        "",
    ]
    for v in verdicts:
        lines += [
            f"## Issue #{v['issue_number']} — {v.get('title', '')}".rstrip(),
            "",
            f"- **Classification:** {v['classification']}",
            f"- **Priority:** {v['priority']}",
            f"- **Suggested labels:** {', '.join(v['suggested_labels']) or '(none)'}",
            f"- **Why:** {v['justification']}",
            f"- **URL:** {v.get('html_url', '')}",
            "",
            "**Draft maintainer response:**",
            "",
            f"> {v['draft_response']}",
            "",
        ]
    if skipped:
        lines += ["## Skipped (unchanged since previous run)", ""]
        for s in skipped:
            lines.append(f"- #{s['number']} — {s['title']}")
        lines.append("")
    if failures:
        lines += ["## Failures", ""]
        for f in failures:
            lines.append(f"- #{f['issue_number']}: {f['error']}")
        lines.append("")
    lines.append("_Read-only triage: nothing was posted to GitHub. Drafts are for a human to post._")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# Provider config bootstrap (OpenMinion setup, project-scoped)
# --------------------------------------------------------------------------- #


def ensure_config(config_path: Path, provider: str, model: str) -> None:
    """Create the project-scoped OpenMinion config via the official CLI setup."""
    if config_path.exists():
        _patch_provider_timeout(config_path, provider)
        return
    env = dict(os.environ)
    # `openminion setup` resolves its config under $OPENMINION_HOME/.openminion/
    env["OPENMINION_HOME"] = str(config_path.parent.parent)
    cli = Path(sys.executable).parent / "openminion"
    cmd = [
        str(cli) if cli.exists() else "openminion", "setup",
        "--provider", provider, "--model", model, "--no-chat",
    ]
    print(f"[setup] creating config: {' '.join(cmd)}")
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=180)
    if not config_path.exists():
        raise SystemExit(
            "Could not create OpenMinion config. Run manually:\n"
            f"  OPENMINION_HOME={config_path.parent.parent} openminion setup "
            f"--provider {provider} --model {model} --no-chat\n"
            f"setup stderr: {proc.stderr[-500:]}"
        )
    _patch_provider_timeout(config_path, provider)


def _patch_provider_timeout(config_path: Path, provider: str) -> None:
    # Local-CPU-model config patches (FINDINGS F2/F3):
    # - `openminion setup` defaults provider timeout_seconds to 60 and
    #   runtime.brain_turn_timeout_seconds to 300; one /api/chat call for a
    #   tool-using turn can take minutes on CPU, so both are raised.
    # - runtime.memory_enabled is turned OFF: the SDK's automatic memory
    #   extraction spends a full extra model request per turn, which costs
    #   ~10 minutes per issue on a local model. TriageMinion's durable memory
    #   is its explicit state file; the SDK session store still persists.
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        changed = False
        prov = cfg.get("providers", {}).get(provider)
        if isinstance(prov, dict) and float(prov.get("timeout_seconds", 0)) < 900:
            prov["timeout_seconds"] = 900
            changed = True
            print(f"[setup] raised providers.{provider}.timeout_seconds to 900")
        if provider == "ollama" and isinstance(prov, dict) and prov.get("tool_call_strategy") != "hybrid":
            # The ollama preset defaults to the text "fallback" tool strategy;
            # tool-capable local models (Qwen2.5 etc.) follow native tool
            # definitions far more reliably. "hybrid" enables both. (F7)
            prov["tool_call_strategy"] = "hybrid"
            changed = True
            print("[setup] set providers.ollama.tool_call_strategy=hybrid")
        runtime = cfg.get("runtime", {})
        if float(runtime.get("brain_turn_timeout_seconds", 0)) < 2400:
            runtime["brain_turn_timeout_seconds"] = 2400
            changed = True
            print("[setup] raised runtime.brain_turn_timeout_seconds to 2400")
        if float(runtime.get("chat_turn_timeout_seconds", 0)) < 2400:
            runtime["chat_turn_timeout_seconds"] = 2400
            changed = True
        if runtime.get("memory_enabled"):
            runtime["memory_enabled"] = False
            changed = True
            print("[setup] set runtime.memory_enabled=false (local-model latency, FINDINGS F3)")
        if changed:
            config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as exc:  # never block the run on config cosmetics
        print(f"[setup] config patch skipped: {exc}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

INSTRUCTIONS = (
    "You are TriageMinion, a GitHub issue triage agent. For the issue you are "
    "given, you MUST first call the get_issue tool to read its full body. Then "
    "decide: classification is exactly one of bug, feature, question, docs; "
    "priority is exactly one of critical, high, medium, low. Then you MUST call "
    "the save_triage_record tool with your verdict (suggested_labels as a "
    "comma-separated string, justification of at most 12 words, and a polite "
    "draft maintainer response of at most 30 words). Be terse everywhere. "
    "Finally reply with ONLY a compact JSON object with fields: issue_number, "
    "classification, priority, suggested_labels (a list of strings), "
    "justification, draft_response."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Textualize/rich", help="owner/name")
    parser.add_argument("--limit", type=int, default=5, help="max open issues to consider")
    parser.add_argument("--provider", default=os.environ.get("OPENMINION_PROVIDER", "ollama"))
    parser.add_argument("--model", default=os.environ.get("OPENMINION_MODEL", "qwen2.5:3b"))
    parser.add_argument("--auto-approve", choices=["yes", "no", "ask"], default="ask",
                        help="approval policy for the write tool (default: ask on TTY)")
    parser.add_argument("--out-dir", default=".", help="where reports are written")
    parser.add_argument("--state", default=".triageminion-state.json")
    parser.add_argument("--timeout", type=float, default=600.0, help="per-issue turn timeout (s)")
    args = parser.parse_args()

    sanitize_proxy_env()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    global STAGING_PATH
    STAGING_PATH = out_dir / "triage-staging.jsonl"

    config_path = Path(".openminion/agents.json").resolve()
    ensure_config(config_path, args.provider, args.model)

    print(f"[triage] fetching open issues from {args.repo} (limit {args.limit}) ...")
    issues = fetch_open_issues(args.repo, args.limit)
    for issue in issues:
        ISSUE_CACHE[issue["number"]] = issue
    print(f"[triage] fetched {len(issues)} open issues")

    state = load_state(Path(args.state))
    repo_state = state["repos"].setdefault(args.repo, {"issues": {}})
    fresh, changed, skipped = plan_work(issues, repo_state)
    work = fresh + changed
    print(f"[memory] new={len(fresh)} changed={len(changed)} skipped={len(skipped)}")
    for s in skipped:
        print(f"[memory] skip #{s['number']} (unchanged since last run)")

    # --- permissions: approval callback gates the dangerous write tool ----- #
    def approval_callback(tool_name: str, tool_args: dict, approval_id: str) -> bool:
        if tool_name != "save_triage_record":
            print(f"[approval] DENY unexpected tool {tool_name} ({approval_id})")
            return False
        summary = f"#{tool_args.get('issue_number')} {tool_args.get('classification')}/{tool_args.get('priority')}"
        if args.auto_approve == "yes":
            print(f"[approval] AUTO-APPROVE save_triage_record {summary}")
            return True
        if args.auto_approve == "no":
            print(f"[approval] AUTO-DENY save_triage_record {summary}")
            return False
        answer = input(f"[approval] Allow save_triage_record {summary}? [y/N] ").strip().lower()
        return answer in {"y", "yes"}

    verdicts: list[dict] = []
    failures: list[dict] = []
    session_id = f"triageminion-{args.repo.replace('/', '-')}"
    model_label = f"{args.provider}/{args.model}"

    if work:
        with Agent(
            instructions=INSTRUCTIONS,
            tools=[get_issue, save_triage_record],
            output_type=TriageVerdict,
            session_id=session_id,
            config_path=str(config_path),
        ) as agent:
            for issue in work:
                num = issue["number"]
                print(f"\n[triage] === issue #{num}: {issue['title'][:80]}")
                started = time.time()
                saved_before = len(SAVED_RECORDS)
                result = None
                last_error = ""
                # Small local models occasionally drop required fields or skip
                # the tools; one corrective retry with the failure spelled out
                # (and the issue body inline) recovers most of those turns.
                for attempt in (1, 2):
                    if attempt == 1:
                        prompt = f"Triage issue #{num} of {args.repo}. Its title is: {issue['title']}"
                    else:
                        print(f"[retry] issue #{num}: {last_error}")
                        prompt = (
                            f"Your previous triage attempt for issue #{num} failed: {last_error}. "
                            f"Here is the full issue text:\n\n{get_issue(num)}\n\n"
                            "Now call save_triage_record with the complete verdict, then reply "
                            "with ONLY the complete JSON object containing ALL six fields: "
                            "issue_number, classification, priority, suggested_labels, "
                            "justification, draft_response."
                        )
                    try:
                        result = agent.run(
                            prompt,
                            approval_callback=approval_callback,
                            timeout_seconds=args.timeout,
                        )
                        break
                    except ProviderError as exc:
                        last_error = f"ProviderError {exc.code}: {exc.message}"
                        result = None
                        break
                    except TurnTimeoutError as exc:
                        last_error = f"TurnTimeoutError: {exc}"
                        result = None
                        break
                    except AgentOutputValidationError as exc:
                        last_error = f"invalid output (missing/invalid fields): {exc.raw_text[:160]}"
                        result = None
                        # If the verdict was already persisted through the
                        # approval-gated tool, do not retry: small models tend
                        # to loop on repeated save calls (FINDINGS F8). The
                        # recovery path below uses the tool record.
                        if any(r["issue_number"] == num for r in SAVED_RECORDS[saved_before:]):
                            print(f"[recover-pending] issue #{num}: tool record exists, skipping retry")
                            break
                        continue
                if result is None:
                    # Recovery path: if the model persisted its verdict through
                    # the approval-gated tool but the turn's final structured
                    # reply failed validation or timed out, the tool record IS
                    # the verdict — use it instead of discarding the issue.
                    recovered = next(
                        (r for r in SAVED_RECORDS[saved_before:] if r["issue_number"] == num),
                        None,
                    )
                    if recovered is not None:
                        print(f"[recover] issue #{num}: using approval-gated tool record "
                              f"after turn failure ({last_error})")
                        verdict = {
                            "issue_number": num,
                            "classification": str(recovered["classification"]).lower(),
                            "priority": str(recovered["priority"]).lower(),
                            "suggested_labels": recovered["suggested_labels"],
                            "justification": recovered["justification"],
                            "draft_response": recovered["draft_response"],
                            "title": issue["title"],
                            "html_url": issue["html_url"],
                            "elapsed_seconds": round(time.time() - started, 1),
                            "persisted_via_tool": True,
                            "recovered_from_tool_record": True,
                        }
                        verdicts.append(verdict)
                        repo_state["issues"][str(num)] = {
                            "updated_at": issue["updated_at"],
                            "classification": verdict["classification"],
                            "priority": verdict["priority"],
                            "triaged_at": datetime.now(timezone.utc).isoformat(),
                        }
                        continue
                    failures.append({"issue_number": num, "error": last_error})
                    print(f"[error] issue #{num} failed: {last_error}")
                    continue
                elapsed = time.time() - started
                verdict = result.output.model_dump()
                verdict["title"] = issue["title"]
                verdict["html_url"] = issue["html_url"]
                verdict["elapsed_seconds"] = round(elapsed, 1)
                verdict["persisted_via_tool"] = len(SAVED_RECORDS) > saved_before
                verdict["recovered_from_tool_record"] = False
                verdicts.append(verdict)
                print(f"[triage] #{num} -> {verdict['classification']}/{verdict['priority']} "
                      f"labels={verdict['suggested_labels']} ({elapsed:.0f}s, "
                      f"tool-persisted={verdict['persisted_via_tool']}, session={result.session_id})")
                repo_state["issues"][str(num)] = {
                    "updated_at": issue["updated_at"],
                    "classification": verdict["classification"],
                    "priority": verdict["priority"],
                    "triaged_at": datetime.now(timezone.utc).isoformat(),
                }

    save_state(Path(args.state), state)

    report_md = render_report(args.repo, verdicts, skipped, changed, failures, model_label)
    (out_dir / "triage-report.md").write_text(report_md, encoding="utf-8")
    (out_dir / "triage-report.json").write_text(
        json.dumps(
            {"repo": args.repo, "model": model_label, "verdicts": verdicts,
             "skipped": [s["number"] for s in skipped], "failures": failures},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\n[done] triaged={len(verdicts)} skipped={len(skipped)} failed={len(failures)}")
    print(f"[done] wrote {out_dir / 'triage-report.md'} and triage-report.json")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
