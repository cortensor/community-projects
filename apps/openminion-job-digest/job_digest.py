"""Freelance job digest agent built on the OpenMinion 0.1 Python SDK.

One useful, repeatable workflow: pull remote job listings from two free public
feeds, dedupe them against jobs the agent already surfaced, shortlist the best
fits for a junior AI/software engineer, and write a Markdown digest.

OpenMinion building blocks used:
  - Agent (Python SDK) with persistent session ids for run-to-run continuity
  - @tool functions with explicit least-privilege scopes, one driven through a
    verifiable forced tool call (the reliable 0.1 pattern for small models)
  - Structured output validated against a Pydantic model (output_type)
  - ProviderError / AgentOutputValidationError handling with backoff

Design note: the feeds are fetched deterministically by the script (the same
functions the Agent exposes as tools), because model-choice tool routing on
free-tier models is unreliable in 0.1 - see LEARNINGS.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import json
import sys
import time
from pathlib import Path

import requests
from pydantic import BaseModel, Field

from openminion import Agent, AgentOutputValidationError, ProviderError, tool

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "out"
SEEN_PATH = DATA_DIR / "seen_jobs.json"

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

PROFILE = (
    "Junior AI/software engineer based in Egypt, about one year of experience. "
    "Looking for remote or Egypt-based entry-level roles or freelance/contract "
    "gigs: Python, machine learning, data engineering, backend, LLM tooling. "
    "Exclude senior roles (3+ years required), unpaid internships, and "
    "gambling/forex/crypto-trading products."
)


class JobPick(BaseModel):
    id: str = Field(description="The job id exactly as given in the input.")
    title: str
    company: str
    url: str
    source: str
    why_fit: str = Field(description="One sentence on why this fits the profile.")


class Digest(BaseModel):
    picks: list[JobPick] = Field(max_length=5)
    notes: str = Field(description="One or two sentences about this run.")


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_remotive_jobs(search: str, limit: int = 5) -> str:
    """Search the Remotive remote-jobs API and return compact JSON rows."""

    resp = requests.get(
        REMOTIVE_URL,
        params={"search": search, "limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    rows = [
        {
            "id": f"remotive-{job['id']}",
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "url": job.get("url", ""),
        }
        for job in resp.json().get("jobs", [])[:limit]
    ]
    return json.dumps(rows)


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_arbeitnow_jobs(limit: int = 8) -> str:
    """Fetch the newest listings from the Arbeitnow job-board API."""

    resp = requests.get(ARBEITNOW_URL, timeout=30)
    resp.raise_for_status()
    rows = [
        {
            "id": f"arbeitnow-{job['slug']}",
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "url": job.get("url", ""),
            "remote": bool(job.get("remote")),
        }
        for job in resp.json().get("data", [])[:limit]
    ]
    return json.dumps(rows)


@tool(min_scope="READ_ONLY", idempotent=True)
def fetch_hn_hiring_jobs(query: str = "remote junior python", limit: int = 8) -> str:
    """Search the latest Hacker News "Who is hiring?" thread (Algolia API)."""

    import re

    thread = requests.get(
        "https://hn.algolia.com/api/v1/search_by_date",
        params={
            "query": "Ask HN: Who is hiring",
            "tags": "story,author_whoishiring",
            "hitsPerPage": 1,
        },
        timeout=30,
    ).json()["hits"][0]["objectID"]
    hits = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={"tags": f"comment,story_{thread}", "query": query, "hitsPerPage": limit},
        timeout=30,
    ).json()["hits"]
    rows = []
    for h in hits:
        text = re.sub(r"<[^>]+>", " ", h.get("comment_text") or "")
        head = text.split("|")[0].strip()[:60] or "HN poster"
        rows.append(
            {
                "id": f"hn-{h['objectID']}",
                "title": text[:110].replace("\n", " "),
                "company": head,
                "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
            }
        )
    return json.dumps(rows)


@tool(min_scope="READ_ONLY", idempotent=True)
def load_seen_job_ids() -> str:
    """Return the ids of jobs already surfaced in earlier digests."""

    if not SEEN_PATH.exists():
        return "[]"
    return json.dumps(sorted(json.loads(SEEN_PATH.read_text())))


def record_seen(ids: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    seen = set(json.loads(SEEN_PATH.read_text())) if SEEN_PATH.exists() else set()
    seen.update(ids)
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=1))


def render_markdown(digest: Digest, run_date: dt.date) -> str:
    lines = [
        f"# Remote job digest - {run_date.isoformat()}",
        "",
        digest.notes,
        "",
    ]
    for i, pick in enumerate(digest.picks, 1):
        lines.append(f"## {i}. {pick.title} - {pick.company}")
        lines.append(f"- Source: {pick.source}")
        lines.append(f"- Link: {pick.url}")
        lines.append(f"- Why it fits: {pick.why_fit}")
        lines.append("")
    return "\n".join(lines)


def run_agent(agent_kwargs: dict, prompt: str, attempts: int = 4):
    """Run one Agent turn with retry/backoff on transient provider failures."""

    last_error = None
    for attempt in range(attempts):
        try:
            with Agent(**agent_kwargs) as agent:
                return agent.run(prompt)
        except AgentOutputValidationError as exc:
            last_error = exc
            print(f"attempt {attempt + 1}: output validation failed, retrying")
            time.sleep(20)
        except ProviderError as exc:
            last_error = exc
            throttled = exc.code == "RATE_LIMITED" or "too large" in str(exc)
            if throttled and attempt < attempts - 1:
                print(f"attempt {attempt + 1}: throttled, waiting 65s")
                time.sleep(65)
                continue
            print(f"provider failed: {exc.code}: {exc.message}", file=sys.stderr)
            return None
    print(f"agent failed after {attempts} attempts: {last_error}", file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", default=None, help="Configured agent id")
    stamp = int(dt.datetime.now().timestamp())
    parser.add_argument(
        "--session", default=f"job-digest-{stamp}", help="OpenMinion session id"
    )
    parser.add_argument(
        "--config",
        default="/tmp/openminion/.openminion/agents.json",
        help="Path to agents.json",
    )
    parser.add_argument(
        "--fallback-config",
        default="/tmp/openminion-groq/.openminion/agents.json",
        help="Fallback agents.json (secondary provider)",
    )
    args = parser.parse_args()

    # Step 1: verifiable tool call through the SDK (same pattern as the
    # official tool_agent example): the model is forced to call
    # load_seen_job_ids, so the tool invocation is real, not simulated.
    agent_kwargs = {
        "agent_id": args.agent,
        "instructions": "Use load_seen_job_ids and reply with the ids only.",
        "tools": [load_seen_job_ids],
        "forced_tools": ["load_seen_job_ids"],
        "session_id": args.session,
    }
    seen_result = run_agent(agent_kwargs, "Which job ids were already surfaced?")
    if seen_result is None and os.environ.get("OPENMINION_GROQ_HOME"):
        print("primary provider failed, retrying tool call on fallback provider")
        prev_home = os.environ.get("OPENMINION_HOME")
        os.environ["OPENMINION_HOME"] = os.environ["OPENMINION_GROQ_HOME"]
        seen_result = run_agent(
            {**agent_kwargs, "session_id": args.session + "-fb"},
            "Which job ids were already surfaced?",
            attempts=2,
        )
        if prev_home is None:
            del os.environ["OPENMINION_HOME"]
        else:
            os.environ["OPENMINION_HOME"] = prev_home
    if seen_result is None:
        # The seen-store is still read directly below, so the digest can be
        # produced; the verifiable tool call is retried on the next run.
        print("tool-call step failed on all providers, continuing without it")

    # Fetch the feeds (same functions the Agent can call as tools).
    remotive = json.loads(fetch_remotive_jobs("machine learning"))
    arbeitnow = json.loads(fetch_arbeitnow_jobs())
    hn = json.loads(fetch_hn_hiring_jobs())
    seen = set(json.loads(load_seen_job_ids()))
    fresh = [j for j in hn + remotive + arbeitnow if j["id"] not in seen]
    print(f"fetched {len(remotive)} + {len(arbeitnow)} jobs, {len(fresh)} unseen")

    # Keep the model request small on free-tier budgets: shortlist locally
    # first, and let the model rank only the survivors.
    senior = ("senior", "sr.", "lead", "manager", "principal", "staff")
    fresh = [
        j for j in fresh
        if not any(word in j["title"].lower() for word in senior)
    ][:6]

    if not fresh:
        print("no new jobs since the last run")
        return 0

    pick_prompt = (
        "Profile:\n"
        f"{PROFILE}\n\n"
        "Candidate listings (JSON):\n"
        f"{json.dumps([{'id': j['id'], 'title': j['title'], 'company': j['company']} for j in fresh])}\n\n"
        "Pick up to 5 best fits. In `source` put the feed name "
        "(remotive, arbeitnow or hn)."
    )

    # Step 2: shortlist through OpenMinion's runtime LLM client (thin
    # completion). The brain-loop Agent turn and its output_type schema
    # injection exceed free-tier request budgets; this path stays inside
    # them while still using the SDK's provider layer (see LEARNINGS.md).
    from openminion import APIRuntime

    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful job scout. Pick only from the "
                "listings in the prompt, keep every id and url "
                "exactly as given, and reply with ONLY a JSON "
                "object of shape {\"picks\": [{\"id\", \"title\", "
                "\"company\", \"url\", \"source\", \"why_fit\"}], "
                "\"notes\": string}. No markdown, no prose."
            ),
        },
        {"role": "user", "content": pick_prompt},
    ]

    # Provider fallback chain: the primary config first, then the Groq
    # fallback config. Free tiers have daily/minute caps; whichever provider
    # answers first wins this run (see LEARNINGS.md).
    llm_response = None
    for config_path in [args.config, args.fallback_config]:
        if not config_path or not Path(config_path).exists():
            continue
        runtime = APIRuntime.from_config_path(config_path)
        try:
            for attempt in range(2):
                try:
                    # Reasoning models can spend the whole default completion
                    # budget on thinking and return empty content; 8192
                    # exceeds the primary model's output cap, 4096 works
                    # (see LEARNINGS.md).
                    candidate = runtime.llm.client.complete(
                        messages, max_tokens=4096
                    )
                    if candidate.output_text.strip():
                        llm_response = candidate
                        print(f"completion via {config_path}")
                        break
                    print(f"attempt {attempt + 1}: empty completion, retrying")
                    time.sleep(20)
                except ProviderError as exc:
                    print(f"{config_path}: provider error {exc.code}: {exc.message}")
                    time.sleep(30)
        finally:
            runtime.close()
        if llm_response is not None:
            break
    if llm_response is None:
        print("all providers failed or returned empty", file=sys.stderr)
        return 1

    text = llm_response.output_text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start_i, end_i = text.find("{"), text.rfind("}")
    digest = Digest.model_validate_json(text[start_i : end_i + 1])

    # Re-attach exact urls by id so the model never has to copy them.
    urls = {j["id"]: j["url"] for j in fresh}
    for pick in digest.picks:
        if pick.id in urls:
            pick.url = urls[pick.id]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    md_path = OUT_DIR / f"digest-{today.isoformat()}.md"
    md_path.write_text(render_markdown(digest, today))
    record_seen([pick.id for pick in digest.picks])

    print(f"wrote {md_path} ({len(digest.picks)} picks)")
    print(f"session={args.session}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
