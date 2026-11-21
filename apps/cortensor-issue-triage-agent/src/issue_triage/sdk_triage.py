"""SDK-backed model steps: run model work through OpenMinion ``Agent.run``.

Why this module exists (audit finding 2 — the normal CLI path used only
the paced :class:`~issue_triage.llm_client.DirectClient`, never the SDK):
the draft step now runs through a real ``Agent.run`` turn. The classify
step deliberately stays on the DirectClient — see the measured reasons
below. Nothing here hides that split: the CLI prints which engine
produced each part (``draft_via`` / ``classify_via``).

Measured free-tier reality (Pollinations, gpt-oss-20b, no key; rounds 1–3,
2026-11-17, full evidence in ``docs/WHAT_WE_LEARNED.md`` §4):

- One tool-less ``Agent.run`` turn makes **4 consecutive provider calls**
  (plus the SDK's internal freshness/intent classification rounds). The
  free tier allows 1 reply / 45 s / IP, so turns 402 non-deterministically;
  the SDK retry is hardcoded 300 ms and ignores ``Retry-After``.
- The SDK has **no** ``response_format`` / ``json_object`` support anywhere
  in its provider layer, so the free model free-forms its JSON. For
  classify it invents its own field names (``issue_id`` / ``status`` /
  ``classification`` instead of the TriageVerdict schema) and a same-session
  follow-up asking for the missing fields returns **all nulls**. SDK
  classify is therefore NOT reliable on this tier; the DirectClient stays
  the classify path because it uses tool_calls + ``response_format``
  ``json_object`` (constrained decoding forces the schema).
- The **draft** step works through the SDK. ``Agent.run`` with
  ``output_type=None`` returns the raw reply text; the model answers in the
  SDK's internal ``{"answer": ..., "freshness": {...}}`` envelope (sometimes
  ``{"draft": ...}``, sometimes plain prose). :func:`parse_sdk_draft`
  understands all three shapes; anything else falls back to the
  DirectClient draft so a bad SDK turn never loses the draft.
- The raw SDK reply arrives prefixed with ``"triage: "`` — even when the
  agent is constructed with ``name="draft"``. The prefix matches the
  runtime's agent-profile name (``build_isolated_runtime`` registers a
  profile called ``"triage"``), not the ``Agent`` name, and the SDK's own
  typed coercion then rejects its own prefixed reply. We strip it at the
  app level; see ``docs/WHAT_WE_LEARNED.md`` §4.
- One internal SDK round sends ``<|constrain|>commentary`` tokens that
  Pollinations' upstream rejects with HTTP 400 — and the upstream caches
  that exact 400 (byte-identical body, same timestamp) for minutes, so the
  SDK's 3 rapid retries of it are useless. The turn still completes: the
  400s are non-fatal internal rounds.
"""

from __future__ import annotations

import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from .config import ProviderSettings
from .models import TriageDraft

# A leading "name: " prefix, stripped only when what follows is a JSON
# object (the SDK turn's reply shape). Prose drafts get only the literal
# "triage: " prefix stripped (see parse_sdk_draft).
_JSON_PREFIX_RE = re.compile(r"^[A-Za-z0-9_.\- ]{1,40}:\s*(?=\{)")


def strip_sdk_prefix(text: str) -> str:
    """Remove the SDK turn's ``"triage: "`` reply prefix, if present."""
    t = text.strip()
    if t.startswith("triage: "):
        return t[len("triage: ") :].lstrip()
    return t


def extract_json_object(text: str) -> str | None:
    """First balanced ``{...}`` object in *text*, or None.

    The SDK reply may be prefixed (``triage: {...}``) or wrapped in prose;
    this scans for the first ``{`` and returns up to its matching ``}``.
    """
    t = _JSON_PREFIX_RE.sub("", text.strip(), count=1)
    start = t.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return t[start : i + 1]
    return None


def parse_sdk_draft(raw: str) -> tuple[TriageDraft | None, str | None]:
    """Parse an ``Agent.run`` (``output_type=None``) draft reply.

    Returns ``(draft, shape)`` where shape is ``"answer"`` (the SDK's
    internal ``{"answer": ...}`` envelope), ``"draft"`` (a
    ``{"draft": ...}`` object), ``"prose"`` (plain text used as-is), or
    ``None`` when the reply holds no usable draft text.
    """
    text = strip_sdk_prefix(raw)
    if not text:
        return None, None
    blob = extract_json_object(text)
    if blob is not None:
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            answer = data.get("answer")
            if isinstance(answer, str) and answer.strip():
                return TriageDraft(draft=answer.strip(), tone="neutral"), "answer"
            draft = data.get("draft")
            if isinstance(draft, str) and draft.strip():
                tone = data.get("tone")
                return TriageDraft(
                    draft=draft.strip(),
                    tone=tone if isinstance(tone, str) else "neutral",
                ), "draft"
            return None, None
    # Plain prose (no JSON object): usable as the draft body as-is.
    if len(text) >= 10:
        return TriageDraft(draft=text, tone="neutral"), "prose"
    return None, None


def _build_isolated_runtime(provider: ProviderSettings, tmp: Path):
    """Same isolated-runtime construction as ``probe.build_isolated_runtime``.

    Duplicated here (rather than imported) so this module never depends on
    the probe module: ``triage`` imports this module, and probes import
    triage helpers at call time.
    """
    import logging

    logging.getLogger("openminion").setLevel(logging.WARNING)
    from openminion import APIRuntime
    from openminion.base.config import OpenMinionConfig
    from openminion.base.config.core import AgentProfileConfig
    from openminion.base.config.providers import OpenAIProviderConfig

    cfg = OpenMinionConfig(
        agents={
            "triage": AgentProfileConfig(
                name="triage", provider="openai", default_channel="console"
            )
        }
    )
    cfg.providers.openai = OpenAIProviderConfig(
        model=provider.model,
        api_key=provider.api_key,
        base_url=provider.base_url + "/v1",
    )
    return APIRuntime.from_config(
        config=cfg, home_root=tmp / "home", data_root=tmp / "data"
    )


def _sdk_runner(
    system: str, user: str, provider: ProviderSettings, timeout_seconds: float
) -> str:
    """One real ``Agent.run`` turn (``output_type=None``) -> raw reply text."""
    from openminion import Agent

    with tempfile.TemporaryDirectory() as tmp:
        rt = _build_isolated_runtime(provider, Path(tmp))
        try:
            agent = Agent(
                instructions=system,
                output_type=None,
                model=provider.model,
                name="draft",
                runtime=rt,
            )
            res = agent.run(user, timeout_seconds=timeout_seconds)
            out = res.output
            return out if isinstance(out, str) else str(out)
        finally:
            rt.close()


def run_sdk_draft(
    system: str,
    user: str,
    provider: ProviderSettings,
    timeout_seconds: float = 240,
    runner: Callable[[str, str, ProviderSettings, float], str] | None = None,
) -> tuple[TriageDraft | None, dict[str, Any]]:
    """Draft a reply through a real OpenMinion ``Agent.run`` turn.

    Returns ``(draft_or_None, meta)``. ``meta`` always carries ``channel``
    (``"sdk-native"``), ``latency_ms``, ``model``, ``shape`` (see
    :func:`parse_sdk_draft`) and, on failure, ``error`` plus the first 200
    chars of the raw reply (``raw_head``) so a failed turn stays debuggable.
    A ``None`` draft means the caller should fall back to the DirectClient
    draft — an SDK turn that cannot produce a draft must never lose one.
    """
    started = time.monotonic()
    run = runner or _sdk_runner
    meta: dict[str, Any] = {
        "channel": "sdk-native",
        "model": provider.model,
        "shape": None,
    }
    try:
        raw = run(system, user, provider, timeout_seconds)
    except Exception as exc:  # noqa: BLE001 - evidence capture, caller falls back
        meta["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        meta["latency_ms"] = int((time.monotonic() - started) * 1000)
        return None, meta
    meta["latency_ms"] = int((time.monotonic() - started) * 1000)
    meta["raw_head"] = raw[:200]
    draft, shape = parse_sdk_draft(raw)
    meta["shape"] = shape
    if draft is None:
        meta["error"] = "SDK reply held no usable draft text"
    return draft, meta
