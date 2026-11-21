"""OpenMinion wiring for Paper Deadline Watch.

Design (multi-source brief, not a verdict):
- The deterministic layer (``store`` / ``brief``) owns all facts: venues,
  dates, verification statuses. The model never supplies a fact.
- Two read-only tools expose that layer to the model: ``lookup_deadlines``
  (topic + window -> JSON rows) and ``lookup_venue`` (one abbreviation).
- The brief writer agent delegates to two subagents — one summarises the
  conference deadlines, one the journal/law deadlines — then synthesises
  2–3 paragraphs as a ``BriefSynthesis`` JSON object. A handoff to a
  reminder-formatter agent produces the final reminder text; if the free
  model does not take the handoff, the formatter is called directly and
  the run record says so.
- The model reply is parsed defensively: the SDK prefixes replies with
  ``agent_id: `` and free models often answer in prose instead of JSON,
  so we strip the prefix and extract the first ``{...}`` object before
  Pydantic validation. Any failure falls back to the deterministic
  template brief — the brief is never blocked on the model.

Free-tier notes: prompts are kept short (few citations, short evidence),
timeouts are generous, and every model call is paced (see ``config``).
"""

from __future__ import annotations

import json
import re
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .brief import Brief, build_template_brief
from .config import ProviderSettings, pace_model_call, resolve_preset, sanitize_no_proxy
from .store import Deadline, VenueStore
from .topics import match_topic

__all__ = [
    "BriefSynthesis",
    "build_runtime",
    "extract_json_object",
    "parse_synthesis_reply",
    "run_agent_with_retry",
    "run_agent_stream_with_retry",
    "run_brief",
]


class BriefSynthesis(BaseModel):
    """Structured synthesis the model must return (prose only, no facts)."""

    paragraphs: list[str] = Field(
        description="2-3 short paragraphs: nearest deadline, A-level venues, what to watch"
    )
    nearest_abbreviation: str = Field(description="Abbreviation of the nearest deadline, copied from the tool output")
    a_level_abbreviations: list[str] = Field(default_factory=list, description="A-level abbreviations in scope, copied from the tool output")


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first balanced ``{...}`` JSON object from reply text.

    Handles the SDK's ``agent_id: `` prefix and prose around the JSON.
    Returns None when no balanced JSON object parses.
    """
    if not text:
        return None
    # Strip a leading "name: " prefix the SDK adds to replies.
    stripped = re.sub(r"^[A-Za-z0-9_.-]+:\s*", "", text.strip(), count=1)
    start = stripped.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(stripped)):
        ch = stripped[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(stripped[start : i + 1])
                except ValueError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def parse_synthesis_reply(text: str) -> BriefSynthesis | None:
    """Parse + validate a model reply into a BriefSynthesis, or None."""
    obj = extract_json_object(text)
    if obj is None:
        return None
    try:
        return BriefSynthesis.model_validate(obj)
    except Exception:
        return None


def parse_retry_after_seconds(error_text: str) -> float | None:
    """Parse Pollinations' ``Retry after Ns`` from a 402 message."""
    m = re.search(r"[Rr]etry after (\d+(?:\.\d+)?)s", error_text or "")
    return float(m.group(1)) if m else None


def is_free_limit_error(exc: BaseException) -> bool:
    """True when the provider refused on the free-tier rate limit (HTTP 402)."""
    text = f"{type(exc).__name__}: {exc}"
    return "402" in text and "Free limit reached" in text


def run_agent_with_retry(agent, message: str, *, timeout_seconds: float, max_retries: int = 3, **run_kwargs):
    """Run an agent, retrying free-tier 402s after the server's Retry-after.

    The SDK retries internally at ~300 ms, which cannot beat Pollinations'
    45 s free window; the retry has to happen here, honouring the
    ``Retry after Ns`` the server returns. Non-402 errors are not retried.
    """
    last: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return agent.run(message, timeout_seconds=timeout_seconds, **run_kwargs)
        except Exception as exc:
            last = exc
            if not is_free_limit_error(exc) or attempt == max_retries:
                raise
            wait = (parse_retry_after_seconds(str(exc)) or 45.0) + 5.0
            time.sleep(wait)
    raise last  # pragma: no cover - loop always raises or returns


def run_agent_stream_with_retry(agent, message: str, *, timeout_seconds: float, on_delta, max_retries: int = 3, **run_kwargs):
    """Same 402 retry policy for ``run_stream``."""
    last: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return agent.run_stream(message, on_delta=on_delta, timeout_seconds=timeout_seconds, **run_kwargs)
        except Exception as exc:
            last = exc
            if not is_free_limit_error(exc) or attempt == max_retries:
                raise
            wait = (parse_retry_after_seconds(str(exc)) or 45.0) + 5.0
            time.sleep(wait)
    raise last  # pragma: no cover


# ---------------------------------------------------------------- runtime

def build_runtime(provider: ProviderSettings, home_root: Path, data_root: Path):
    """Isolated APIRuntime for one provider preset (no keys on disk)."""
    sanitize_no_proxy()
    from openminion import APIRuntime
    from openminion.base.config import OpenMinionConfig
    from openminion.base.config.core import AgentProfileConfig
    from openminion.base.config.providers import OpenAIProviderConfig

    cfg = OpenMinionConfig(
        agents={
            "paper-watch": AgentProfileConfig(
                name="paper-watch", provider="openai", default_channel="console"
            )
        }
    )
    cfg.providers.openai = OpenAIProviderConfig(
        model=provider.model,
        api_key=provider.api_key,
        api_key_env=provider.api_key_env,
        base_url=provider.base_url,
        timeout_seconds=provider.timeout_seconds,
    )
    return APIRuntime.from_config(config=cfg, home_root=home_root, data_root=data_root)


def _tools_for(store: VenueStore, today: date):
    """The two read-only lookup tools (deterministic, CSV-backed)."""
    from openminion import tool

    @tool(name="lookup_deadlines", description="Look up upcoming deadlines for a topic. Returns JSON rows with venue, grade, date, verification status, source URL.", min_scope="READ_ONLY")
    def lookup_deadlines(topic: str, within_days: int = 120) -> str:
        rows = store.upcoming(within_days, today)
        matched = match_topic(topic, rows)
        return json.dumps(
            [
                {
                    "abbreviation": d.abbreviation,
                    "full_name": d.full_name,
                    "kind": d.kind,
                    "ccf_grade": d.ccf_grade,
                    "deadline": d.deadline_date.isoformat() if d.deadline_date else None,
                    "deadline_kind": d.deadline_kind,
                    "track": d.track,
                    "status": d.status,
                    "source_url": d.source_url,
                }
                for d in matched
            ],
            ensure_ascii=False,
        )

    @tool(name="lookup_venue", description="Look up one venue by abbreviation. Returns one JSON row or null.", min_scope="READ_ONLY")
    def lookup_venue(abbreviation: str) -> str:
        d = store.by_abbreviation(abbreviation)
        if d is None:
            return "null"
        return json.dumps(
            {
                "abbreviation": d.abbreviation,
                "full_name": d.full_name,
                "kind": d.kind,
                "ccf_grade": d.ccf_grade,
                "deadline": d.deadline_date.isoformat() if d.deadline_date else None,
                "deadline_kind": d.deadline_kind,
                "status": d.status,
                "source_url": d.source_url,
            },
            ensure_ascii=False,
        )

    return [lookup_deadlines, lookup_venue]


BRIEF_WRITER_INSTRUCTIONS = (
    "You write short research briefs about paper submission deadlines. "
    "You MUST call lookup_deadlines first and use ONLY the rows it returns. "
    "Never invent a venue, a date, or a grade. Copy each deadline's "
    "verification status word for word. Reply with ONLY one JSON object: "
    '{"paragraphs": ["...", "..."], "nearest_abbreviation": "...", '
    '"a_level_abbreviations": ["...", ...]}. No other text.'
)

REMINDER_INSTRUCTIONS = (
    "You format a deadline reminder from a finished brief. Use ONLY the "
    "brief text you are given. Reply with the reminder text only: one line "
    "per deadline (venue, date, verification status), then one line saying "
    "which dates still need checking on the official page."
)


def run_brief(
    topic: str,
    store: VenueStore,
    *,
    within_days: int = 120,
    preset: str | None = None,
    today: date | None = None,
    workdir: str | Path | None = None,
    record: dict[str, Any] | None = None,
) -> Brief:
    """Run the multi-source brief flow; fall back to template on any failure.

    ``record`` (optional) is filled with run evidence: preset, model,
    timings, which path was taken (model / template / handoff / direct),
    and the raw reply (truncated) for the fixtures log.
    """
    today = today or date.today()
    rows = store.upcoming(within_days, today)
    matched = match_topic(topic, rows)
    unclear = [d for d in store.unclear if match_topic(topic, [d])]
    template = build_template_brief(topic, matched, unclear_count=len(unclear))
    provider = resolve_preset(preset)
    if record is not None:
        record.update({"preset": provider.preset, "model": provider.model, "topic": topic})
    if not provider.available:
        if record is not None:
            record["path"] = "template"
            record["fallback_reason"] = provider.unavailable_reason
        return template
    if not matched:
        if record is not None:
            record["path"] = "template"
            record["fallback_reason"] = "no matching deadlines; nothing to synthesise"
        return template

    from openminion import Agent, Handoff, subagent

    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="paper-watch-"))
    tmp.mkdir(parents=True, exist_ok=True)
    runtime = build_runtime(provider, tmp / "home", tmp / "data")
    started = time.monotonic()
    try:
        tools = _tools_for(store, today)
        reminder_agent = Agent(
            instructions=REMINDER_INSTRUCTIONS, runtime=runtime, name="reminder-formatter"
        )
        writer = Agent(
            instructions=BRIEF_WRITER_INSTRUCTIONS,
            runtime=runtime,
            name="brief-writer",
            tools=tools,
            forced_tools=["lookup_deadlines"],
            handoffs=[Handoff(target=reminder_agent, name="format_reminder",
                              description="Format the finished brief as a reminder list")],
        )
        # 1-2. Subagents summarise each source family first (multi-source).
        sub_notes: list[str] = []
        for source, kinds in (("conferences", ["conference"]), ("journals and law", ["journal", "law"])):
            child = subagent(
                writer,
                instructions=(
                    f"Summarise the {source} deadlines for topic {topic!r} in one "
                    "sentence, using only lookup_deadlines results. Never invent data."
                ),
                tools=tools,
                name=f"{source}-summariser",
                timeout_seconds=provider.timeout_seconds,
            )
            pace_model_call()
            sub_started = time.monotonic()
            try:
                sub_res = run_agent_with_retry(
                    child,
                    f"Topic: {topic}. Use lookup_deadlines with within_days={within_days}.",
                    timeout_seconds=provider.timeout_seconds,
                )
                sub_notes.append(f"[{source}] {sub_res.text[:500]}")
                if record is not None:
                    record.setdefault("subagents", []).append(
                        {"source": source, "seconds": round(time.monotonic() - sub_started, 1)}
                    )
            except Exception as exc:  # subagent failure must not kill the brief
                sub_notes.append(f"[{source}] summariser failed: {exc!r}")
                if record is not None:
                    record.setdefault("subagents", []).append(
                        {"source": source, "error": repr(exc)}
                    )
        # 3. Main synthesis.
        prompt = (
            f"Topic: {topic}. within_days={within_days}. "
            "Source notes: " + " ".join(sub_notes)
            + " Now call lookup_deadlines and write the JSON synthesis."
        )
        pace_model_call()
        main_started = time.monotonic()
        result = run_agent_with_retry(writer, prompt, timeout_seconds=provider.timeout_seconds)
        main_seconds = round(time.monotonic() - main_started, 1)
        if record is not None:
            record["main_seconds"] = main_seconds
            record["raw_reply"] = result.text[:2000]
            record["stats"] = dict(getattr(result, "stats", {}) or {})
            record["thread_id"] = getattr(result, "thread_id", None)
        synthesis = parse_synthesis_reply(result.text)
        if synthesis is None:
            if record is not None:
                record["path"] = "template"
                record["fallback_reason"] = (
                    "model reply did not parse as BriefSynthesis JSON; "
                    f"raw reply began: {result.text[:200]!r}"
                )
            return template
        # Validate the model's citations against the deterministic table:
        # every abbreviation it names must exist in the matched set.
        known = {d.abbreviation for d in matched}
        if synthesis.nearest_abbreviation not in known:
            if record is not None:
                record["path"] = "template"
                record["fallback_reason"] = (
                    "model named nearest venue "
                    f"{synthesis.nearest_abbreviation!r} which is not in the "
                    "deterministic match set — possible hallucination"
                )
            return template
        brief = Brief(
            topic=topic,
            deadlines=matched,
            paragraphs=list(synthesis.paragraphs)[:3],
            synthesis_source="model",
            model_name=f"{provider.preset}:{provider.model}",
            total_matching=len(matched),
            unclear_count=len(unclear),
        )
        if record is not None:
            record["path"] = "model"
            raw = getattr(result, "raw", {}) or {}
            record["handoff_taken"] = any(
                "handoff" in str(k).lower() or "transfer" in str(k).lower()
                for k in raw.keys()
            ) if isinstance(raw, dict) else False
        # 4. Reminder text: handoff if the model took it, else direct call.
        try:
            pace_model_call()
            rem = run_agent_with_retry(
                reminder_agent,
                "Format this brief as a reminder:\n" + "\n".join(brief.paragraphs),
                timeout_seconds=provider.timeout_seconds,
            )
            if record is not None:
                record["reminder_text"] = rem.text[:1000]
                record["reminder_path"] = (
                    "handoff" if record.get("handoff_taken") else "direct"
                )
        except Exception as exc:
            if record is not None:
                record["reminder_error"] = repr(exc)
        return brief
    except Exception as exc:
        if record is not None:
            record["path"] = "template"
            record["fallback_reason"] = f"agent run failed: {exc!r}"
        return template
    finally:
        try:
            runtime.close()
        except Exception:
            pass
        if record is not None:
            record["total_seconds"] = round(time.monotonic() - started, 1)
