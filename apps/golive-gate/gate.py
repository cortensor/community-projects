"""Go-Live Gate: an OpenMinion agent that decides whether a website is ready to launch.

Usage:
    python gate.py example.com [--auto-approve yes|no] [--config .om/home/.openminion/agents.json]

The agent calls read-only tools (checks.py), returns a pydantic-validated
GoLiveReport, and must ask a human before the dangerous `save_report` tool
writes anything to disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from openminion import Agent, ProviderError, tool
from openminion.api.agent import AgentOutputValidationError
from openminion.services.runtime.ingress.types import TurnTimeoutError

import checks

ROOT = Path(__file__).parent


def pace_provider(tpm: int) -> None:
    """Keep provider calls under a tokens-per-minute budget (free tiers such as Groq allow 8k TPM).

    shortcut: patches the OpenAI-compatible adapter's HTTP call; upgrade when OpenMinion exposes rate pacing.
    """
    import openminion.modules.llm.providers.openai.adapter as adapter

    sent: list[tuple[float, int]] = []
    post = adapter._http_json_post

    def paced(**kw):
        need = len(json.dumps(kw.get("payload", {}))) // 3 + 1500  # rough prompt tokens + output headroom
        while True:
            now = time.time()
            sent[:] = [(t, n) for t, n in sent if now - t < 60]
            if sum(n for _, n in sent) + need <= tpm or not sent:
                break
            time.sleep(max(1.0, 60 - (now - sent[0][0])))
        msgs = kw.get("payload", {}).get("messages", [])
        print(f"[provider] call ~{need - 1500} prompt tokens, {len(msgs)} messages", flush=True)
        if os.environ.get("GOLIVE_DUMP"):
            Path(os.environ["GOLIVE_DUMP"]).mkdir(exist_ok=True)
            (Path(os.environ["GOLIVE_DUMP"]) / f"{time.time():.3f}.json").write_text(json.dumps(kw.get("payload"), indent=1))
        out = post(**kw)
        sent.append((time.time(), int((out.get("usage") or {}).get("total_tokens") or need)))
        return out

    adapter._http_json_post = paced
OUT = ROOT / "out"
_SITE: dict[str, object] = {}  # facts gathered this run, reused by save_report


class Check(BaseModel):
    name: str = Field(description="short id, e.g. title, canonical, og, json_ld, robots_ai, sitemap, llms_txt, real_404, icons")
    status: Literal["pass", "warn", "fail"]
    evidence: str = Field(description="the fact from a tool result that justifies the status")
    fix: str = Field(default="", description="one concrete fix when status is warn or fail")


class GoLiveReport(BaseModel):
    site: str
    verdict: Literal["ready", "ready_with_warnings", "blocked"]
    checks: list[Check]
    summary: str = Field(description="two sentences a site owner understands")


@tool(name="plugin.golive.inspect_home", idempotent=True, tags=("read_only",), capabilities=("read_only", "network"))
def inspect_home(site: str) -> str:
    """Fetch the home page and return its head facts (title, description, canonical, og:*, JSON-LD types, h1, icons)."""
    _collect("inspect_home", site)
    return json.dumps(_SITE["home"])


@tool(name="plugin.golive.inspect_crawlers", idempotent=True, tags=("read_only",), capabilities=("read_only", "network"))
def inspect_crawlers(site: str) -> str:
    """Return robots.txt facts (AI crawlers blocked), sitemap facts and llms.txt / llms-full.txt facts."""
    _collect("inspect_crawlers", site)
    return json.dumps(_SITE["crawlers"])


@tool(name="plugin.golive.inspect_404", idempotent=True, tags=("read_only",), capabilities=("read_only", "network"))
def inspect_404(site: str) -> str:
    """Request a path that does not exist and report whether the site answers a real HTTP 404."""
    _collect("inspect_404", site)
    return json.dumps(_SITE["404"])


@tool(name="plugin.golive.save_report", dangerous=True)
def save_report(site: str, verdict: str, markdown: str) -> str:
    """Write the final go-live report (markdown) and the raw facts to out/<site>-<timestamp>/. Requires human approval."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = OUT / f"{checks.origin(site).split('://')[1]}-{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.md").write_text(markdown)
    (d / "facts.json").write_text(json.dumps({"verdict": verdict, **_SITE}, indent=2))
    return f"saved {d}"


def register_tool_manifests(tools) -> None:
    """Workaround documented by another builder for 0.1.4 (decorated tools missing from the model-visible set).
    On 0.1.14 our tools were reached with and without it (README finding 2); kept because it is harmless."""
    from openminion.modules.tool.framework import derive_manifest
    from openminion.modules.tool.runtime.dispatch import get_registry_manager

    manager = get_registry_manager()
    for fn in tools:
        try:
            manager.register_module_manifest(derive_manifest(fn.tool_family_spec()), source_module="golive")
        except Exception as exc:
            if "duplicate" not in str(exc).lower():
                raise


def _collect(name: str, site: str) -> None:
    name = name.rsplit(".", 1)[-1]
    if name == "inspect_home":
        _SITE["home"] = checks.page_facts(checks.origin(site) + "/")
    elif name == "inspect_crawlers":
        robots = checks.robots_facts(site)
        _SITE["crawlers"] = {"robots": robots, "sitemap": checks.sitemap_facts(site, robots.get("sitemaps") or None),
                             "llms": checks.llms_facts(site)}
    else:
        _SITE["404"] = checks.not_found_facts(site)


READ_ONLY = {"plugin.golive.inspect_home": "home", "plugin.golive.inspect_crawlers": "crawlers", "plugin.golive.inspect_404": "404"}

INVESTIGATOR = """You are the investigator of Go-Live Gate. Call plugin.golive.inspect_home, plugin.golive.inspect_crawlers
and plugin.golive.inspect_404
for the site you are given, each exactly once, then reply with one short line per tool saying what it found.
Never invent a fact you did not get from a tool."""

INSTRUCTIONS = """You are Go-Live Gate, a strict pre-launch reviewer for small-business websites.
You receive the raw facts the investigator's tools collected. Never invent a fact that is not in them.
Judge these checks: title (10-65 chars), description (50-160 chars), canonical present, og (og:title, og:description, og:image),
   json_ld (at least one type; INVALID_JSON_LD is a fail), lang, icons (favicon and apple-touch-icon),
   robots_ai (no listed AI crawler blocked), sitemap (HTTP 200 with at least one <loc>), llms_txt (/llms.txt ok),
   real_404 (missing page answers 404).
Verdict: blocked if title, canonical, sitemap or real_404 fails or the home page is not HTTP 200;
   ready_with_warnings if anything else is warn/fail; ready otherwise.
Reply with exactly one JSON object that matches the schema in the message, and nothing else."""


def judge_facts(site: str, config: str | None, session: str):
    """Structured verdict from the facts; one corrective retry when the model answers in prose."""
    # Schema and facts travel in the message: the end of long instructions did not reach the model, and a
    # follow-up run in the same session did not see the previous message (README findings 4 and 5).
    msg = json.dumps({"site": site, "facts": _SITE, "reply_schema": GoLiveReport.model_json_schema(),
                      "reply_format": "only one JSON object matching reply_schema, no markdown"})
    with Agent(instructions=INSTRUCTIONS, output_type=GoLiveReport, config_path=config, session_id=session) as judge:
        try:
            return judge.run(msg, timeout_seconds=600)
        except AgentOutputValidationError as exc:
            print(f"[judge] reply was not JSON ({len(exc.raw_text or '')} chars of prose); asking once more")
            return judge.run("Your previous reply was prose. " + msg, timeout_seconds=600)


def run(site: str, auto: str | None, config: str | None) -> int:
    def approve(tool_name: str, args: dict, reason: str) -> bool:
        # The default action policy still asks for read-only, idempotent tools (see README finding 1).
        if tool_name in READ_ONLY:
            print(f"[approval] {tool_name} -> read-only, allowed")
            return True
        if auto:
            print(f"[approval] {tool_name} -> auto {auto}")
            return auto == "yes"
        return input(f"Allow {tool_name} to write the report for {args.get('site')}? [y/N] ").strip().lower() == "y"

    t0 = time.time()
    session = f"golive-{checks.origin(site).split('://')[1]}-{int(t0)}"
    # Two agents on purpose: with output_type set, OpenMinion 0.1.14 exposes only submit_output to the model,
    # so tools and structured output cannot share one turn (README finding 2).
    _SITE.clear()
    register_tool_manifests([inspect_home, inspect_crawlers, inspect_404, save_report])
    with Agent(instructions=INVESTIGATOR, tools=[inspect_home, inspect_crawlers, inspect_404],
               config_path=config, session_id=session) as investigator:
        try:
            inv = investigator.run(f"Investigate {site}.", approval_callback=approve, timeout_seconds=600)
            print(f"[investigator] run_id={inv.run_id} {time.time() - t0:.1f}s\n{inv.text}")
        except TurnTimeoutError:
            print(f"[investigator] turn timed out after {time.time() - t0:.1f}s; tools already ran: {sorted(_SITE)}")
    missing = sorted(n for n, key in READ_ONLY.items() if key not in _SITE)
    if missing:  # the model skipped a tool: fill the gap instead of letting the judge guess
        print(f"[investigator] model skipped {missing}; collecting deterministically")
        for name in missing:
            _collect(name, site)
    res = judge_facts(site, config, session + "-judge")
    report: GoLiveReport = res.output
    stats = getattr(res, "stats", None)
    print(f"[judge] run_id={getattr(res, 'run_id', '?')} state={getattr(res, 'run_state', '?')} {time.time() - t0:.1f}s")

    md = [f"# Go-Live Gate: {report.site}", "", f"**Verdict: {report.verdict}**", "", report.summary, "",
          "| check | status | evidence | fix |", "|---|---|---|---|"]
    md += [f"| {c.name} | {c.status} | {c.evidence} | {c.fix} |" for c in report.checks]
    markdown = "\n".join(md) + "\n"
    print(markdown)

    # Publishing is a separate, tool-forced turn so the dangerous call always goes through approval.
    with Agent(instructions="Call save_report exactly once with the given arguments, then reply 'done'.",
               tools=[save_report], forced_tools=["plugin.golive.save_report"], config_path=config,
               session_id=session + "-publish") as publisher:
        pub = publisher.run(json.dumps({"site": report.site, "verdict": report.verdict, "markdown": markdown}),
                            approval_callback=approve, timeout_seconds=600)
    print(f"[publish] {pub.text}")
    if stats is not None:
        print(f"[stats] {stats}")
    return 0 if report.verdict != "blocked" else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("site")
    ap.add_argument("--auto-approve", choices=["yes", "no"])
    ap.add_argument("--config", default=str(ROOT / ".om/home/.openminion/agents.json"))
    ap.add_argument("--tpm", type=int, default=0, help="tokens-per-minute budget for free tiers, e.g. 6500 on Groq (0 = no pacing)")
    a = ap.parse_args()
    if a.tpm:
        pace_provider(a.tpm)
    for attempt in range(4):
        try:
            return run(a.site, a.auto_approve, a.config)
        except ProviderError as exc:
            # Free tiers reset tokens-per-minute every 60 s; anything else is a real failure.
            if "RATE_LIMITED" not in str(exc) or attempt == 3:
                print(f"provider failed: {exc}", file=sys.stderr)
                return 1
            print(f"[retry] rate limited, waiting 65 s (attempt {attempt + 1})", file=sys.stderr)
            time.sleep(65)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
