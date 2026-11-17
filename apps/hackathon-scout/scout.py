"""Hackathon Scout: an OpenMinion agent that turns a hackathon or bounty page
into a structured brief and a submission checklist.

Usage:
    python scout.py <url> [<url> ...]          # brief + checklist for each page
    python scout.py --yes <url>                # auto-approve writing the checklist

Workflow (repeatable, one URL at a time):
    1. fetch_page (read-only tool) downloads the page and reduces it to text.
    2. The model records a typed HackathonBrief through the submit_brief tool.
    3. save_checklist (write tool) asks for human approval, then writes
       out/<slug>.md. The default OpenMinion action policy gates this step.
    4. Each URL runs in its own session; the script ranks all briefs at the end
       (GO first, then least effort).
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from openminion import Agent, tool

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
MAX_PAGE_CHARS = 6_000


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip())


def install_rate_limit_backoff(max_retries: int = 6) -> None:
    """Retry provider HTTP 429s, honouring the retry-after hint.

    OpenMinion 0.1.22 surfaces a 429 as RATE_LIMITED and ends the turn, even when
    the provider says exactly how long to wait. On small free tiers (for example
    Groq's 8k tokens per minute) a single tool-using turn can cross the limit
    mid-loop, so the agent waits and resends the same request instead.
    """
    original_send = httpx.Client.send

    def send_with_backoff(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        response = original_send(self, request, *args, **kwargs)
        for attempt in range(max_retries):
            if response.status_code != 429:
                break
            hint = response.headers.get("retry-after", "")
            try:
                body = response.read().decode("utf-8", "replace")
            except httpx.HTTPError:
                body = ""
            match = re.search(r"try again in ([\d.]+)s", body)
            daily = re.search(r'"retryDelay":\s*"(\d+)s"', body)
            if daily and int(daily.group(1)) > 120:
                print(f"  [backoff] provider quota exhausted for ~{int(daily.group(1)) // 3600}h; not retrying")
                return httpx.Response(429, request=request, content=body.encode(), headers=response.headers)
            wait = float(hint) if hint.replace(".", "", 1).isdigit() else (
                float(match.group(1)) if match else 15.0 * (attempt + 1)
            )
            wait = min(wait + 1.0, 65.0)
            print(f"  [backoff] provider 429, waiting {wait:.0f}s (retry {attempt + 1}/{max_retries})")
            response.close()
            time.sleep(wait)
            response = original_send(self, request, *args, **kwargs)
        return response

    httpx.Client.send = send_with_backoff  # type: ignore[method-assign]


# ---------------------------------------------------------------- tools


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|form)\b.*?</\1>", " ", raw)
    main = re.search(r"(?is)<(main|article)\b.*?</\1>", raw)
    if main:
        raw = main.group(0)
    raw = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr)>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


@tool(
    name="fetch_page",
    description=(
        "Download a public web page (hackathon, bounty or grant listing) and "
        "return its readable text, truncated to about 6k characters plus key requirement lines."
    ),
    min_scope="READ_ONLY",
    tags=("web", "research"),
)
def fetch_page(url: str) -> str:
    """Fetch a public URL and return plain text."""
    if not url.startswith(("http://", "https://")):
        return "ERROR: only http(s) URLs are allowed"
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (hackathon-scout; +openminion)"},
        )
    except httpx.HTTPError as exc:
        return f"ERROR: request failed: {exc}"
    if response.status_code >= 400:
        return f"ERROR: HTTP {response.status_code}"
    content_type = response.headers.get("content-type", "")
    body = response.text
    if "json" in content_type:
        # Listing APIs embed HTML descriptions inside JSON strings: flatten the
        # string values first, then strip the markup.
        try:
            strings: list[str] = []

            def walk(node: object) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if isinstance(value, (int, float)) or (
                            isinstance(value, str) and 0 < len(value) <= 40
                        ):
                            strings.append(f"{key}: {value}")
                        else:
                            walk(value)
                elif isinstance(node, list):
                    for value in node:
                        walk(value)
                elif isinstance(node, str) and len(node) > 3:
                    strings.append(node)

            walk(response.json())
            text = _html_to_text("\n".join(strings))
        except ValueError:
            text = body
    else:
        text = _html_to_text(body)
    # Deterministic pre-scan: surface lines that gate participation (money, KYC,
    # region, deadline) at the top, so small models do not miss them.
    signals: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line and line not in signals and re.search(
            r"deposit|fund your|stake|kyc|at least \d+ ?(usdc|usd|sol|eth)|region|resident|"
            r"must be|deadline|eligib",
            line,
            re.I,
        ):
            signals.append(line[:200])
    header = ""
    if signals:
        header = "GATING SIGNALS FOUND ON THIS PAGE:\n- " + "\n- ".join(signals[:15]) + "\n\nPAGE TEXT:\n"
    if len(text) > MAX_PAGE_CHARS:
        text = text[:MAX_PAGE_CHARS] + "\n[...truncated]"
    text = header + text
    return text


@tool(
    name="save_checklist",
    description=(
        "Write a markdown submission checklist to out/<slug>.md. "
        "This writes a local file, so it needs human approval."
    ),
    tags=("files",),
)
def save_checklist(slug: str, markdown: str) -> str:
    """Persist the checklist for the operator."""
    safe = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")[:60] or "brief"
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{safe}.md"
    path.write_text(markdown, encoding="utf-8")
    return f"saved {path.relative_to(ROOT)}"


# ---------------------------------------------------------------- output


class HackathonBrief(BaseModel):
    name: str
    url: str
    deadline: str = Field(description="Submission deadline as written on the page, or 'unknown'")
    prize_summary: str = Field(description="Prize pool and how it is paid (token, fiat)")
    eligibility: list[str] = Field(default_factory=list)
    required_deliverables: list[str] = Field(
        default_factory=list, description="Everything that must be submitted"
    )
    judging_criteria: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(
        default_factory=list,
        description="Things a solo builder would need first: KYC, deposits, region locks, accounts",
    )
    effort_hours: int = Field(description="Honest estimate for a solo builder")
    verdict: str = Field(description="GO or SKIP plus one sentence why")


_CAPTURED: dict[str, HackathonBrief] = {}


@tool(
    name="submit_brief",
    description=(
        "Submit the final structured brief for the page you just read. Call it exactly "
        "once, after save_checklist. List arguments are arrays of short strings."
    ),
    min_scope="READ_ONLY",
    tags=("output",),
)
def submit_brief(
    name: str,
    url: str,
    deadline: str,
    prize_summary: str,
    eligibility: list[str],
    required_deliverables: list[str],
    judging_criteria: list[str],
    blockers: list[str],
    effort_hours: int,
    verdict: str,
) -> str:
    """Capture the typed brief.

    The runtime wraps final replies in its own answer envelope, so a typed tool
    call is the reliable channel for structured output.
    """
    # Deterministic policy on top of the model's opinion: own capital at risk means SKIP.
    money = re.compile(r"deposit|fund|stake|\d+\s*(usdc|usd|sol|eth)\b|buy|purchase", re.I)
    needs_capital = any(money.search(b) for b in blockers or [])
    model_skip = (verdict or "").strip().upper().startswith("SKIP")
    reason = re.sub(r"^\s*(GO|SKIP)\b[\s:\-–—]*", "", verdict or "", flags=re.I).strip()
    if needs_capital:
        verdict = "SKIP - requires the builder's own capital: " + next(
            b for b in blockers if money.search(b)
        )
    elif model_skip:
        verdict = "SKIP - " + (reason or "the model judged it not worth entering")
    else:
        verdict = "GO - " + (reason or "no capital or KYC gate found on the page")
    brief = HackathonBrief(
        name=name,
        url=url,
        deadline=deadline,
        prize_summary=prize_summary,
        eligibility=list(eligibility or []),
        required_deliverables=list(required_deliverables or []),
        judging_criteria=list(judging_criteria or []),
        blockers=list(blockers or []),
        effort_hours=int(effort_hours or 0),
        verdict=verdict,
    )
    _CAPTURED[url] = brief
    return "brief recorded"


INSTRUCTIONS = """You are Hackathon Scout, a careful research assistant for solo builders.
For the given URL, use exactly three tool calls in this order, ONE tool call per
response (never call tools in parallel):
1. fetch_page(url). Use only facts from the returned text and write 'unknown'
   instead of guessing.
2. save_checklist(slug, markdown): a title, the deadline, then one '- [ ]' line per
   required deliverable and blocker, in the order a builder should tackle them.
3. submit_brief(...) with every field filled.
   - required_deliverables: only what gets handed in (repo link, demo video, post link,
     write-up, form fields).
   - blockers: what must be true before a solo builder can even compete: money to
     deposit or stake (quote the amount), KYC, region or residency limits, accounts
     to create. Leave it empty if the page states none.
   - verdict: start with GO or SKIP, then one sentence. Say SKIP when the page asks
     the builder to deposit or put their own capital at risk.
After submit_brief, reply with one short sentence."""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--yes", action="store_true", help="auto-approve file writes")
    parser.add_argument("--model", default=None, help="override the configured model id")
    args = parser.parse_args()

    load_env()
    # Agent.run(timeout_seconds=...) does not lift the runtime's own 300 s brain turn
    # budget; small free tiers need more wall time once 429 backoff kicks in.
    os.environ.setdefault("OPENMINION_TURN_TIMEOUT_SECONDS", "900")
    install_rate_limit_backoff()

    def approve(tool_name: str, tool_args: dict, approval_id: str) -> bool:
        target = tool_args.get("slug", "")
        if args.yes:
            print(f"  [approval {approval_id[:8]}] auto-approved {tool_name}({target})")
            return True
        answer = input(f"  [approval {approval_id[:8]}] allow {tool_name}({target})? [y/N] ")
        return answer.strip().lower() in {"y", "yes"}

    briefs: list[HackathonBrief] = []
    with Agent(
        name="hackathon-scout",
        instructions=INSTRUCTIONS,
        tools=[fetch_page, save_checklist, submit_brief],
        model=args.model,
    ) as agent:
        for url in args.urls:
            print(f"\n=== {url}")
            run_id = session_id = None
            stats: dict = {}
            # Each page gets an explicit instruction and its own session. If the model
            # sends a malformed internal task_update, the runtime answers with a
            # "could not safely update the task conditions" clarify instead of
            # retrying, so the agent retries once in a fresh session.
            brief = None
            for attempt in range(2):
                result = agent.run(
                    f"Scout this opportunity page and record its brief: {url}",
                    session_id=f"scout-{uuid4().hex[:12]}",
                    approval_callback=approve,
                    timeout_seconds=900,
                )
                run_id, session_id, stats = result.run_id, result.session_id, result.stats
                brief = _CAPTURED.get(url) or (next(iter(_CAPTURED.values())) if _CAPTURED else None)
                _CAPTURED.clear()
                if brief is not None or "task conditions" not in result.text:
                    break
                print("  [retry] runtime asked to restate the task; retrying in a fresh session")
            if brief is None:
                print(f"  [output] no submit_brief call; final reply was: {result.text[:200]}")
                continue
            briefs.append(brief)
            print(f"{brief.name} | deadline: {brief.deadline}")
            print(f"prizes: {brief.prize_summary}")
            for item in brief.required_deliverables:
                print(f"  deliverable: {item}")
            for item in brief.blockers:
                print(f"  blocker: {item}")
            print(f"effort: ~{brief.effort_hours}h | {brief.verdict}")
            print(f"run={run_id} session={session_id} stats={stats}")

    if len(briefs) > 1:
        ranked = sorted(briefs, key=lambda b: (not b.verdict.upper().startswith("GO"), b.effort_hours))
        print("\n=== ranking (GO first, then least effort)")
        for i, b in enumerate(ranked, 1):
            print(f"{i}. {b.name}: {b.verdict} (~{b.effort_hours}h)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
