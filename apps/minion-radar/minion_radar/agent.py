"""OpenMinion runtime path: tools + structured output + an approval-gated memory write."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from openminion import Agent, AgentOutputValidationError, tool

from . import diff, github, state
from .brief import BuilderBrief, BriefParseError, apply_tool_urls, brief_from_snapshot, enrich_brief_from_cache, parse_builder_brief

INSTRUCTIONS = """You are Minion Radar, a release and issue watcher for builders.
1. Call radar_new_releases and radar_new_issues for the repo.
2. Write a BuilderBrief: a one line headline, each new release with why it matters and a risk level
   (none, low, medium, high), up to 8 issues or PRs a builder should watch, and concrete actions.
   Treat words like breaking, removed, deprecated, migration, security, regression as risk signals.
3. Call radar_save_checkpoint once so the next run only shows newer items.
Only use facts from the tool results. Do not invent versions or issue numbers.
Copy each url exactly from the tool results. Do not drop a leading v from a release tag.
Reply with a single raw JSON object only. No markdown, no code fences, no preamble, no trailing commentary.
The JSON must have keys: repo, headline, releases, issues_to_watch, actions.
Each releases and issues_to_watch item has keys: title, url, why_it_matters, risk.
risk must be one of: none, low, medium, high. actions is a list of strings."""

FILM_INSTRUCTIONS = """You are Minion Radar, a release and issue watcher for builders.
The radar_snapshot result is already in the user message. Do not call tools.
Do not echo the snapshot. Do not nest the answer under summary, data, result, or radar_snapshot.
Do not wrap the answer in an array. Do not add type, builder, or builder_spec fields.
Do not copy full release bodies. Write a short why_it_matters in your own words.
Reply with one raw JSON object only, no markdown and no code fences, with exactly these keys:
repo, headline, releases, issues_to_watch, actions.
Each releases and issues_to_watch item has keys: title, url, why_it_matters, risk.
risk must be one of: none, low, medium, high. actions is a list of strings.
Copy each url exactly from the snapshot, including any leading v in a release tag.
Only use facts from the snapshot. Do not invent versions or issue numbers.
Keep releases to at most 3 items, issues_to_watch to at most 5, and actions to at most 4 short lines.
Wrong:
{"repo":"openminion/openminion","summary":{"releases":[],"issues":[]}}
Right:
{"repo":"openminion/openminion","headline":"Two releases and one security issue.","releases":[{"title":"v0.1.23: 0.1.23","url":"https://github.com/openminion/openminion/releases/tag/v0.1.23","why_it_matters":"Config diff and CLI fixes.","risk":"low"}],"issues_to_watch":[{"title":"#642 security audit","url":"https://github.com/openminion/openminion/issues/642","why_it_matters":"PII store permissions.","risk":"high"}],"actions":["Read the 0.1.23 notes before you upgrade."]}"""

STRICT_RETRY_INSTRUCTIONS = """You convert a builder brief into valid JSON.
Reply with a single raw JSON object only. No markdown, no code fences, no preamble, no commentary.
The JSON must have keys: repo, headline, releases, issues_to_watch, actions.
Each item in releases and issues_to_watch has keys: title, url, why_it_matters, risk.
risk must be one of: none, low, medium, high.
actions is a list of strings.
Use only facts from the provided text. Do not invent versions or issue numbers.
Copy urls exactly, including any leading v in a release tag."""


def session_id_for(repo: str, suffix: str = "") -> str:
    """OpenMinion memory rejects session scopes that contain '/'."""
    base = "minion-radar:" + repo.replace("/", "__")
    return base + suffix if suffix else base


def build_tools(repo: str, demo: bool, state_root=state.DEFAULT_DIR, *,
                compact: bool = False) -> tuple[list[Callable], dict]:
    cache: dict[str, Any] = {}
    rel_fetch = 3 if compact else 10
    iss_fetch = 8 if compact else 30
    rel_keep = 3 if compact else 5
    iss_keep = 8 if compact else 20
    body_limit = 180 if compact else 400

    def _mark_issues(rows: list[dict]) -> list[dict]:
        for r in rows:
            r["is_bug"] = diff.is_bug(r)
            r["risk_flags"] = diff.risk_flags(r.get("title", ""))
            r["body"] = r.get("body", "")[:body_limit]
        return rows

    def _save() -> str:
        s = diff.next_state(state.load(repo, state_root), cache.get("releases", []), cache.get("issues", []))
        path = state.save(s, state_root)
        cache["checkpoint_saved"] = True
        return f"saved checkpoint to {path}"

    @tool  # bare @tool = local write, so OpenMinion asks for confirmation first
    def radar_save_checkpoint() -> str:
        """Remember everything seen in this run so the next brief only shows newer items."""
        return _save()

    if compact:
        @tool(min_scope="READ_ONLY", idempotent=True)
        def radar_snapshot() -> str:
            """Return new releases and updated issues for the watched repo in one call."""
            rel = github.fetch_releases(repo, demo=demo, limit=rel_fetch)
            iss = github.fetch_issues(repo, demo=demo, limit=iss_fetch)
            cache["releases"] = rel
            cache["issues"] = iss
            new_rel = diff.new_releases(rel, state.load(repo, state_root))[:rel_keep]
            new_iss = _mark_issues(diff.new_or_updated_issues(iss, state.load(repo, state_root)))[:iss_keep]
            print(f"[tool] radar_snapshot: {len(new_rel)} new releases, {len(new_iss)} new issues", flush=True)
            return json.dumps({"releases": new_rel, "issues": new_iss})

        cache["_save"] = _save
        return [radar_snapshot, radar_save_checkpoint], cache

    @tool(min_scope="READ_ONLY", idempotent=True)
    def radar_new_releases() -> str:
        """Return releases of the watched repo that are new since the last checkpoint."""
        rel = github.fetch_releases(repo, demo=demo, limit=rel_fetch)
        cache["releases"] = rel
        return json.dumps(diff.new_releases(rel, state.load(repo, state_root))[:rel_keep])

    @tool(min_scope="READ_ONLY", idempotent=True)
    def radar_new_issues() -> str:
        """Return issues and PRs created or updated since the last checkpoint, with bug and risk flags."""
        iss = github.fetch_issues(repo, demo=demo, limit=iss_fetch)
        cache["issues"] = iss
        rows = _mark_issues(diff.new_or_updated_issues(iss, state.load(repo, state_root)))
        return json.dumps(rows[:iss_keep])

    cache["_save"] = _save
    return [radar_new_releases, radar_new_issues, radar_save_checkpoint], cache


def _meta_from(result, **extra) -> dict:
    meta = {"run_id": result.run_id, "session_id": result.session_id, "run_state": result.run_state,
            "stats": result.stats}
    meta.update(extra)
    return meta


def _parse_or_raise(text: str) -> BuilderBrief:
    try:
        return parse_builder_brief(text)
    except BriefParseError as exc:
        raise AgentOutputValidationError(
            f"Reply did not validate against BuilderBrief after repair: {exc}",
            raw_text=text,
        ) from exc


def _retry_as_json(repo: str, raw_text: str, *, agent_id: str | None, timeout: float,
                   model: str | None, config_path: str | None):
    prompt = (
        f"Repo: {repo}\n\nConvert this brief into BuilderBrief JSON:\n\n"
        f"{raw_text[:12000]}"
    )
    with Agent(
        name="minion-radar-json", agent_id=agent_id, instructions=STRICT_RETRY_INSTRUCTIONS,
        tools=[], output_type=BuilderBrief, session_id=session_id_for(repo, "-json"),
        model=model, config_path=config_path,
    ) as agent:
        return agent.run(prompt, timeout_seconds=timeout)


def _film_config_path() -> str | None:
    """A lean OpenMinion config for filmed runs. No API keys are copied in."""
    src = Path(".openminion/agents.json")
    if not src.exists():
        return None
    cfg = json.loads(src.read_text())
    runtime = cfg.setdefault("runtime", {})
    # Keep planning policy at the default (balanced). Setting it to off caused
    # Cortensor Portal 502s on the entry tool call: "tool arguments do not
    # match the advertised schema." Memory stays off to cut startup delay.
    runtime["memory_enabled"] = False
    runtime["memory_dynamic_retrieval_enabled"] = False
    runtime["session_summary_enrichment_enabled"] = False
    runtime["session_archive_enabled"] = False
    runtime["agent_loop_max_steps"] = 12
    runtime["agent_loop_tool_result_max_chars"] = 2500
    if "self_improvement" in cfg:
        cfg["self_improvement"]["enabled"] = False
    dest = Path(".openminion/agents.film.json")
    dest.write_text(json.dumps(cfg, indent=2) + "\n")
    # Never leave a concrete key in the film config if setup later stored one.
    raw = dest.read_text()
    # If a secret-looking api_key were present we would refuse to use this file.
    # We only check that api_key fields stay empty; we do not print them.
    probe = json.loads(raw)
    for provider in (probe.get("providers") or {}).values():
        if (provider.get("api_key") or "").strip():
            dest.unlink(missing_ok=True)
            return None
    for agent in (probe.get("agents") or {}).values():
        for conn in (agent.get("model_connections") or {}).values():
            ov = (conn.get("provider_config_overrides") or {})
            if (ov.get("api_key") or "").strip():
                dest.unlink(missing_ok=True)
                return None
    return str(dest)


def run_agent(repo: str, *, agent_id: str | None, approve: Callable[[str, dict, str], bool],
              demo_data: bool = False, timeout: float = 1800, model: str | None = None,
              compact: bool = False, allow_retry: bool = True) -> tuple[BuilderBrief, dict]:
    tools, cache = build_tools(repo, demo_data, compact=compact)
    session_id = session_id_for(repo, "-film2" if compact else "")
    config_path = _film_config_path() if compact else None
    prompt = f"Brief me on {repo}."
    agent_tools = tools
    if compact:
        print("Minion Radar film mode: compact snapshot first, then one model call.", flush=True)
        if config_path:
            print("OpenMinion film config: memory off, short loop.", flush=True)
        print("OpenMinion 0.1.23 has no public switch to skip the judge phase.", flush=True)
        # Cortensor Portal repeatedly 502s on the entry tool-routing call when
        # user tools are attached ("tool arguments do not match the advertised
        # schema"). Run the snapshot tool here, then ask the agent for JSON
        # only. The checkpoint still goes through approval after the brief.
        snapshot_fn = next(fn for fn in tools if getattr(fn, "__name__", "") == "radar_snapshot")
        snapshot_json = snapshot_fn()
        prompt = (
            "Repo: " + repo + "\n\nHere is the radar_snapshot result:\n"
            + snapshot_json
            + "\n\nWrite the BuilderBrief JSON now. Use the exact keys in the Right example: "
            "repo, headline, releases, issues_to_watch, actions. "
            "Do not nest it under summary. Do not copy the snapshot."
        )
        agent_tools = []
    with Agent(
        name="minion-radar", agent_id=agent_id,
        instructions=FILM_INSTRUCTIONS if compact else INSTRUCTIONS,
        tools=agent_tools, output_type=BuilderBrief, session_id=session_id, model=model,
        config_path=config_path,
    ) as agent:
        try:
            try:
                result = agent.run(prompt, timeout_seconds=timeout, approval_callback=approve)
            except Exception as exc:
                if type(exc).__name__ != "ProviderError" and "PROVIDER_ERROR" not in str(exc):
                    raise
                print(f"Provider failed once ({type(exc).__name__}); retrying the same run once.", flush=True)
                result = agent.run(prompt, timeout_seconds=timeout, approval_callback=approve)
            brief, meta = result.output, _meta_from(result, origin="model_generated")
        except AgentOutputValidationError as exc:
            raw = getattr(exc, "raw_text", "") or ""
            try:
                brief = parse_builder_brief(raw)
                meta = {"run_id": None, "session_id": session_id, "run_state": "model_generated",
                        "stats": {}, "repaired": True, "origin": "model_generated"}
            except BriefParseError:
                fallback = brief_from_snapshot(repo, cache) if compact else None
                if fallback is not None:
                    brief, meta = fallback, {"run_id": None, "session_id": session_id,
                                             "run_state": "snapshot_fallback", "stats": {},
                                             "fallback": "offline_from_snapshot",
                                             "origin": "fallback"}
                elif not allow_retry:
                    raise
                else:
                    try:
                        retry = _retry_as_json(repo, raw, agent_id=agent_id, timeout=timeout,
                                               model=model, config_path=config_path)
                        brief, meta = retry.output, _meta_from(retry, retried=True, origin="model_generated")
                    except AgentOutputValidationError as retry_exc:
                        raw2 = getattr(retry_exc, "raw_text", "") or ""
                        brief = _parse_or_raise(raw2 or raw)
                        meta = {"run_id": None, "session_id": session_id_for(repo, "-json"),
                                "run_state": "model_generated", "stats": {}, "repaired": True, "retried": True,
                                "origin": "model_generated"}
    brief = enrich_brief_from_cache(apply_tool_urls(brief, cache), cache)
    if not cache.get("checkpoint_saved") and cache.get("releases") is not None:
        if approve("radar_save_checkpoint", {}, "local"):
            cache["_save"]()
            meta = dict(meta)
            meta["checkpoint"] = "approved_after_run"
        else:
            meta = dict(meta)
            meta["checkpoint"] = "skipped"
    elif cache.get("checkpoint_saved"):
        meta = dict(meta)
        meta["checkpoint"] = "saved_by_agent"
    meta = dict(meta)
    meta.setdefault("origin", "fallback" if meta.get("run_state") == "snapshot_fallback" else "model_generated")
    return brief, meta
